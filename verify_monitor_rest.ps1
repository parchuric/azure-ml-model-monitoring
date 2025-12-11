<#
verify_monitor_rest.ps1

Calls the ARM REST endpoints for schedules (which include monitor schedules) under the configured workspace
and prints a friendly summary. Run after loading .env and activating the venv in the same session.

Usage (PowerShell):
  .\set_env.ps1
  .\.venv\Scripts\Activate.ps1
  .\verify_monitor_rest.ps1

This script uses az rest so you must be logged in (az login) or using a service principal via env vars.
#>

if (-not $env:AZURE_SUBSCRIPTION_ID -or -not $env:AZURE_RESOURCE_GROUP -or -not $env:AZURE_ML_WORKSPACE) {
    Write-Error "Please load environment variables first via set_env.ps1"
    exit 1
}

$sub = $env:AZURE_SUBSCRIPTION_ID
$rg = $env:AZURE_RESOURCE_GROUP
$ws = $env:AZURE_ML_WORKSPACE
$wsId = "/subscriptions/$sub/resourceGroups/$rg/providers/Microsoft.MachineLearningServices/workspaces/$ws"

# Use supported API versions for schedules endpoint
$apiVersions = @("2024-04-01", "2024-01-01-preview", "2023-10-01", "2023-06-01-preview", "2023-04-01-preview")

function Show-JsonSummary {
    param($jsonText, $kind)
    
    if (-not $jsonText) {
        Write-Host "  (no response)"
        return
    }
    try {
        $obj = $jsonText | ConvertFrom-Json -ErrorAction Stop
    } catch {
        Write-Host "  (response not JSON or empty): $jsonText"
        return
    }
    if ($obj -is [System.Array]) {
        if ($obj.Length -eq 0) {
            Write-Host "  (no $kind found)"
        } else {
            foreach ($item in $obj) {
                $name = $item.name
                if (-not $name) { $name = $item.id }
                if (-not $name) { $name = "(unnamed)" }
                Write-Host "  - $name"
            }
        }
    } elseif ($obj.value) {
        if ($obj.value.Count -eq 0) { 
            Write-Host "  (no $kind found)" 
        } else { 
            foreach ($item in $obj.value) { 
                $name = $item.name
                $isEnabled = $item.properties.isEnabled
                $triggerType = $item.properties.trigger.triggerType
                Write-Host "  - $name (enabled: $isEnabled, trigger: $triggerType)"
                
                # Check if it is a monitor schedule
                if ($item.properties.action.actionType -eq "CreateMonitor") {
                    Write-Host "    Type: Model Monitor"
                    $monitorDef = $item.properties.action.monitorDefinition
                    if ($monitorDef -and $monitorDef.signals) {
                        Write-Host "    Signals:"
                        foreach ($signalName in $monitorDef.signals.PSObject.Properties.Name) {
                            Write-Host "      - $signalName"
                        }
                    }
                }
            } 
        }
    } else {
        Write-Host "  (single object)"
        $obj | ConvertTo-Json -Depth 4
    }
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Azure ML Workspace: $ws"
Write-Host "=========================================="
Write-Host ""

foreach ($api in $apiVersions) {
    Write-Host ""
    Write-Host "=== API version: $api ==="
    
    # List all schedules (includes monitor schedules)
    $uri = "https://management.azure.com$wsId/schedules?api-version=$api"
    Write-Host "Calling: $uri"
    try {
        $resp = az rest --method get --uri $uri 2>&1
        if ($LASTEXITCODE -ne 0) { 
            Write-Host "  az rest failed: $resp"
            continue 
        }
        Show-JsonSummary -jsonText $resp -kind "schedules"
        # If we got a successful response, no need to try other API versions
        $parsed = $null
        try {
            $parsed = $resp | ConvertFrom-Json -ErrorAction SilentlyContinue
        } catch { }
        if ($resp -and $parsed) {
            Write-Host ""
            Write-Host "Successfully retrieved schedules with API version $api"
            break
        }
    } catch {
        Write-Host "  Error calling schedules: $_"
    }
}

Write-Host ""
Write-Host "=========================================="
Write-Host ""
Write-Host "Done. View monitors in Azure ML Studio:"
$studioUrl = "https://ml.azure.com/monitoring?wsid=" + $wsId
Write-Host "  $studioUrl"
Write-Host ""