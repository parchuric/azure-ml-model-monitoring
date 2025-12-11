# Security notes and service principal rotation

This file contains short guidance for handling the `.env` file and rotating service principal credentials used by the demo scripts.

1) Keep secrets out of source control
- Ensure `.env` is listed in `.gitignore` (already added).
- Never commit `.env` or any file containing plain-text credentials to your repository.

2) Use secure stores for CI / production
- For GitHub Actions use GitHub Secrets (Repository -> Settings -> Secrets) and reference them in your workflow.
- For Azure-hosted pipelines use Azure Key Vault and connect it to your pipelines.

3) Rotate the service principal credentials (recommended cadence: quarterly or sooner)
- Create a new client secret for the service principal in Azure AD:

  1. In the Azure Portal, search for "App registrations" and open the app (`aml-monitor-sp`).
  2. Go to "Certificates & secrets" -> "New client secret".
  3. Give it a descriptive name and choose an expiration.
  4. Save the new secret value in your secrets store (or update `.env` locally).

- Update your environment (example PowerShell to update the local `.env`):

```powershell
# Replace the secret value in .env safely using a text editor or script
(Get-Content .env) -replace 'AZURE_CLIENT_SECRET=.*', 'AZURE_CLIENT_SECRET=<new-secret>' | Set-Content .env
```

- After verification, remove the old secret in Azure AD (Certificates & secrets) to fully revoke it.

4) Least privilege
- When creating service principals for automation, grant least-privilege permissions (e.g., "Contributor" scoped to the resource group or resource rather than subscription-wide), and avoid using owner-level privileges unless required.

5) Use managed identities where possible
- For resources running in Azure (VMs, Function Apps, Container Apps), prefer managed identities over long-lived client secrets.

6) Audit and alerts
- Enable Azure AD sign-in logs and conditional access for critical service principals.
- Configure alerts for anomalous sign-in activity.
