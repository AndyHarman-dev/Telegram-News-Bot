import logging

import aiohttp
import hashlib
import json

from app.misc.log_helper import LogHelper

# Simple in-memory cache. Not for external use
cache = {}

AIOHTTP_REQUESTER_LOG = LogHelper(__name__, "AIOHTTP Requester Thread")


async def fetch_with_cache(url, method='GET', data=None, params=None, custom_session=None):
    # Generate a cache key
    cache_key = hashlib.sha256(json.dumps([url, method, data, params], sort_keys=True).encode()).hexdigest()

    # Check cache
    if cache_key in cache:
        AIOHTTP_REQUESTER_LOG.log(logging.INFO, "Returning cached response")
        return cache[cache_key]

    if custom_session:
        return await _process_async_request(url, method, data, params, custom_session, cache_key)
    else:
        # Make HTTP request
        async with aiohttp.ClientSession() as session:
            return await _process_async_request(url, method, data, params, session, cache_key)


async def _process_async_request(url, method='GET', data=None, params=None, custom_session=None, cache_key=None):
    async with custom_session.request(url=url, method=method, data=data, params=params) as response:
        response_data = await response.json()
        # Cache the response
        cache[cache_key] = response_data
        return response_data
