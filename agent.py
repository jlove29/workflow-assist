import os

import auth as auth_lib
import calendar_tool
import gmail_tool
import prompts

from google import genai
from google.genai import types


def run(user_input: str):
  client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY'))
  credentials = auth_lib.get_credentials()
  config = types.GenerateContentConfig(
      tools=[
          calendar_tool.make_get_events_tool(credentials)
      ]
  )

  response = client.models.generate_content(
      model="gemini-2.5-flash",
      contents=prompts.build_prompt(user_input),
      config=config,
  )

  print(response.text)


if __name__ == '__main__':
  user_input = input()
  run(user_input)
