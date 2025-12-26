# Google Cloud CLI Cheatsheet for Gen AI

> **Your gcloud path:** `/home/gyasis/google-cloud-sdk/bin/gcloud`
> **Project:** `gen-lang-client-0887898557`
> **Account:** `gyasis@gmail.com`

---

## Quick Setup

```bash
# Add to PATH (already added to ~/.bashrc)
export PATH="$PATH:/home/gyasis/google-cloud-sdk/bin"

# Or use alias
alias gcloud='/home/gyasis/google-cloud-sdk/bin/gcloud'
```

---

## Authentication & Config

```bash
# Check current auth
gcloud auth list

# Login (browser opens)
gcloud auth login

# Login for application default credentials
gcloud auth application-default login

# Set active account
gcloud config set account gyasis@gmail.com

# Set default project
gcloud config set project gen-lang-client-0887898557

# View all config
gcloud config list

# View specific property
gcloud config get-value project
```

---

## Project Management

```bash
# List all projects
gcloud projects list

# Create new project
gcloud projects create my-new-project --name="My New Project"

# Set default project
gcloud config set project PROJECT_ID

# Describe project
gcloud projects describe gen-lang-client-0887898557

# Delete project (careful!)
gcloud projects delete PROJECT_ID
```

---

## API Management

```bash
# List enabled APIs
gcloud services list --enabled

# List all available APIs
gcloud services list --available | grep -i "generative\|vertex\|ai"

# Enable an API
gcloud services enable generativelanguage.googleapis.com
gcloud services enable aiplatform.googleapis.com  # Vertex AI

# Disable an API
gcloud services disable SERVICE_NAME
```

---

## Billing

```bash
# List billing accounts
gcloud billing accounts list

# Check project billing
gcloud billing projects describe gen-lang-client-0887898557

# Link billing to project
gcloud billing projects link PROJECT_ID --billing-account=ACCOUNT_ID

# Unlink billing (careful - disables paid APIs)
gcloud billing projects unlink PROJECT_ID
```

---

## Quotas & Limits

```bash
# Install alpha commands (one-time)
gcloud components install alpha

# List quotas for Generative Language API
gcloud alpha services quota list \
  --service=generativelanguage.googleapis.com \
  --project=gen-lang-client-0887898557

# List Vertex AI quotas
gcloud alpha services quota list \
  --service=aiplatform.googleapis.com

# Request quota increase (opens browser)
# Go to: https://console.cloud.google.com/iam-admin/quotas
```

---

## Vertex AI Commands

```bash
# Enable Vertex AI
gcloud services enable aiplatform.googleapis.com

# List available models
gcloud ai models list --region=us-central1

# List endpoints
gcloud ai endpoints list --region=us-central1

# Describe a model
gcloud ai models describe MODEL_ID --region=us-central1

# List custom jobs
gcloud ai custom-jobs list --region=us-central1

# Get model info
gcloud ai models describe publishers/google/models/gemini-1.5-pro \
  --region=us-central1
```

---

## Service Accounts (for automation)

```bash
# List service accounts
gcloud iam service-accounts list

# Create service account
gcloud iam service-accounts create genai-service \
  --display-name="Gen AI Service Account"

# Create key for service account
gcloud iam service-accounts keys create ~/genai-key.json \
  --iam-account=genai-service@PROJECT_ID.iam.gserviceaccount.com

# Grant roles
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:genai-service@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

---

## Useful Filters & Formats

```bash
# JSON output
gcloud projects list --format=json

# Table with specific columns
gcloud projects list --format="table(projectId,name,createTime)"

# Filter results
gcloud services list --enabled --filter="name:generative"

# Get just the value
gcloud config get-value project

# Quiet mode (no prompts)
gcloud services enable aiplatform.googleapis.com --quiet
```

---

## Component Management

```bash
# List installed components
gcloud components list

# Update all components
gcloud components update

# Install specific component
gcloud components install alpha
gcloud components install beta
gcloud components install kubectl

# Remove component
gcloud components remove COMPONENT_ID
```

---

## Logs & Monitoring

```bash
# View recent logs
gcloud logging read "resource.type=aiplatform.googleapis.com" --limit=50

# Stream logs
gcloud logging tail "resource.type=aiplatform.googleapis.com"

# View API usage (last 24h)
gcloud logging read \
  'resource.type="consumed_api" AND resource.labels.service="generativelanguage.googleapis.com"' \
  --limit=100
```

---

## Quick Reference URLs

| Resource | URL |
|----------|-----|
| API Keys | https://aistudio.google.com/app/apikey |
| Cloud Console | https://console.cloud.google.com |
| Quotas | https://console.cloud.google.com/iam-admin/quotas |
| Billing | https://console.cloud.google.com/billing |
| Vertex AI | https://console.cloud.google.com/vertex-ai |
| API Dashboard | https://console.cloud.google.com/apis/dashboard |

---

## Common Issues & Fixes

### "API not enabled"
```bash
gcloud services enable generativelanguage.googleapis.com
```

### "Permission denied"
```bash
# Check your roles
gcloud projects get-iam-policy PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:gyasis@gmail.com"
```

### "Quota exceeded"
```bash
# Check current usage
gcloud alpha services quota list --service=generativelanguage.googleapis.com

# Request increase via Console
# https://console.cloud.google.com/iam-admin/quotas
```

### "gcloud not found"
```bash
# Use full path
/home/gyasis/google-cloud-sdk/bin/gcloud --version

# Or source the path
source /home/gyasis/google-cloud-sdk/path.bash.inc
```

---

## Your Project Quick Commands

```bash
# Set your defaults
gcloud config set project gen-lang-client-0887898557
gcloud config set account gyasis@gmail.com

# Check your APIs
gcloud services list --enabled

# Check billing
gcloud billing projects describe gen-lang-client-0887898557

# View quotas (need alpha)
gcloud components install alpha --quiet
gcloud alpha services quota list --service=generativelanguage.googleapis.com
```
