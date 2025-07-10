# Workflow assistant

## Setup instructions

### Get API access

1. Go to https://console.cloud.google.com/apis/dashboard. Note that you must use a Cloud account tied to the **same** email that you want to triage.
2. Enable Calendar API and Gmail API.

### Create OAuth credentials

In the Cloud console:
1. Go to `Credentials` -> `Create credentials` -> `OAuth client ID`.
2. Select application type `Desktop app`.
3. Create
4. Where clients are listed, click download on the new client (far right)
5. Rename it `credentials.json`
6. Move it into this directory (top-level).

### Get a Gemini API key

1. Go to https://aistudio.google.com/apikey
2. Create a key
3. In terminal, set `GEMINI_API_KEY={your key}`

### Set up environment

```sh
python3 -m venv env
source env/bin/activate
pip3 install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib google-genai mypy
```

Ensure you have your `GEMINI_API_KEY` environment variable set.


## Run triage workflow

```sh
python3 agent.py
```
