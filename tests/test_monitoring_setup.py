import builtins
import types
import sys
import os

import pytest

# Ensure the project root is on sys.path so tests can import monitoring_setup
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Import the functions to test
from monitoring_setup import create_drift_signal, create_monitor_schedule


class DummyMonitorSignals:
    def __init__(self):
        self.created = []

    def create_or_update(self, obj):
        # store a lightweight dict so assertions don't depend on SDK classes
        self.created.append({
            'name': getattr(obj, 'name', None),
            'baseline': getattr(obj, 'baseline_data', None),
            'target': getattr(obj, 'target_data', None),
            'features': getattr(obj, 'features', None),
            'metric': getattr(obj, 'metric', None),
            'threshold': getattr(obj, 'threshold', None),
        })


class DummyMonitorSchedules:
    def __init__(self):
        self.created = []

    def create_or_update(self, obj):
        self.created.append({
            'name': getattr(obj, 'name', None),
            'signals': getattr(obj, 'signals', None),
            'frequency': getattr(obj, 'frequency', None),
            'description': getattr(obj, 'description', None),
        })


class DummyMLClient:
    def __init__(self):
        self.monitor_signals = DummyMonitorSignals()
        self.monitor_schedules = DummyMonitorSchedules()


def test_create_drift_signal_creates_signal_and_calls_client():
    client = DummyMLClient()
    signal = create_drift_signal(
        ml_client=client,
        name='test-signal',
        baseline_dataset='train_ds',
        datastore_name='ds1',
        path='monitoring/inference',
        features=['f1', 'f2'],
        metric='psi',
        threshold=0.1,
    )

    # Verify returned object has expected values
    assert signal.name == 'test-signal'
    assert 'azureml:train_ds' in signal.baseline_data
    assert 'datastores/ds1' in signal.target_data
    assert signal.features == ['f1', 'f2']
    assert signal.metric == 'psi'
    assert signal.threshold == 0.1

    # Verify client recorded the create_or_update call
    assert len(client.monitor_signals.created) == 1
    created = client.monitor_signals.created[0]
    assert created['name'] == 'test-signal'
    assert created['baseline'] == 'azureml:train_ds'


def test_create_monitor_schedule_calls_client():
    client = DummyMLClient()
    schedule = create_monitor_schedule(
        ml_client=client,
        name='test-schedule',
        signal_name='test-signal',
        frequency='Day',
        description='desc',
    )

    # Basic checks on returned schedule object
    assert schedule.name == 'test-schedule'
    assert schedule.signals == ['test-signal']
    assert schedule.frequency == 'Day'

    # Verify client recorded the call
    assert len(client.monitor_schedules.created) == 1
    created = client.monitor_schedules.created[0]
    assert created['name'] == 'test-schedule'
    assert created['signals'] == ['test-signal']
