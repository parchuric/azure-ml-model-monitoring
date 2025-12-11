# Azure ML Model Monitoring: Data & Feature Drift Detection


## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [End-to-end Example (recommended)](#end-to-end-example-recommended)
    - [Create environment & install deps](#create-environment--install-deps)
    - [Train a toy model & register dataset/model](#train-a-toy-model--register-datasetmodel)
    - [Upload simulated inference data to datastore](#upload-simulated-inference-data-to-datastore)
    - [Create Data Collector & Drift Signal](#create-data-collector--drift-signal)
    - [Create Monitor Schedule and run](#create-monitor-schedule-and-run)
    - [View results in Azure ML Studio](#view-results-in-azure-ml-studio)
4. [Full sample scripts](#full-sample-scripts)
5. [Requirements & run commands](#requirements--run-commands)
6. [Validation (syntax & tests)](#validation-syntax--tests)
7. [CI Integration (GitHub Actions)](#ci-integration-github-actions)
8. [Summary of Chat Conversation](#summary-of-chat-conversation)
9. [References & Azure documentation](#references--azure-documentation)

---


## Overview

Azure Machine Learning provides built-in model monitoring features to automate data and feature drift detection. This enables you to:

- Automatically collect inference data and compare it to training baselines
- Run scheduled drift detection (daily/weekly/monthly)
- Configure thresholds and receive alerts (email, webhooks, Teams)
- Log drift metrics to the Model Catalog/Registry for governance and lineage


## Prerequisites

- An Azure subscription with permissions to create resources
- A Resource Group and an Azure ML Workspace
- Azure CLI with the `az ml` extension (optional but useful)
- Python 3.8+ and a virtual environment
- Python packages: `azure-ai-ml` (SDK v2), `azure-identity`, `pandas`, `scikit-learn`
- An Azure Blob/ADLS datastore attached to the workspace (we'll use it to store simulated inference data)


## End-to-end Example (recommended)

This example covers:

- Creating a simple training dataset and training a toy model locally
- Registering the dataset and model in Azure ML
- Uploading simulated inference data to a datastore path
- Creating a Data Collector and Data Drift signal
- Scheduling a Monitor to run the detection and viewing results


### Create environment & install deps

Open PowerShell and run:

```powershell
# create venv
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# upgrade pip and install deps
python -m pip install --upgrade pip
pip install azure-ai-ml azure-identity pandas scikit-learn
```


Set these environment variables (or replace inline in scripts):

```powershell
$env:AZURE_SUBSCRIPTION_ID = "<your-subscription-id>"
$env:AZURE_RESOURCE_GROUP = "<your-resource-group>"
$env:AZURE_ML_WORKSPACE = "<your-workspace>"
```


### Train a toy model & register dataset/model

Create `train_register.py` (full script below). In short, it will:

- Generate a toy classification dataset using scikit-learn
- Save the training CSV locally
- Register the CSV as a dataset in Azure ML
- Train a simple model and register it


High level snippet (see full script in "Full sample scripts"):

```python
# generate toy data -> train.csv
# use MLClient to register dataset and model
```


### Upload simulated inference data to datastore

We simulate scoring data (transaction/online data) that represents production input. Upload it to a datastore path the monitor will use as the target data.

Use the Azure ML SDK to upload the CSV to a datastore location. Example (see full scripts):

```python
# ml_client.datastores.upload('my_datastore', target_path, local_path)
```


### Create Data Collector & Drift Signal

Using the Azure ML SDK, create a Data Collector resource (or configure the monitor to read files from the datastore path). Create a drift signal that references the registered training dataset (baseline) and the datastore path (target).

Example (simplified):

```python
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import DataDriftSignal, MonitorSchedule

ml_client = MLClient(DefaultAzureCredential(), subscription_id, resource_group, workspace)

# create DataDriftSignal referencing baseline dataset and target path
signal = DataDriftSignal(
    name='tx-feature-drift',
    baseline_data=f'azureml:{training_dataset_id}',
    target_data=f'azureml://datastores/{datastore_name}/paths/monitoring/',
    features=['amount','time_delta','merchant_id'],
    metric='population_stability_index',
    threshold=0.05
)

ml_client.monitor_signals.create_or_update(signal)
```


Note: The exact class names for the SDK can differ across SDK patch releases; if a symbolic name is not available, you can create the equivalent monitor resources via the Studio UI and the REST API.


### Create Monitor Schedule and run

Create a MonitorSchedule to run the configured signal on a cadence. You can create it to run immediately (for testing) and then schedule recurring runs.

Example (simplified):

```python
schedule = MonitorSchedule(
    name='tx-monitor-weekly',
    signals=[signal.name],
    frequency='Day',
    description='Daily data/feature drift monitor for transactions',
    actions=[{'type':'alert','channels':['email','webhook'] }]
)

ml_client.monitor_schedules.create_or_update(schedule)
```


After creating the schedule, the first run may be started by the service depending on the cadence. For testing you can trigger an ad-hoc run from the Studio UI or call a run API (if available in your SDK version).


### View results in Azure ML Studio

- Open Azure ML Studio -> Models / Model Catalog -> select model -> Monitoring tab.
- Review drift metrics, per-feature charts, and alerts.
- You can also pull results via the SDK or REST API for automated reporting and ingestion into your Model Catalog.


## Full sample scripts

Below are the minimal scripts used in this example. Save each into the project folder and run them in order.

1. `train_register.py` - generate data, train, register dataset and model

```python
import os
import pandas as pd
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

SUBSCRIPTION_ID = os.environ.get('AZURE_SUBSCRIPTION_ID')
RESOURCE_GROUP = os.environ.get('AZURE_RESOURCE_GROUP')
WORKSPACE = os.environ.get('AZURE_ML_WORKSPACE')

ml_client = MLClient(DefaultAzureCredential(), SUBSCRIPTION_ID, RESOURCE_GROUP, WORKSPACE)

# generate toy training data
X, y = make_classification(n_samples=2000, n_features=5, n_informative=3, random_state=42)
cols = [f'feature_{i}' for i in range(X.shape[1])]
df = pd.DataFrame(X, columns=cols)
df['label'] = y
train_csv = 'train.csv'
df.to_csv(train_csv, index=False)

# register dataset
dataset = ml_client.data.create_or_update(
    name='tx_training_dataset',
    path=train_csv
)

# train a simple model
X_train, X_valid, y_train, y_valid = train_test_split(df[cols], df['label'], test_size=0.2, random_state=42)
model = RandomForestClassifier(n_estimators=50, random_state=42)
model.fit(X_train, y_train)
joblib.dump(model, 'rf_model.joblib')

# register model
ml_client.models.create_or_update(
    name='tx_rf_model',
    path='rf_model.joblib'
)

print('Training data and model registered.')
```


2. `upload_inference.py` - create simulated inference CSV and upload to datastore

```python
import os
import pandas as pd
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential

SUBSCRIPTION_ID = os.environ.get('AZURE_SUBSCRIPTION_ID')
RESOURCE_GROUP = os.environ.get('AZURE_RESOURCE_GROUP')
WORKSPACE = os.environ.get('AZURE_ML_WORKSPACE')

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

# upload to a path in default datastore
datastore_name = 'workspaceblobstore'  # replace with your datastore name
target_path = 'monitoring/inference-batches/'

ml_client.datastores.upload(
    name=datastore_name,
    path=target_path,
    local_path=local_path,
    overwrite=True
)

print('Uploaded inference data to datastore path: ', target_path)
```


3. `create_monitor.py` - create drift signal and schedule (SDK names may vary)

```python
import os
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
from azure.ai.ml.entities import DataDriftSignal, MonitorSchedule

SUBSCRIPTION_ID = os.environ.get('AZURE_SUBSCRIPTION_ID')
RESOURCE_GROUP = os.environ.get('AZURE_RESOURCE_GROUP')
WORKSPACE = os.environ.get('AZURE_ML_WORKSPACE')

ml_client = MLClient(DefaultAzureCredential(), SUBSCRIPTION_ID, RESOURCE_GROUP, WORKSPACE)

# IDs/names from previous steps
training_dataset_name = 'tx_training_dataset'
datastore_name = 'workspaceblobstore'
target_path = f'azureml://datastores/{datastore_name}/paths/monitoring/inference-batches/'

# Create a drift signal (API surface may vary; adjust to your SDK version)
signal = DataDriftSignal(
    name='tx_data_drift_signal',
    baseline_data=f'azureml:{training_dataset_name}',
    target_data=target_path,
    features=['feature_0','feature_1','feature_2','feature_3','feature_4'],
    metric='population_stability_index',
    threshold=0.05
)

ml_client.monitor_signals.create_or_update(signal)

# Create monitor schedule
schedule = MonitorSchedule(
    name='tx_daily_monitor',
    signals=[signal.name],
    frequency='Day',
    description='Daily monitor for transaction model input drift'
)

ml_client.monitor_schedules.create_or_update(schedule)

print('Monitor and schedule created.')
```


## Requirements & run commands

Add this to `requirements.txt` if you maintain one:

```
azure-ai-ml>=1.10.0
azure-identity
pandas
scikit-learn
joblib
```


Run the example (PowerShell):

```powershell
# activate venv
.\.venv\Scripts\Activate.ps1

# train and register
python train_register.py

# upload inference data
python upload_inference.py

# create the monitor
python create_monitor.py
```


## Validation (syntax & tests)

We include quick validation steps and unit tests to ensure the helper scripts are syntactically correct and behave as expected in isolation.

- Syntax checks: Use Python's built-in compile check to validate scripts don't contain syntax errors:

```powershell
# from project root
python -m py_compile monitoring_setup.py tests/test_monitoring_setup.py
```

- Unit tests: A small pytest-based test suite is provided at `tests/test_monitoring_setup.py`. It uses lightweight dummy MLClient objects to verify that `create_drift_signal` and `create_monitor_schedule` call the SDK surface correctly and return objects with expected attributes.

Run tests locally:

```powershell
pip install pytest
pytest -q
```


## CI Integration (GitHub Actions)

A GitHub Actions workflow ` .github/workflows/monitoring-ci.yml` is included to run the unit tests on push or pull request to `main`.

Workflow steps:

- Checkout the repository
- Set up Python 3.10
- Install pytest
- Run pytest

This gives immediate feedback on syntax or unit-test regressions when contributors modify monitoring helper scripts.

## Summary of Chat Conversation

Azure ML's built-in Model Monitoring (Data Collector, Monitor Schedules, drift signals, Model Catalog integration, and alerting) allows teams to replace quarterly custom runs with automated, scheduled drift detection that integrates with the Model Catalog and alerting channels.

---

For help adapting this to your environment (datastore names, exact SDK class names, or automation into your CI/CD), tell me which parts you want automated and I will update the scripts to match your workspace.


## References & Azure documentation

Official Azure documentation and resources referenced while building this guide:

- Azure Machine Learning overview — [Azure ML overview](https://learn.microsoft.com/azure/machine-learning/overview)
- Azure ML model monitoring (data drift & model monitoring) — [Model monitoring guide](https://learn.microsoft.com/azure/machine-learning/how-to-monitoring)
- Monitor model drift in Azure ML (guide with SDK examples) — [Monitor model drift](https://learn.microsoft.com/azure/machine-learning/how-to-monitor-drift)
- Data collection for model monitoring — [Data collection for monitoring](https://learn.microsoft.com/azure/machine-learning/how-to-data-collection)
- Azure ML Python SDK v2 (API overview) — [azure-ai-ml SDK v2 docs](https://learn.microsoft.com/python/api/overview/azure/ai-ml)
- Create and manage datastores — [Access data & datastores](https://learn.microsoft.com/azure/machine-learning/how-to-access-data)
- Alerts & notifications (Azure Monitor & Action Groups) — [Azure Monitor alerts overview](https://learn.microsoft.com/azure/azure-monitor/alerts/alerts-overview)

Useful SDK references (Azure ML SDK v2)

- `MLClient` (core client for workspace operations) — https://learn.microsoft.com/python/api/azure.ai.ml/azure.ai.ml.mlclient?view=azure-python
- Monitoring/Signals/Monitors (see the monitoring guide and SDK examples) — [Monitor model drift (Python examples)](https://learn.microsoft.com/azure/machine-learning/how-to-monitor-drift?tabs=python)
- Data collection & ingestion examples — [Data collection for monitoring (examples)](https://learn.microsoft.com/azure/machine-learning/how-to-data-collection)

Studio UI quick pointers (where to click)

- Data collection: Studio -> Data collection (or Monitor -> Data Collection) -> Create Data Collector -> choose source (endpoint, datastore path) and schema mapping.
- Create drift signal and schedule: Studio -> Models / Model Catalog -> select model -> Monitoring tab -> Create signal or Monitor -> add Drift signal -> choose baseline dataset and target source -> configure features and thresholds -> Save and schedule.

Use these links for the most up-to-date API surfaces and Studio screenshots; SDK names and fields may change between SDK patch versions so consult the Python SDK docs for exact class names and examples.
