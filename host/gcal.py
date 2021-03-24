import os
import json
from datetime import datetime, timezone, timedelta
import asyncio
import logging
from typing import Tuple, Any, Mapping
from dataclasses import dataclass

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


_log = logging.getLogger(__name__)


TOKEN_PATH = "secrets/google-token.json"
CLIENT_SECRETS_PATH = "secrets/google-client-secrets.json"
CALENDAR_LIST_PATH = "secrets/calendars.json"
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
POLL_EVENTS_EVERY = 60 * 10


@dataclass
class Event:
    reminder: timedelta
    event: Mapping


async def send_events(queue: asyncio.Queue):
    events_gen = poll_events()
    events = await events_gen.asend(None)
    create_new_events = lambda: asyncio.create_task(events_gen.asend(None))
    create_next_event = lambda events: asyncio.create_task(wait_for_next_event(events))
    new_events = create_new_events()
    next_event = create_next_event(events)

    while True:
        done, _ = await asyncio.wait(
            {new_events, next_event},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if new_events in done:
            events = new_events.result()
            new_events = create_new_events()
            next_event.cancel()
            next_event = create_next_event(events)
        else:
            await queue.put(next_event.result())
            next_event = create_next_event(events)


async def poll_events():
    while True:
        yield await asyncio.to_thread(get_events)
        await asyncio.sleep(POLL_EVENTS_EVERY)


async def wait_for_next_event(events):
    """
    Wait for the next event to alarm on.
    A reminder should be fired 5 minutes before the event and on the event.
    - For each future event, produce two reminder events.
    - Find next event
    - Wait for it
    """
    reminder_stamp, reminder, event = get_next_event(events)
    await asyncio.sleep((reminder_stamp - datetime.now(timezone.utc)).total_seconds())
    return Event(reminder, event)


def get_next_event(events) -> Tuple[datetime, timedelta, Any]:
    reminders = [timedelta(minutes=5), timedelta(seconds=0)]
    max_reminder = max(reminders)
    now = datetime.now(timezone.utc)
    next_so_far = None

    events.sort(key=lambda event: event["start"]["dateTime"])

    for event in events:
        stamp = parse_stamp(event["start"]["dateTime"])
        # if event past the skip
        if stamp < now:
            continue

        # if event is further ahead than the longest reminder ahead of the current best candidate
        if next_so_far is not None and stamp - next_so_far[0] > max_reminder:
            return next_so_far

        for reminder in reminders:
            reminder_stamp = stamp - reminder
            if reminder_stamp < now:
                continue

            if next_so_far is None or reminder_stamp < next_so_far[0]:
                next_so_far = (reminder_stamp, reminder, event)

    raise Exception("not found")


async def main_test():
    import asyncio
    queue = asyncio.Queue()
    asyncio.create_task(send_events(queue))
    while True:
        event = await queue.get()

        print(event['summary'])


def parse_stamp(stamp: str) -> datetime:
    if stamp[-1] == 'Z':
        stamp = stamp[:-1] + '+00:00'

    return datetime.fromisoformat(stamp).astimezone(timezone.utc)


def get_events():
    _log.debug('get events')
    client = get_client()
    now = datetime.utcnow().isoformat() + 'Z'

    with open(CALENDAR_LIST_PATH) as f:
        events = [
            event
            for calendar_id in json.load(f)
            for event in client.events().list(
                calendarId=calendar_id,
                maxResults=50,
                timeMin=now,
                singleEvents=True,
                orderBy='startTime'
            ).execute().get('items', [])
        ]
        events.sort(key=lambda event: event['start']['dateTime'])
        return events


def get_client():
    return build('calendar', 'v3', credentials=get_credentials())


def get_credentials():
    """
    Taken from https://developers.google.com/calendar/quickstart/python
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(TOKEN_PATH, 'w+') as token:
            token.write(creds.to_json())

    return creds

if __name__ == '__main__':
    import asyncio

    asyncio.run(main_test())
