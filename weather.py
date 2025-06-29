from typing import Any, Union
import httpx
import asyncio
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather")

#Constantes
NWS_API_URL = "https://api.weather.gov"
URSER_AGENT = "weather-agent/1.0"

#Helper Functions

async def make_nws_request(url: str) -> Union[dict[str, Any], None]:
    """
    Make a request to the NWS API and return the response as a dictionary.
    """

    headers = {
        "User-Agent": URSER_AGENT,
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            print(f"Error fetching data from NWS API: {e}")
            return None
        except httpx.RequestError as e:
            print(f"Error making request to NWS API: {e}")
            return None

def format_alert(feature: dict) -> str:
    """Format an alert feature into a readable string."""
    props = feature["properties"]
    return f"""
            Event: {props.get('event', 'Unknown')}
            Area: {props.get('areaDesc', 'Unknown')}
            Severity: {props.get('severity', 'Unknown')}
            Description: {props.get('description', 'No description available')}
            Instructions: {props.get('instruction', 'No specific instructions provided')}
            """

# Implementing tool execution

@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """Get weather forecast for a location.

    Args:
        latitude: Latitude of the location
        longitude: Longitude of the location
    """
    # First get the forecast grid endpoint
    points_url = f"{NWS_API_URL}/points/{latitude},{longitude}"
    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    # Get the forecast URL from the points response
    forecast_url = points_data["properties"]["forecast"]
    forecast_data = await make_nws_request(forecast_url)

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
    
@mcp.tool()
async def get_alerts(latitude: float, longitude: float) -> str:
    """Get the alerts for a given location."""
    url = f"{NWS_API_URL}/points/{latitude},{longitude}/alerts"
    data = await make_nws_request(url)
    if not data or "features" not in data:
        return "No alerts data available."

    if not data["features"]:
        return "No active alerts found for this location."
        
    alerts = data["features"]
    return "\n\n".join(format_alert(alert) for alert in alerts)


if __name__ == "__main__":
    mcp.run(transport="stdio")
    