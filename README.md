# ABP Agent

## Setup instructions

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
