import backoff
import base64
import dataclasses
import datetime
from email.message import EmailMessage as EmailMessageBuiltin
import httplib2
import sys
import requests
from typing import Any, Callable, no_type_check

import auth as auth_lib

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build  # type: ignore
from googleapiclient.errors import HttpError  # type: ignore

GmailService = Any


@dataclasses.dataclass
class EmailMessage:
  id: str
  thread_id: str = ''
  subject: str = ''
  sender: str = ''
  snippet: str = ''
  body: str = ''
  date: str = ''

  @classmethod
  @no_type_check
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
    return EmailMessage(
        id=data["id"],
        thread_id=data.get("threadId", ""),
        subject=subject,
        sender=sender,
        snippet=snippet,
        body=body,
        date=date_obj,
    )

  def to_string(self, short: bool = False) -> str:
    as_str = (
        'Email message:\n'
        f'Subject: {self.subject}\n'
        f'Sender: {self.sender}\n'
    )
    if short:
      as_str += self.snippet
    else:
      as_str += self.body
    return as_str


def get_gmail_service(credentials: Credentials) -> GmailService | None:
  try:
    service = build('gmail', 'v1', credentials=credentials)
    return service
  except HttpError as error:
    print(f'An error occurred: {error}')
    return None


def get_emails_impl(
    service: GmailService,
    *,
    num_emails: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    unread_only: bool = False,
    received_since: datetime.datetime | None = None,
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
      if received_since:
        timestamp = int(received_since.timestamp())
        query += f" after:{timestamp}"

      emails: list[EmailMessage] = []
      page_token = None
      label_ids = ['INBOX']
      if unread_only:
        label_ids.append('UNREAD')
      while True:
        list_params = {
            'userId': 'me',
            'q': query,
            'labelIds': label_ids,
            'pageToken': page_token,
        }

        @backoff.on_exception(
            backoff.expo,
            (httplib2.error.ServerNotFoundError,),
            max_tries=5,
            on_giveup=lambda e: print(f'Too many failures: {e}')
        )
        def call_with_backoff():
          return service.users().messages().list(**list_params).execute()

        results = call_with_backoff()
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


def update_labels(
    service: GmailService,
    message: EmailMessage,
    star: bool = False,
    mark_as_read: bool = False,
) -> EmailMessage | None:
  try:
    body = {}
    if star:
      body['addLabelIds'] = ['STARRED']
    if mark_as_read:
      body['removeLabelIds'] = ['UNREAD']
    service.users().messages().modify(
        userId='me',
        id=message.id,
        body=body,
    ).execute()
    return message
  except Exception as e:
    print(f'An error occurred: {e}')
    return None


def create_draft(
    service: GmailService,
    *,
    message: str,
    reply_to: str,
) -> None:
  # TODO: get other recipients and send it to them.
  obj = EmailMessageBuiltin()
  obj.set_content(message)
  # message['To'] = 'Ignore'
  # message['From'] = 'Ignore'
  # TODO: fetch subject from original message.
  # message['Subject'] = 'Automated draft'
  encoded = base64.urlsafe_b64encode(obj.as_bytes()).decode()
  body = { 'message': { 'threadId': reply_to, 'raw': encoded} }
  service.users().drafts().create(userId="me", body=body).execute()


if __name__ == '__main__':
  creds = auth_lib.get_credentials()
  service = get_gmail_service(creds)

  if len(sys.argv) > 1:

    if sys.argv[1] == 'draft':
      create_draft(
          service,
          message='This is a draft',
          reply_to='197c31c0f7f13a53',
      )

    else:
      update_labels(
          service,
          EmailMessage(id=sys.argv[1]),
          star=True,
          mark_as_read=True,
      )

  else:
    emails = get_emails_impl(service, num_emails=10)
    for e in emails:
      print(e.subject)
