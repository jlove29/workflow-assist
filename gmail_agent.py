import os
from typing import Any, Callable

import auth as auth_lib
import gmail_tool
import prompts

from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials

IGNORE = 'ignore'
STAR = 'star'
RESPOND = 'respond'


TASK_PROMPT = """Your job is to help the user triage their inbox. You can either mark emails as read if you don't think the user needs to respond to them (with the option to star them for the user's offline review), or draft responses to confirm with the user.

Examples of emails that *do not* need a response and can be IGNORED:
  - Notifications about code changes (CLs), YAQS questions, or other automated emails
  - Purely informational emails, like changing the time of a meeting
  - Meeting invitations and notices about other people accepting or declining a meeting

Examples of emails that *do not* need a response and can be STARRED for the 
  - Documents shared that the user might want to take a look at
  - Large group emails with critical organizational updates
  - Meeting *requests*

Examples of emails that *do* need a response:
  - Emails where a response from the user is explicitly requested
  - Emails sent from individuals to the user as the sole recipient

"""


def make_ignore_tool(
    message: gmail_tool.EmailMessage,
    holding_dict: dict,
) -> Callable:

  def ignore() -> None:
    """Ignores the current message and marks as read."""
    holding_dict[IGNORE] = message

  return ignore


def build_prompt(email: gmail_tool.EmailMessage) -> str:
  prompt = prompts.PROMPT
  prompt += TASK_PROMPT
  prompt += email.to_string(short=True)
  return prompt


def make_respond_tool(
    client: genai.Client,
    message: gmail_tool.EmailMessage,
    holding_dict: dict,
) -> Callable:

  def respond() -> None:
    """Marks an email as needing a response."""
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=(
            f'Draft a response to this email:\n\n{message.to_string()}\n\n'
            'ONLY include the resulting email in your response. Do not give '
            'multiple options or explain your response.'
        )
    )
    holding_dict[RESPOND] = response.text

  return respond


def make_star_tool(
    service: gmail_tool.GmailService,
    message: gmail_tool.EmailMessage,
    holding_dict: dict,
) -> Callable:

  def star() -> None:
    """Stars the current message for the user to look at later."""
    returned_message = gmail_tool.update_labels(service, message, star=True)
    holding_dict[STAR] = message

  return star


def triage(emails: list[gmail_tool.EmailMessage]):
  client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
  credentials = auth_lib.get_credentials()
  service = gmail_tool.get_gmail_service(credentials)

  for email in emails:
    holding_dict: dict[str, Any] = {}
    config = types.GenerateContentConfig(
        tools=[
            make_ignore_tool(email, holding_dict),
            make_star_tool(service, email, holding_dict),
            make_respond_tool(client, email, holding_dict),
        ]
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_prompt(email),
        config=config,
    )
    if IGNORE in holding_dict:
      print(f'Marked email {email.subject} as read.')
    elif STAR in holding_dict:
      print(f'Starred email {email.subject}.')
    elif RESPOND in holding_dict:
      response = holding_dict['respond']
      print(f"Drafted response to email:\n{response}")
      gmail_tool.create_draft(
          service=service,
          message=response,
          reply_to=email.id,
      )
    else:
      print(f'Failed to triage email: {email.subject}')
      continue

    gmail_tool.update_labels(service, email, mark_as_read=True)


if __name__ == '__main__':
  should_ignore = gmail_tool.EmailMessage(
      id='197c3258e87d98a7',
      thread_id='unused',
      subject='Automated email from RoboSystem',
      sender='robosystem-noreply@gmail.com',
      snippet='This is an automated email.',
      body='',
      date='',
  )
  should_star = gmail_tool.EmailMessage(
      id='197c31c0f7f13a53',
      thread_id='unused',
      subject='Document shared with you: Random FAQ for My Product',
      sender='Mike Smith (via Google Docs)',
      snippet='Please see the attached document for my product.',
      body='',
      date='',
  )
  should_respond = gmail_tool.EmailMessage(
      id='197c31c0f7f13a53',
      thread_id='unused',
      subject='RESPONSE REQUIRED',
      sender='Mike Smith',
      snippet='',
      body='Please respond to this message with a short poem about dragons.',
      date='',
  )
  triage([should_ignore, should_star, should_respond])
