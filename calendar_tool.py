import dataclasses
import datetime
import os
from typing import Any, Callable
from zoneinfo import ZoneInfo

import auth as auth_lib

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CalendarService = Any


@dataclasses.dataclass
class Attendee:
  email: str
  display_name: str
  response_status: str

  @classmethod
  def from_json(cls, data: dict) -> 'Attendee':
    return Attendee(
        email=data.get('email'),
        display_name=data.get('displayName', ''),
        response_status=data.get('responseStatus'),
    )


def _parse_date(date_info: dict) -> str:
  if 'dateTime' in date_info:
    dt = datetime.datetime.fromisoformat(date_info['dateTime'])
    london_tz = ZoneInfo("Europe/London")
    dt_obj = dt.astimezone(london_tz)
    return dt_obj.strftime("%A, %d %B %Y at %I:%M %p")
  else:
    dt_obj = datetime.date.fromisoformat(date_info['date'])
    return dt_obj.strftime("%A, %d %B %Y")



@dataclasses.dataclass
class CalendarEvent:
  status: str
  summary: str
  description: str
  location: str
  creator: str
  start: str
  end: str
  attendees: list[Attendee]

  @classmethod
  def from_json(cls, data: dict) -> 'CalendarEvent':

    attendees_list = []
    for attendee_data in data.get('attendees', []):
      attendee = Attendee.from_json(attendee_data)
      attendees_list.append(attendee)

    return CalendarEvent(
        status=data.get('status'),
        summary=data.get('summary'),
        description=data.get('description', ''),
        location=data.get('location', ''),
        creator=data['creator'].get('email'),
        start=_parse_date(data['start']),
        end=_parse_date(data['end']),
        attendees=attendees_list,
    )


def get_calendar_service(credentials: Credentials) -> CalendarService | None:
  try:
    service = build('calendar', 'v3', credentials=credentials)
    return service
  except HttpError as error:
    print(f'An error occurred: {error}')
    return None


def get_events_impl(
    service: CalendarService,
    *,
    num_events: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    updated_since: datetime.datetime | None = None,
) -> list[CalendarEvent]:
  """Fetches calendar events."""
  if not (num_events or start_date or end_date):
    # If nothing is specified, fetch a reasonable number of events.
    num_events = 50

  if start_date:
      time_min_dt = datetime.datetime.strptime(start_date, '%Y-%m-%d')
      time_min = time_min_dt.replace(tzinfo=datetime.timezone.utc).isoformat()
  else:
      time_min = datetime.datetime.utcnow().isoformat() + 'Z'

  list_params = {
      'calendarId': 'primary',
      'timeMin': time_min,
      'maxResults': num_events,  # API handles None by using its default.
      'singleEvents': True,
      'orderBy': 'startTime',
  }

  if end_date:
    end_dt = datetime.datetime.strptime(end_date, '%Y-%m-%d').replace(
        hour=23, minute=59, second=59, microsecond=999999
    )
    list_params['timeMax'] = end_dt.replace(
        tzinfo=datetime.timezone.utc
    ).isoformat()

  if updated_since:
    list_params['updatedMin'] = updated_since.replace(
        tzinfo=datetime.timezone.utc
    ).isoformat()

  events_result = service.events().list(**list_params).execute()
  events = events_result.get('items', [])

  if not events:
    print('No upcoming events found.')
    return []

  parsed_events = []
  user_email = os.environ.get('EMAIL')
  for e in events:
    event = CalendarEvent.from_json(e)
    declined = False
    for a in event.attendees:
      if (
          user_email and
          a.email.startswith(user_email) and
          a.response_status == 'declined'
      ):
        declined = True
        break
    if not declined:
      parsed_events.append(event)
  return parsed_events


def make_get_events_tool(credentials: Credentials) -> Callable:
  service = get_calendar_service(credentials)

  def get_events(
      num_events: int | None = None,
      start_date: str | None = None,
      end_date: str | None = None,
  ):
    """Fetches calendar events.

    Args:
      num_events: If set, will fetch the next `num_events` events.
      start_date: If set, will fetch events starting from that date.
        Must be in YYYY-MM-DD format, e.g. `2025-06-29`.
      end_date: If set, will fetch events starting up to that date.

    Returns:
      a list of calendar events.
    """
    events = get_events_impl(
        service,
        num_events=num_events,
        start_date=start_date,
        end_date=end_date,
    )
    return events

  return get_events



if __name__ == '__main__':
  service = get_calendar_service(auth_lib.get_credentials())
  events = get_events_impl(service, num_events=10)
  for e in events:
    print(e.summary, e.start)
