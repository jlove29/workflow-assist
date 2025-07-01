import datetime
import os
from typing import Literal

GEMINI_MD = './GEMINI.md'
TRIAGE_MD = './TRIAGE.md'

PROMPT = """You are an AI Agent helping out a user in the role of an administrative assistant.

"""

def user_prefs(prompt_file: str = GEMINI_MD) -> str:
  prompt = ''
  if os.path.exists(prompt_file):
    prompt += (
        "Here are the user's preferences for how you should help them:\n\n"
    )
    with open(prompt_file, 'r') as f:
      user_prefs = f.read()
    prompt += user_prefs
    prompt += '\n\n'

  return prompt


def build_prompt(user_input: str) -> str:
  prompt = PROMPT

  now = datetime.datetime.now()
  prompt += now.strftime("Today's date is: %Y-%m-%d. It is %H:%M.\n\n")

  prompt += user_prefs()

  prompt += f'User query:\n{user_input}'
  return prompt


if __name__ == '__main__':
  print('*************')
  print(build_prompt('What are my next 5 calendar events?'))
  print('*************')
