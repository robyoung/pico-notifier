import asyncio
import os
from dataclasses import dataclass
from enum import Enum, auto
from typing import Mapping, Any, Optional
from collections import defaultdict

from loguru import logger

import aiohttp
from aiohttp.client_exceptions import ClientResponseError

from . import pico

BASE_URL = "https://api.github.com"


async def search_pulls(session, is_open: bool):
    open_closed = "open" if is_open else "closed"
    params = {
        "q": f"author:robyoung is:{open_closed} is:pr",
        "order": "desc",
        "sort": "updated",
    }
    async with session.get(BASE_URL + "/search/issues", params=params) as resp:
        return await resp.json()


async def search_open_pulls(session):
    return await search_pulls(session, is_open=True)


async def search_closed_pulls(session):
    return await search_pulls(session, is_open=False)


async def get_raw_pull(session, search_result):
    parts = search_result["url"].split("/")
    number = parts[-1]
    repo = parts[-3]
    owner = parts[-4]
    path = f"/repos/{owner}/{repo}/pulls/{number}"

    async with session.get(BASE_URL + path) as resp:
        return await resp.json()


async def get_reviews(session, pull):
    async with session.get(pull["_links"]["self"]["href"] + "/reviews") as resp:
        return await resp.json()


async def get_status(session, pull):
    head_sha = pull["head"]["sha"]
    repo_url = pull["head"]["repo"]["url"]
    async with session.get(f"{repo_url}/commits/{head_sha}/status") as resp:
        result = await resp.json()
        return result


async def get_checks(session, pull):
    head_sha = pull["head"]["sha"]
    repo_url = pull["head"]["repo"]["url"]
    path = f"{repo_url}/commits/{head_sha}/check-runs"
    async with session.get(path) as resp:
        result = await resp.json()
        return result


# Get checks from most recent commit
# Get statuses from pull, get most recent for each context


class PullState(Enum):
    PENDING = auto()
    FAILED = auto()
    MERGE = auto()
    DONE = auto()


@dataclass
class Pull:
    url: str
    state: PullState


@dataclass
class Event:
    pull: Pull
    offset: int

    @property
    def colour(self):
        if self.pull.state == PullState.FAILED:
            return pico.RED
        elif self.pull.state == PullState.MERGE:
            return pico.GREEN
        elif self.pull.state == PullState.PENDING:
            return pico.ORANGE
        elif self.pull.state == PullState.DONE:
            return pico.GREEN

    @property
    def key_cmds(self):
        if self.pull.state == PullState.DONE:
            return [pico.Key.leds(pico.OFF)]
        else:
            return [
                pico.Key.key('COMMAND'),
                pico.Key.sleep(0.2),
                pico.Key.write('firefox'),
                pico.Key.key('ENTER'),
                pico.Key.sleep(0.2),
                pico.Key.key('CONTROL', 'T'),
                pico.Key.sleep(0.2),
                pico.Key.write(self.pull.url),
                pico.Key.key('ENTER'),
            ]

    @staticmethod
    def done(offset: int) -> "Event":
        return Event(Pull("", PullState.DONE), offset)


async def resolve_open_pull(session, result: Mapping[str, Any]) -> Optional[Pull]:
    raw_pull = await get_raw_pull(session, result)
    reviews, status, checks = await asyncio.gather(
        get_reviews(session, raw_pull),
        get_status(session, raw_pull),
        get_checks(session, raw_pull),
    )
    review_ok = (
        all(review["state"] == "APPROVED" for review in reviews) and len(reviews) > 1
    )
    review_fail = any(review["state"] == "REQUEST_CHANGES" for review in reviews)
    status_state = status["state"]  # failure | pending | success
    status_count = status["total_count"]
    checks_pending = any(
        check["status"] in {"in_progress", "queued"} for check in checks["check_runs"]
    )
    checks_failed = any(
        check["status"] == "complete"
        and check["conclusion"] not in {"success", "skipped"}
        for check in checks["check_runs"]
    )

    if review_fail or checks_failed or status_state == "failed":
        state = PullState.FAILED
    elif (status_state == "pending" and status_count > 0) or checks_pending or not review_ok:
        state = PullState.PENDING
    else:
        state = PullState.MERGE

    return Pull(url=raw_pull["html_url"], state=state)


async def get_open_pulls(session) -> list[Pull]:
    results = await search_open_pulls(session)
    pull_coros = [resolve_open_pull(session, result) for result in results["items"]]
    return [
        pull
        for coro in asyncio.as_completed(pull_coros)
        if (pull := await coro) is not None
    ]


async def resolve_closed_pull(result: Mapping[str, Any]) -> Optional[Pull]:
    # TODO
    return None


async def get_closed_pulls(session) -> list[Pull]:
    results = await search_open_pulls(session)
    pull_coros = [resolve_closed_pull(result) for result in results["items"]]
    return [
        pull
        for coro in asyncio.as_completed(pull_coros)
        if (pull := await coro) is not None
    ]


async def get_pulls(session) -> list[Pull]:
    results = await asyncio.gather(
        get_open_pulls(session),
        get_closed_pulls(session),
    )
    return results[0] + results[1]


def get_headers():
    return {
        "Authorization": f"token {os.environ['GH_TOKEN']}",
    }

async def send_events(queue: asyncio.Queue):
    POLL_EVERY = 30

    MAX_SENT = 0
    async with aiohttp.ClientSession(headers=get_headers()) as session:
        while True:
            try:
                logger.debug("get pulls")
                pulls = await get_pulls(session)

                # handle DONE
                for pull in pulls:
                    if pull.state != PullState.DONE:
                        continue
                    logger.debug(f"done {pull.url}")

                # handle not DONE
                offset = 0
                sent = defaultdict(int)
                for pull in pulls:
                    sent[pull.state] += 1
                    if pull.state == PullState.DONE:
                        continue
                    event = Event(pull=pull, offset=offset)
                    logger.debug("send update event")
                    await queue.put(event)
                    offset += 1
                    if offset > MAX_SENT:
                        MAX_SENT = offset
                logger.info("sent {event_details}", event_details=", ".join([f"{num} {state} events" for state, num in sent.items()]))
                current_max = offset
                while offset < MAX_SENT:
                    await queue.put(Event.done(offset))
                    offset += 1

                MAX_SENT = current_max
            except ClientResponseError as e:
                logger.exception(e)
            finally:
                await asyncio.sleep(POLL_EVERY)


async def main():
    async with aiohttp.ClientSession(headers=get_headers()) as session:
        await get_pulls(session)


if __name__ == "__main__":
    asyncio.run(main())
