"""create_monitor_sdk.py

Creates a data drift monitor using the Azure ML Python SDK.

This monitor compares the feature distributions between:
- Baseline: tx_training_dataset (training data)
- Production: inference data uploaded to the datastore

Prerequisites:
    pip install azure-ai-ml azure-identity

Run in the project venv after loading env vars:
    .\\set_env.ps1
    .\\.venv\\Scripts\\Activate.ps1
    python create_monitor_sdk.py
"""

import os
from azure.identity import DefaultAzureCredential
from azure.ai.ml import Input, MLClient
from azure.ai.ml.entities import (
    AlertNotification,
    BaselineDataRange,
    DataDriftSignal,
    MonitoringTarget,
    MonitorDefinition,
    MonitorSchedule,
    RecurrencePattern,
    RecurrenceTrigger,
    ServerlessSparkCompute,
    ReferenceData,
    ProductionData,
    DataDriftMetricThreshold,
)


def main():
    # -------------------------------------------------------------------------
    # 1. Get workspace details from environment variables
    # -------------------------------------------------------------------------
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_group = os.environ["AZURE_RESOURCE_GROUP"]
    workspace_name = os.environ["AZURE_ML_WORKSPACE"]
    datastore_name = os.environ.get("DEFAULT_DATASTORE", "workspaceblobstore")
    alert_email = os.environ.get("ALERT_EMAIL", "")

    # Get a handle to the workspace via MLClient
    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )
    print(f"Connected to workspace: {workspace_name}")

    # -------------------------------------------------------------------------
    # 2. Create a serverless Spark compute for monitoring jobs
    # -------------------------------------------------------------------------
    spark_compute = ServerlessSparkCompute(
        instance_type="standard_e4s_v3",
        runtime_version="3.4",
    )

    # -------------------------------------------------------------------------
    # 3. Specify the ML task type for the model being monitored
    # -------------------------------------------------------------------------
    monitoring_target = MonitoringTarget(
        ml_task="classification",
        endpoint_deployment_id=None,  # Not using managed endpoint
    )

    # -------------------------------------------------------------------------
    # 4. Define baseline (reference) data - training dataset
    # -------------------------------------------------------------------------
    reference_data = ReferenceData(
        input_data=Input(
            type="mltable",
            path="azureml:tx_training_mltable:1",
        ),
        data_column_names={
            "target_column": "label",
        },
    )

    # -------------------------------------------------------------------------
    # 5. Define production data - inference data as MLTable
    # -------------------------------------------------------------------------
    production_data = ProductionData(
        input_data=Input(
            type="mltable",
            path="azureml:tx_inference_mltable:1",
        ),
        data_window=BaselineDataRange(
            lookback_window_offset="P0D",   # Start from today
            lookback_window_size="P7D",     # Look back 7 days
        ),
    )

    # -------------------------------------------------------------------------
    # 6. Create Data Drift Signal
    # -------------------------------------------------------------------------
    # Features to monitor for drift
    features = ["feature_0", "feature_1", "feature_2", "feature_3", "feature_4"]

    data_drift_signal = DataDriftSignal(
        reference_data=reference_data,
        production_data=production_data,
        features=features,
        metric_thresholds=DataDriftMetricThreshold(
            numerical=None,      # Use defaults
            categorical=None,    # Use defaults
        ),
        alert_enabled=True,
    )

    # Put all monitoring signals in a dictionary
    monitoring_signals = {
        "tx_data_drift": data_drift_signal,
    }

    # -------------------------------------------------------------------------
    # 7. Create alert notification (required by API)
    # -------------------------------------------------------------------------
    alert_notification = AlertNotification(
        emails=[alert_email] if alert_email else ["noreply@example.com"]
    )

    # -------------------------------------------------------------------------
    # 8. Set up the monitor definition
    # -------------------------------------------------------------------------
    monitor_definition = MonitorDefinition(
        compute=spark_compute,
        monitoring_target=monitoring_target,
        monitoring_signals=monitoring_signals,
        alert_notification=alert_notification,
    )

    # -------------------------------------------------------------------------
    # 9. Specify the schedule frequency
    # -------------------------------------------------------------------------
    recurrence_trigger = RecurrenceTrigger(
        frequency="day",
        interval=1,             # Run every 1 day
        schedule=RecurrencePattern(
            hours=6,            # Start at 6 AM
            minutes=0,
        ),
    )

    # -------------------------------------------------------------------------
    # 10. Create the monitoring schedule
    # -------------------------------------------------------------------------
    model_monitor = MonitorSchedule(
        name="tx_data_drift_monitor",
        trigger=recurrence_trigger,
        create_monitor=monitor_definition,
    )

    # -------------------------------------------------------------------------
    # 11. Submit the monitoring schedule to Azure ML
    # -------------------------------------------------------------------------
    print("Creating/updating model monitor schedule...")
    try:
        poller = ml_client.schedules.begin_create_or_update(model_monitor)
        created_monitor = poller.result()

        print(f"\n✓ Monitor created successfully!")
        print(f"  Name: {created_monitor.name}")
        print(f"  Provisioning state: {created_monitor.provisioning_state}")
    except Exception as e:
        print(f"\n✗ Error creating monitor: {type(e).__name__}: {e}")
        print("\nTip: Check that your data assets exist and paths are correct.")
        raise

    print(f"\nView in Azure ML Studio:")
    print(f"  https://ml.azure.com/monitoring?wsid=/subscriptions/{subscription_id}"
          f"/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices"
          f"/workspaces/{workspace_name}")


if __name__ == "__main__":
    main()
