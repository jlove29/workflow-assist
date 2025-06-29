import datetime
import os

GEMINI_MD = './GEMINI.md'

PROMPT = """You are an AI Agent helping out a user in the role of an administrative assistant.

"""


def build_prompt(user_input: str):
  prompt = PROMPT

  now = datetime.datetime.now()
  prompt += now.strftime("Today's date is: %Y-%m-%d. It is %H:%M.\n\n")

  if os.path.exists(GEMINI_MD):
    prompt += (
        "Here are the user's preferences for how you should help them:\n\n"
    )
    with open(GEMINI_MD, 'r') as f:
      user_prefs = f.read()
    prompt += user_prefs

  prompt += f'\nUser query:\n{user_input}'
  return prompt


if __name__ == '__main__':
  print('*************')
  print(build_prompt('What are my next 5 calendar events?'))
  print('*************')
