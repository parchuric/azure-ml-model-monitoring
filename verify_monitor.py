"""verify_monitor.py

Lists monitor schedules in the configured Azure ML workspace using the Azure ML SDK.

Run in the project venv after loading env vars (set_env.ps1) and activating the venv:

    .\\set_env.ps1
    .\\.venv\\Scripts\\Activate.ps1
    python verify_monitor.py

This will print available monitor schedules or a helpful error if something is wrong.

Prerequisites:
    pip install azure-ai-ml azure-identity
"""

import os
from azure.identity import DefaultAzureCredential
from azure.ai.ml import MLClient


def main():
    # -------------------------------------------------------------------------
    # 1. Get workspace details from environment variables
    # -------------------------------------------------------------------------
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_group = os.environ["AZURE_RESOURCE_GROUP"]
    workspace_name = os.environ["AZURE_ML_WORKSPACE"]

    # -------------------------------------------------------------------------
    # 2. Create MLClient to connect to the workspace
    # -------------------------------------------------------------------------
    print(f"Connecting to workspace: {workspace_name}...")
    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )
    print(f"✓ Connected to workspace: {workspace_name}\n")

    # -------------------------------------------------------------------------
    # 3. List all schedules (monitor schedules are a type of schedule)
    # -------------------------------------------------------------------------
    print("Monitor Schedules:")
    print("-" * 50)

    try:
        schedules = ml_client.schedules.list()
        schedule_count = 0

        for schedule in schedules:
            schedule_count += 1
            print(f"\n- Name: {schedule.name}")
            print(f"  Display Name: {schedule.display_name or '(none)'}")
            print(f"  Provisioning State: {schedule.provisioning_state}")
            print(f"  Is Enabled: {schedule.is_enabled}")

            # Check if this is a monitor schedule
            if hasattr(schedule, "create_monitor") and schedule.create_monitor:
                print("  Type: Model Monitor")
                monitor_def = schedule.create_monitor  # type: ignore[attr-defined]

                # Print monitoring signals if available
                if hasattr(monitor_def, "monitoring_signals") and monitor_def.monitoring_signals:
                    print("  Signals:")
                    for signal_name, signal in monitor_def.monitoring_signals.items():
                        signal_type = type(signal).__name__
                        print(f"    - {signal_name}: {signal_type}")
            else:
                print("  Type: General Schedule")

            # Print trigger info if available
            if hasattr(schedule, "trigger") and schedule.trigger:
                trigger = schedule.trigger
                trigger_type = type(trigger).__name__
                print(f"  Trigger: {trigger_type}")
                if hasattr(trigger, "frequency") and hasattr(trigger, "interval"):
                    print(f"    Frequency: every {trigger.interval} {trigger.frequency}")  # type: ignore[attr-defined]

        if schedule_count == 0:
            print("  No schedules found.")
        else:
            print(f"\n{'=' * 50}")
            print(f"Total schedules: {schedule_count}")

    except Exception as e:
        print(f"Error listing schedules: {type(e).__name__}: {e}")
        raise

    # -------------------------------------------------------------------------
    # 4. Print link to Azure ML Studio
    # -------------------------------------------------------------------------
    print(f"\nView in Azure ML Studio:")
    print(f"  https://ml.azure.com/monitoring?wsid=/subscriptions/{subscription_id}"
          f"/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices"
          f"/workspaces/{workspace_name}")


if __name__ == "__main__":
    main()
