<#
Loads variables from .env into the PowerShell session as environment variables.
Usage: .\set_env.ps1
#>
$envFile = Join-Path -Path $PSScriptRoot -ChildPath '.env'
if (-Not (Test-Path $envFile)) {
    Write-Error ".env file not found at $envFile"
    exit 1
}

Get-Content $envFile | ForEach-Object {
    if ($_ -match '^[\s#]' -or $_ -eq '') { return }
    $parts = $_ -split '=', 2
    if ($parts.Length -eq 2) {
        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        Write-Host "Setting env: $name"
        Set-Item -Path Env:$name -Value $value
    }
}

Write-Host "Environment variables loaded from .env"
