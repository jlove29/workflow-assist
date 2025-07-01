import os
from typing import Any, Callable

import auth as auth_lib
import gmail_tool
import prompts

from google import genai
from google.genai import types


TASK_PROMPT = """Your job is to help the user triage their inbox. You can either mark emails as read if you don't think the user needs to respond to them (with the option to star them for the user's offline review), or draft responses to confirm with the user.

Examples of emails that *do not* need a response and can be IGNORED:
  - Notifications about code changes (CLs), YAQS questions, or other automated emails
  - Purely informational emails, like changing the time of a meeting
  - Meeting invitations and notices about other people accepting or declining a meeting
  - gThanks

Examples of emails that *do not* need a response and can be STARRED for the 
  - Documents shared that the user might want to take a look at
  - Large group emails with critical organizational updates
  - Meeting *requests*

Examples of emails that *do* need a response:
  - Emails where a response from the user is explicitly requested
  - Emails sent from individuals to the user as the sole recipient

"""


def build_prompt(email: gmail_tool.EmailMessage) -> str:
  prompt = prompts.PROMPT
  prompt += TASK_PROMPT
  prompt += email.to_string(short=True)
  return prompt


def make_respond_tool(
    client: genai.Client,
    message: gmail_tool.EmailMessage,
    edited_dict: dict[str, Any],
) -> Callable:

  def respond() -> None:
    """Marks an email as needing a response."""
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=(
            f'Draft a response to this email:\n\n{message.to_string()}'
        )
    )
    edited_dict['respond'] = response.text

  return respond


def triage(emails: list[gmail_tool.EmailMessage]):
  client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
  credentials = auth_lib.get_credentials()

  for email in emails:
    holding_dict = {}
    config = types.GenerateContentConfig(
        tools=[
            gmail_tool.make_ignore_tool(
              credentials,
              email,
              edited_dict=holding_dict,
            ),
            gmail_tool.make_star_tool(
              credentials,
              email,
              edited_dict=holding_dict,
            ),
            make_respond_tool(client, email, holding_dict),
        ]
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=build_prompt(email),
        config=config,
    )
    if 'ignore' in holding_dict:
      print(f'Marked email {email.subject} as read.')
    elif 'star' in holding_dict:
      print(f'Starred email {email.subject}.')
    elif 'respond' in holding_dict:
      response = holding_dict['respond']
      print(f"Drafted response to email:\n{response}")
      gmail_tool.create_draft(
          credentials=credentials,
          message=response,
          reply_to=email.id,
      )
    else:
      print(f'Failed to triage email: {email.subject}')


if __name__ == '__main__':
  should_ignore = gmail_tool.EmailMessage(
      id='197c3258e87d98a7',
      thread_id='unused',
      subject='Automated email from RoboSystem',
      sender='robosystem-noreply@gmail.com',
      snippet='This is an automated email.',
      body='',
      date=None,
  )
  should_star = gmail_tool.EmailMessage(
      id='197c31c0f7f13a53',
      thread_id='unused',
      subject='Document shared with you: Random FAQ for My Product',
      sender='Mike Smith (via Google Docs)',
      snippet='Please see the attached document for my product.',
      body='',
      date=None,
  )
  should_respond = gmail_tool.EmailMessage(
      id='197c31c0f7f13a53',
      thread_id='unused',
      subject='RESPONSE REQUIRED',
      sender='Mike Smith',
      snippet='',
      body='Please respond to this message with a short poem about dragons.',
      date=None,
  )
  triage([should_ignore, should_star, should_respond])
