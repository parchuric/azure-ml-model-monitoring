import os
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import Data, Model

SUBSCRIPTION_ID = os.environ.get('AZURE_SUBSCRIPTION_ID')
RESOURCE_GROUP = os.environ.get('AZURE_RESOURCE_GROUP')
WORKSPACE = os.environ.get('AZURE_ML_WORKSPACE')

def main():
    if not SUBSCRIPTION_ID or not RESOURCE_GROUP or not WORKSPACE:
        raise SystemExit('Please set AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP and AZURE_ML_WORKSPACE environment variables')

    ml_client = MLClient(DefaultAzureCredential(), SUBSCRIPTION_ID, RESOURCE_GROUP, WORKSPACE)

    # generate toy training data
    X, y = make_classification(n_samples=2000, n_features=5, n_informative=3, random_state=42)
    cols = [f'feature_{i}' for i in range(X.shape[1])]
    df = pd.DataFrame(X, columns=cols)
    df['label'] = y
    train_csv = 'train.csv'
    df.to_csv(train_csv, index=False)

    # register dataset (handle SDK signature differences)
    try:
        dataset = ml_client.data.create_or_update(
            name='tx_training_dataset',
            path=train_csv
        )
    except TypeError:
        # Some SDK versions expect an entity object with a name set
        data_asset = Data(name='tx_training_dataset', path=train_csv, type='uri_file', description='toy training dataset')
        dataset = ml_client.data.create_or_update(data_asset)

    # train a simple model locally and register
    X_train, X_valid, y_train, y_valid = train_test_split(df[cols], df['label'], test_size=0.2, random_state=42)
    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X_train, y_train)
    joblib.dump(model, 'rf_model.joblib')

    # register model (handle SDK signature differences)
    try:
        ml_client.models.create_or_update(
            name='tx_rf_model',
            path='rf_model.joblib'
        )
    except TypeError:
        model_asset = Model(name='tx_rf_model', path='rf_model.joblib', description='RandomForest model')
        ml_client.models.create_or_update(model_asset)

    print('Training data and model registered.')


if __name__ == '__main__':
    main()
