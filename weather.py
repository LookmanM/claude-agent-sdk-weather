"""Weather tool example with the Claude Agent SDK.

User asks "What is the weather in New York?" -> Claude calls our get_weather
tool -> the tool hits Open-Meteo (free, no API key) -> Claude answers.

Run:  python weather.py  ["optional question"]
"""
import asyncio
import sys
from typing import Annotated, Any

import httpx
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
    tool,
)


@tool(
    "get_weather",
    "Get the current weather for a city",
    {"city": Annotated[str, "City name, e.g. 'New York'"]},
)
async def get_weather(args: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            geo = (await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": args["city"], "count": 1},
            )).json()
            if not geo.get("results"):
                return {
                    "content": [{"type": "text", "text": f"City not found: {args['city']}"}],
                    "is_error": True,
                }
            place = geo["results"][0]
            wx = (await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": "temperature_2m,apparent_temperature,wind_speed_10m,weather_code",
                    "temperature_unit": "fahrenheit",
                    "wind_speed_unit": "mph",
                },
            )).json()["current"]
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Weather lookup failed: {e}"}], "is_error": True}

    return {
        "content": [{
            "type": "text",
            "text": (
                f"{place['name']}, {place.get('admin1', '')}: {wx['temperature_2m']}°F "
                f"(feels like {wx['apparent_temperature']}°F), wind {wx['wind_speed_10m']} mph, "
                f"WMO weather code {wx['weather_code']}"
            ),
        }]
    }


weather_server = create_sdk_mcp_server(name="weather", version="1.0.0", tools=[get_weather])


async def main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else "What is the weather in New York?"
    options = ClaudeAgentOptions(
        mcp_servers={"weather": weather_server},
        allowed_tools=["mcp__weather__get_weather"],  # pre-approve: no permission prompt
        tools=[],  # drop built-in tools (Bash, Read, ...) so only our tool is available
        max_turns=5,
    )

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"[tool call] {block.name}({block.input})")
        elif isinstance(message, ResultMessage):
            print(f"\n{message.result}")
            print(f"\n[{message.subtype}] turns={message.num_turns} cost=${message.total_cost_usd or 0:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
