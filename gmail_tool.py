import base64
import dataclasses
import datetime
from typing import Any, Callable

import auth as auth_lib

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

GmailService = Any


@dataclasses.dataclass
class EmailMessage:
  subject: str
  sender: str
  snippet: str
  body: str
  date: str

  @classmethod
  def from_json(cls, data: dict) -> 'EmailMessage':
    headers = data["payload"]["headers"]
    subject = (h["value"] for h in headers if h["name"].lower() == "subject")
    subject = next(subject, '')
    sender = (h["value"] for h in headers if h["name"].lower() == "from")
    sender = next(sender, '')
    date_str = (h["value"] for h in headers if h["name"].lower() == "date")
    date_str = next(date_str, '')
    if '(' in date_str:
      date_str = date_str.split("(")[0].strip()
    date_obj = datetime.datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    snippet = data.get("snippet", "")
    payload = data.get("payload", {})
    body = ""
    if "parts" in payload:
      for part in payload["parts"]:
        if part["mimeType"] == "text/plain" and "data" in part["body"]:
          body = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8")
          break
    elif "data" in payload.get("body", {}):
      body = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")
    return EmailMessage(subject, sender, snippet, body, date_obj)


def get_gmail_service(credentials: Credentials) -> GmailService | None:
  try:
    service = build('gmail', 'v1', credentials=credentials)
    return service
  except HttpError as error:
    print(f'An error occurred: {error}')
    return None


def get_emails_impl(
    service: "GmailService",
    *,
    num_emails: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    unread_only: bool = False,
) -> list[EmailMessage]:
    """Gets emails from the user's inbox."""
    if not (num_emails or start_date or end_date):
      # If nothing is provided, fetch a reasonable number of emails.
      num_emails = 100

    try:
      query = ''
      if start_date:
        query += f" after:{start_date.replace('-', '/')}"
      if end_date:
        query += f" before:{end_date.replace('-', '/')}"

      emails = []
      page_token = None
      label_ids = ['INBOX']
      if unread_only:
        label_ids.append('UNREAD')
      while True:
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                labelIds=label_ids,
                pageToken=page_token)
            .execute()
        )
        messages_info = results.get("messages", [])

        if not messages_info:
          break

        for msg_info in messages_info:
          if num_emails is not None and len(emails) >= num_emails:
            return emails

          msg = (
              service.users()
              .messages()
              .get(userId="me", id=msg_info["id"], format="full")
              .execute()
          )
          emails.append(EmailMessage.from_json(msg))

        # 4. Get the next page token to continue the loop.
        page_token = results.get("nextPageToken")
        if not page_token:
          break

      return emails

    except HttpError as error:
      print(f"An error occurred: {error}")
      return []


def make_get_emails_tool(credentials: Credentials) -> Callable:
  service = get_gmail_service(credentials)

  def get_emails(
      num_emails: int | None = None,
      start_date: str | None = None,
      end_date: str | None = None,
      unread_only: bool = False,
  ):
    """Gets emails from the user's inbox.

    Args:
      service: An authenticated Gmail API service object.
      num_emails: A limit on the total number of emails to fetch.
      start_date: The start date to filter emails from (format YYYY-MM-DD).
      end_date: The end date to filter emails to (format YYYY-MM-DD).
      unread_only: Whether to filter to unread emails.

    Returns:
      A list of email messages.
    """
    emails = get_emails_impl(
        service,
        num_emails=num_emails,
        start_date=start_date,
        end_date=end_date,
        unread_only=unread_only,
    )
    return emails

  return get_emails



if __name__ == '__main__':
  service = get_gmail_service(auth_lib.get_credentials())
  emails = get_emails_impl(service, num_emails=10)
  for e in emails:
    print(e.subject)
