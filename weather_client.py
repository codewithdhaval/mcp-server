import asyncio
import json
from typing import Optional
from unittest import result
from mcp import ClientSession
from mcp.client.sse import sse_client
# from openai import OpenAI
import mcp.client.sse as _sse_mod
from httpx import AsyncClient as _BaseAsyncClient
import os
import httpx
import logging

from mcp.server.fastmcp import tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("client-sse")


async def main():
    sse_url = "http://localhost:8100/sse"

    async with sse_client(url=sse_url) as (in_stream, out_stream):
        async with ClientSession(in_stream, out_stream) as session:
            info = await session.initialize()
            logger.info(f"Connected to {info.serverInfo.name} v{info.serverInfo.version}")
            tools = (await session.list_tools())
            logger.info(tools)
            available_tools = await session.list_tools()
            result = await session.call_tool("get_forecast", {'latitude': 40.7128,'longitude': -74.006})
            logger.info(result)

if __name__ == "__main__":
    asyncio.run(main())