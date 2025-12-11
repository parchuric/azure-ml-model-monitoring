"""
Check Azure ML monitor child endpoints (/monitorSchedules and /monitorSignals)
for a list of api-versions using DefaultAzureCredential. Prints SDK version,
MLClient attributes, and HTTP responses for each api-version.

Usage: run inside the repo venv where Azure credentials are available.
"""
import sys
import json
import urllib.parse
from typing import List

from azure.identity import DefaultAzureCredential
import requests
import logging
from http.client import HTTPConnection

try:
    import azure.ai.ml as azure_ai_ml
    from azure.ai.ml import MLClient
except Exception:
    azure_ai_ml = None
    MLClient = None


API_VERSIONS = [
    "2025-10-01-preview",
    "2025-04-01-preview",
    "2024-08-01-preview",
    "2024-06-01-preview",
    "2024-01-01-preview",
    "2023-10-01",
    "2023-10-01-preview",
]


def get_env_var(name: str) -> str:
    import os

    val = os.environ.get(name)
    if not val:
        print(f"Environment variable {name} not set. Please set it (e.g. in set_env.ps1).")
        sys.exit(2)
    return val


def build_workspace_resource_id(subscription: str, resource_group: str, workspace: str) -> str:
    return f"/subscriptions/{subscription}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{workspace}"


def get_arm_token() -> str:
    cred = DefaultAzureCredential()
    token = cred.get_token("https://management.azure.com/.default")
    return token.token


def call_arm(resource_id: str, api_version: str, path: str) -> dict:
    token = get_arm_token()
    base = "https://management.azure.com"
    url = urllib.parse.urljoin(base, f"{resource_id}/{path}")
    params = {"api-version": api_version}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.get(url, params=params, headers=headers)
    try:
        body = resp.json()
    except Exception:
        body = {"text": resp.text}
    return {"status_code": resp.status_code, "body": body, "url": resp.url}


def main(argv: List[str]):
    # configure logging to file for HTTP/debug traces
    import os
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    log_path = os.path.join(repo_root, "azure_http_debug.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        filemode="w",
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    # enable http.client debug output
    HTTPConnection.debuglevel = 1
    # enable requests logging
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.DEBUG)
    logging.getLogger("azure.core.pipeline.transport").setLevel(logging.DEBUG)

    # also echo some logs to stdout
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    logging.getLogger().addHandler(console)

    subscription = get_env_var("AZURE_SUBSCRIPTION_ID")
    resource_group = get_env_var("AZURE_RESOURCE_GROUP")
    workspace = get_env_var("AZURE_ML_WORKSPACE")

    print("azure-ai-ml installed:", getattr(azure_ai_ml, "__version__", "(not installed)"))
    if MLClient is not None:
        print("MLClient has attributes:", [a for a in dir(MLClient) if not a.startswith("__")][:40])
    else:
        print("MLClient import failed or azure-ai-ml not installed in this environment.")

    resource_id = build_workspace_resource_id(subscription, resource_group, workspace)
    print("Target workspace resource id:", resource_id)

    paths = ["monitorSchedules", "monitorSignals"]

    results = {}
    for api in API_VERSIONS:
        print("\n=== api-version:", api)
        results[api] = {}
        for p in paths:
            print(f"Calling {p} ...", end=" ")
            r = call_arm(resource_id, api, p)
            print(r["status_code"])
            try:
                print(json.dumps(r["body"], indent=2)[:1000])
            except Exception:
                print(str(r["body"])[:1000])
            results[api][p] = r

    out_path = "monitor_api_check_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults written to {out_path}")


if __name__ == "__main__":
    main(sys.argv[1:])
