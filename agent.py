import datetime
import os
import sys
import time

import auth as auth_lib
import calendar_tool
import gmail_tool
import prompts

from google import genai
from google.genai import types

INTERVAL = 15  # seconds


class Agent:

  def __init__(self):
    self._client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
    self._last_ckpt = datetime.datetime.now(datetime.UTC)

  def call(self, user_input: str) -> str:
    credentials = auth_lib.get_credentials()
    config = types.GenerateContentConfig(
        tools=[
            calendar_tool.make_get_events_tool(credentials),
            gmail_tool.make_get_emails_tool(credentials),
        ]
    )
    response = self._client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompts.build_prompt(user_input),
        config=config,
    )
    return response.text

  def run(self) -> None:
    while True:
      time.sleep(INTERVAL)
      creds = auth_lib.get_credentials()
      print('Fetching latest events...')
      latest_events = calendar_tool.get_events_impl(
          calendar_tool.get_calendar_service(creds),
          updated_since=self._last_ckpt,
      )
      print(latest_events)
      print('Fetching latest emails...')
      latest_emails = gmail_tool.get_emails_impl(
          gmail_tool.get_gmail_service(creds),
          received_since=self._last_ckpt,
      )
      print(latest_emails)
      self._last_ckpt = datetime.datetime.now(datetime.UTC)


if __name__ == '__main__':
  agent = Agent()

  if len(sys.argv) > 1 and sys.argv[1] == 'chat':
    user_input = input('> ')
    print(agent.call(user_input))

  else:
    agent.run()
