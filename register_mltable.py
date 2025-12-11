"""register_mltable.py

Registers training and inference data as MLTable assets for model monitoring.

MLTable format is required for Azure ML model monitoring signals.

Run after loading env vars:
    .\\set_env.ps1
    .\\.venv\\Scripts\\Activate.ps1
    python register_mltable.py
"""

import os
import shutil
from azure.identity import DefaultAzureCredential
from azure.ai.ml import MLClient
from azure.ai.ml.entities import Data
from azure.ai.ml.constants import AssetTypes


def create_mltable_yaml(csv_filename: str, output_dir: str) -> str:
    """Create an MLTable YAML file that references a CSV."""
    os.makedirs(output_dir, exist_ok=True)
    
    mltable_content = f"""type: mltable
paths:
  - file: ./{csv_filename}
transformations:
  - read_delimited:
      delimiter: ','
      header: all_files_same_headers
      encoding: utf8
"""
    yaml_path = os.path.join(output_dir, "MLTable")
    with open(yaml_path, "w") as f:
        f.write(mltable_content)
    
    return output_dir


def main():
    subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
    resource_group = os.environ["AZURE_RESOURCE_GROUP"]
    workspace_name = os.environ["AZURE_ML_WORKSPACE"]

    ml_client = MLClient(
        DefaultAzureCredential(),
        subscription_id=subscription_id,
        resource_group_name=resource_group,
        workspace_name=workspace_name,
    )
    print(f"Connected to workspace: {workspace_name}")

    # -------------------------------------------------------------------------
    # 1. Register training data as MLTable
    # -------------------------------------------------------------------------
    train_csv = "train.csv"
    train_mltable_dir = "train_mltable"
    
    if os.path.exists(train_csv):
        print(f"\nCreating MLTable for training data...")
        
        # Create MLTable directory with YAML and copy CSV
        if os.path.exists(train_mltable_dir):
            shutil.rmtree(train_mltable_dir)
        os.makedirs(train_mltable_dir)
        shutil.copy(train_csv, os.path.join(train_mltable_dir, train_csv))
        create_mltable_yaml(train_csv, train_mltable_dir)
        
        # Register as MLTable data asset
        train_data = Data(
            name="tx_training_mltable",
            path=train_mltable_dir,
            type=AssetTypes.MLTABLE,
            description="Training dataset as MLTable for model monitoring",
        )
        registered_train = ml_client.data.create_or_update(train_data)
        print(f"✓ Registered: {registered_train.name} (version {registered_train.version})")
    else:
        print(f"✗ {train_csv} not found. Run train_register.py first.")

    # -------------------------------------------------------------------------
    # 2. Register inference data as MLTable
    # -------------------------------------------------------------------------
    inference_csv = "inference_batch.csv"
    inference_mltable_dir = "inference_mltable"
    
    if os.path.exists(inference_csv):
        print(f"\nCreating MLTable for inference data...")
        
        # Create MLTable directory with YAML and copy CSV
        if os.path.exists(inference_mltable_dir):
            shutil.rmtree(inference_mltable_dir)
        os.makedirs(inference_mltable_dir)
        shutil.copy(inference_csv, os.path.join(inference_mltable_dir, inference_csv))
        create_mltable_yaml(inference_csv, inference_mltable_dir)
        
        # Register as MLTable data asset
        inference_data = Data(
            name="tx_inference_mltable",
            path=inference_mltable_dir,
            type=AssetTypes.MLTABLE,
            description="Inference batch data as MLTable for model monitoring",
        )
        registered_inference = ml_client.data.create_or_update(inference_data)
        print(f"✓ Registered: {registered_inference.name} (version {registered_inference.version})")
    else:
        print(f"✗ {inference_csv} not found. Run upload_inference.py first.")

    print("\n" + "=" * 50)
    print("Done! Now update create_monitor_sdk.py to use:")
    print("  - Reference data: azureml:tx_training_mltable:1")
    print("  - Production data: azureml:tx_inference_mltable:1")


if __name__ == "__main__":
    main()
