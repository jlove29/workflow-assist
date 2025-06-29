import os

import auth as auth_lib
import calendar_tool
import gmail_tool
import prompts

from google import genai
from google.genai import types


class Agent:

  def __init__(self):
    self._client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))

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


if __name__ == '__main__':
  agent = Agent()
  user_input = input('> ')
  print(agent.call(user_input))
