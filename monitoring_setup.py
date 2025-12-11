from dataclasses import dataclass
from typing import List, Optional


@dataclass
class DataDriftSignal:
    name: str
    baseline_data: str
    target_data: str
    features: List[str]
    metric: str
    threshold: float


@dataclass
class MonitorSchedule:
    name: str
    signals: List[str]
    frequency: str
    description: Optional[str] = None


def create_drift_signal(ml_client, name: str, baseline_dataset: str, datastore_name: str, path: str,
                        features: List[str], metric: str, threshold: float):
    """Create a DataDriftSignal object and call the client's monitor_signals.create_or_update.

    This function builds lightweight objects compatible with the unit tests in `tests/test_monitoring_setup.py`.
    It returns the created DataDriftSignal instance.
    """
    # Construct baseline and target references similar to examples in the repo docs
    baseline_ref = f'azureml:{baseline_dataset}'
    target_ref = f'azureml://datastores/{datastore_name}/paths/{path.rstrip("/")}/'

    signal = DataDriftSignal(
        name=name,
        baseline_data=baseline_ref,
        target_data=target_ref,
        features=features,
        metric=metric,
        threshold=threshold,
    )

    # Call the ML client's monitor_signals.create_or_update if available
    if hasattr(ml_client, 'monitor_signals') and hasattr(ml_client.monitor_signals, 'create_or_update'):
        ml_client.monitor_signals.create_or_update(signal)

    return signal


def create_monitor_schedule(ml_client, name: str, signal_name: str, frequency: str, description: Optional[str] = None):
    """Create a MonitorSchedule object and call the client's monitor_schedules.create_or_update.

    Returns the created MonitorSchedule instance.
    """
    schedule = MonitorSchedule(
        name=name,
        signals=[signal_name],
        frequency=frequency,
        description=description,
    )

    if hasattr(ml_client, 'monitor_schedules') and hasattr(ml_client.monitor_schedules, 'create_or_update'):
        ml_client.monitor_schedules.create_or_update(schedule)

    return schedule
