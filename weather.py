from typing import Any, Union
import httpx
from mcp.server.fastmcp import FastMCP
import asyncio
import json

from fastapi import FastAPI
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
import logging
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptMessage,
    TextContent,
)


logger = logging.getLogger("server")

mcp = FastMCP("weather")

transport = SseServerTransport("/messages/")

#constants
NWS_API_URL = "https://api.weather.gov"
USER_AGENT = "weather-mcp/1.0"

#helper function to fetch weather data
async def fetch_weather_data(url: str) -> Union[dict[str, Any], None]:
    """Fetch weather data from the NWS API"""
    try: 
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url=url,
                headers=headers, timeout=10
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
            print(f"Error fetching data from NWS API: {e}")
            return None
    except httpx.RequestError as e:
        print(f"Error making request to NWS API: {e}")
        return None

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """
    Provide a detailed weather forecast for the given latitude and longitude.
    Respond with the next 5 forecast periods, including temperature, wind, and a summary.
    """

    # First get the forecast grid endpoint
    points_url = f"{NWS_API_URL}/points/{latitude},{longitude}"
    points_data = await fetch_weather_data(points_url)

    if not points_data:
            return "Unable to fetch forecast data for this location"

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await fetch_weather_data(forecast_url)

    if not forecast_data:
        return "Unable to fetch detailed forecast."

    # Format the periods into a readable forecast
    periods = forecast_data["properties"]["periods"]
    forecasts = []
    for period in periods[:5]:  # Only show next 5 periods
        forecast = f"""
            {period['name']}:
            Temperature: {period['temperature']}°{period['temperatureUnit']}
            Wind: {period['windSpeed']} {period['windDirection']}
            Forecast: {period['detailedForecast']}
            """
        forecasts.append(forecast)

    return "\n---\n".join(forecasts)


async def handle_sse(request):
    # Prepare bidirectional streams over SSE
    async with transport.connect_sse(
        request.scope,
        request.receive,
        request._send
    ) as (in_stream, out_stream):
        # Run the MCP server: read JSON-RPC from in_stream, write replies to out_stream
        await mcp._mcp_server.run(
            in_stream,
            out_stream,
            mcp._mcp_server.create_initialization_options()
        )

sse_app = Starlette(routes=[
    Route("/sse", handle_sse, methods=["GET"]),
    Mount("/messages", app=transport.handle_post_message)
])

app = FastAPI()
app.mount("/", sse_app)


@mcp.prompt()
async def weather_advisor_prompt(location: str) -> str: 
    """
    Generate weather-based advice for activities and planning.
    
    Args:
        location: City
    """

    # Create system message with weather expertise
    prompt=f"""You are a professional meteorologist and activity planning expert. 

        Your expertise includes:
        - Weather pattern analysis and forecasting interpretation
        - Activity-specific weather considerations
        - Safety recommendations for weather conditions
        - Optimal timing suggestions for activities
        - Regional weather patterns and microclimates


        Always provide:
        1. Current conditions summary
        2. Activity-specific recommendations
        3. Timing suggestions (best/worst times)
        4. Safety considerations
        5. Alternative suggestions if weather is unsuitable
      
        Be specific, practical, and safety-conscious in your advice."""
    
    
    return f"{prompt}"




@app.get("/health")
def health():
        return {"message":"MCP SSE server is running!!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8100)