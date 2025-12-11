import os
from azure.ai.ml import MLClient
from azure.identity import DefaultAzureCredential
import logging

# Configure debug logging for azure SDK HTTP traffic
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('azure_http_debug.log', mode='w', encoding='utf-8')
fmt = logging.Formatter('%(asctime)s %(name)s %(levelname)s: %(message)s')
fh.setFormatter(fmt)
logger.addHandler(fh)
for lname in ('azure.core.pipeline.policies.http_logging_policy', 'azure.ai.ml', 'azure.core.pipeline.transport'):
    logging.getLogger(lname).setLevel(logging.DEBUG)

from monitoring_setup import create_drift_signal, create_monitor_schedule

SUBSCRIPTION_ID = os.environ.get('AZURE_SUBSCRIPTION_ID')
RESOURCE_GROUP = os.environ.get('AZURE_RESOURCE_GROUP')
WORKSPACE = os.environ.get('AZURE_ML_WORKSPACE')

def main():
    if not SUBSCRIPTION_ID or not RESOURCE_GROUP or not WORKSPACE:
        raise SystemExit('Please set AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP and AZURE_ML_WORKSPACE environment variables')

    ml_client = MLClient(DefaultAzureCredential(), SUBSCRIPTION_ID, RESOURCE_GROUP, WORKSPACE)

    training_dataset_name = 'tx_training_dataset'
    datastore_name = os.environ.get('DEFAULT_DATASTORE')
    if not datastore_name:
        raise SystemExit('Please set DEFAULT_DATASTORE environment variable')
    target_path = f'azureml://datastores/{datastore_name}/paths/monitoring/inference-batches/'

    # Create drift signal using our helper
    signal = create_drift_signal(
        ml_client=ml_client,
        name='tx_data_drift_signal',
        baseline_dataset=training_dataset_name,
        datastore_name=datastore_name,
        path='monitoring/inference-batches/',
        features=['feature_0','feature_1','feature_2','feature_3','feature_4'],
        metric='population_stability_index',
        threshold=0.05
    )

    # Try to call the ML client's create_or_update directly to capture returned objects
    created_signal = None
    if hasattr(ml_client, 'monitor_signals') and hasattr(ml_client.monitor_signals, 'create_or_update'):
        try:
            created_signal = ml_client.monitor_signals.create_or_update(signal)
        except Exception as e:
            print('Warning: creating signal via ML client raised:', e)

    # Create monitor schedule (use the helper to build the schedule object)
    schedule = create_monitor_schedule(
        ml_client=ml_client,
        name='tx_daily_monitor',
        signal_name=getattr(signal, 'name', None),
        frequency='Day',
        description='Daily monitor for transaction model input drift'
    )

    created_schedule = None
    if hasattr(ml_client, 'monitor_schedules') and hasattr(ml_client.monitor_schedules, 'create_or_update'):
        try:
            created_schedule = ml_client.monitor_schedules.create_or_update(schedule)
        except Exception as e:
            print('Warning: creating schedule via ML client raised:', e)

    # Print captured details to help locate resources and always persist debug info
    def dump_debug(obj, filename_prefix):
        import json, traceback
        debug = {}
        try:
            debug['type'] = type(obj).__name__ if obj is not None else 'NoneType'
            debug['repr'] = repr(obj)
            # as_dict if available
            if obj is not None and hasattr(obj, 'as_dict'):
                try:
                    debug['as_dict'] = obj.as_dict()
                except Exception as e:
                    debug['as_dict_error'] = str(e)
            # __dict__ if available
            if obj is not None and hasattr(obj, '__dict__'):
                try:
                    # convert non-serializable values to str
                    debug['__dict__'] = {k: (v if isinstance(v, (str, int, float, bool, list, dict, type(None))) else str(v)) for k, v in obj.__dict__.items()}
                except Exception as e:
                    debug['__dict___error'] = str(e)
        except Exception as e:
            debug['inspect_error'] = traceback.format_exc()

        # write JSON and a plain text dump
        try:
            with open(f'{filename_prefix}_debug.json', 'w', encoding='utf-8') as jf:
                json.dump(debug, jf, indent=2, default=str)
        except Exception as e:
            print(f'Failed to write {filename_prefix}_debug.json:', e)
        try:
            with open(f'{filename_prefix}_debug.txt', 'w', encoding='utf-8') as tf:
                tf.write('TYPE:\n')
                tf.write(debug.get('type', ''))
                tf.write('\n\nREPR:\n')
                tf.write(debug.get('repr', ''))
                tf.write('\n\nAS_DICT:\n')
                tf.write(str(debug.get('as_dict', '')))
                tf.write('\n\n__DICT__:\n')
                tf.write(str(debug.get('__dict__', '')))
        except Exception as e:
            print(f'Failed to write {filename_prefix}_debug.txt:', e)

    dump_debug(created_signal, 'created_signal')

    dump_debug(created_schedule, 'created_schedule')

    print('Monitor and schedule created.')


if __name__ == '__main__':
    main()
