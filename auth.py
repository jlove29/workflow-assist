import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore

USER_TOKEN_FILE = "token.json"
OAUTH_CREDS_FILE = "credentials.json"

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


def get_credentials() -> Credentials:
  """Loads or generates user credentials."""
  creds = None
  if os.path.exists(USER_TOKEN_FILE):
    creds = Credentials.from_authorized_user_file(USER_TOKEN_FILE, SCOPES)
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          OAUTH_CREDS_FILE, SCOPES
      )
      creds = flow.run_local_server(port=0)
  with open(USER_TOKEN_FILE, "w") as token:
    token.write(creds.to_json())
  return creds


if __name__ == '__main__':
  get_credentials()
