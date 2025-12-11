import os
import pandas as pd
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import Data

SUBSCRIPTION_ID = os.environ.get('AZURE_SUBSCRIPTION_ID')
RESOURCE_GROUP = os.environ.get('AZURE_RESOURCE_GROUP')
WORKSPACE = os.environ.get('AZURE_ML_WORKSPACE')

def main():
    if not SUBSCRIPTION_ID or not RESOURCE_GROUP or not WORKSPACE:
        raise SystemExit('Please set AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP and AZURE_ML_WORKSPACE environment variables')

    ml_client = MLClient(DefaultAzureCredential(), SUBSCRIPTION_ID, RESOURCE_GROUP, WORKSPACE)

    # small simulated inference data
    df = pd.DataFrame({
        'feature_0': [0.1, -0.2, 0.3],
        'feature_1': [1.2, 0.2, -0.3],
        'feature_2': [0.5, 0.5, 0.6],
        'feature_3': [0.0, 0.1, -0.1],
        'feature_4': [0.1, 0.2, 0.3]
    })

    local_path = 'inference_batch.csv'
    df.to_csv(local_path, index=False)

    # Register the inference CSV as a data asset (SDK will upload the file)
    try:
        ml_client.data.create_or_update(
            name='inference_batch_csv',
            path=local_path,
        )
        print('Uploaded and registered inference CSV as data asset: inference_batch_csv')
    except TypeError:
        # Some SDK versions expect a Data entity
        datastore = os.environ.get('DEFAULT_DATASTORE', 'workspaceblobstore')
        cloud_path = f'azureml://datastores/{datastore}/paths/monitoring/inference-batches/'
        data_asset = Data(name='inference_batch_csv', path=local_path, type='uri_file', description='inference batch')
        ml_client.data.create_or_update(data_asset)
        print('Uploaded and registered inference CSV as data asset: inference_batch_csv')


if __name__ == '__main__':
    main()
