import asyncio
import json
import os

import aiohttp

BASE_URL = "https://api.github.com"


async def search_pulls(session, is_open: bool):
    open_closed = 'open' if is_open else 'closed'
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


async def get_pull(session, search_result):
    parts = search_result["url"].split('/')
    number = parts[-1]
    repo = parts[-3]
    owner = parts[-4]
    path = f"/repos/{owner}/{repo}/pulls/{number}"

    async with session.get(BASE_URL + path) as resp:
        return await resp.json()


async def get_reviews(session, pull):
    async with session.get(pull['_links']['self']['href'] + "/reviews") as resp:
        return await resp.json()


async def get_statuses(session, pull):
    async with session.get(pull['_links']['statuses']['href']) as resp:
        return await resp.json()


# Get checks from most recent commit
# Get statuses from pull, get most recent for each context

async def main():
    headers = {
        "Authorization": f"token {os.environ['GH_TOKEN']}",
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        results = await search_open_pulls(session)
        pull = await get_pull(session, results["items"][0])
        reviews = await get_reviews(session, pull)
        statuses = await get_statuses(session, pull)
        print(json.dumps(statuses))


if __name__ == '__main__':
    asyncio.run(main())
