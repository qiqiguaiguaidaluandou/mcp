import httpx


def register(mcp):
    @mcp.tool()
    async def get_weather(location: str) -> dict:
        """Get current weather for a location via wttr.in.

        Args:
            location: city name, airport code, or "lat,lon" (e.g. "Beijing",
                "SFO", "39.9,116.4"). Non-ASCII names work too.
        """
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://wttr.in/{location}", params={"format": "j1"}
            )
            r.raise_for_status()
            data = r.json()

        c = data["current_condition"][0]
        area = data.get("nearest_area", [{}])[0]
        return {
            "location": location,
            "resolved_area": (area.get("areaName", [{}])[0].get("value")),
            "temp_c": c["temp_C"],
            "feels_like_c": c["FeelsLikeC"],
            "humidity": c["humidity"],
            "description": c["weatherDesc"][0]["value"],
            "wind_kmph": c["windspeedKmph"],
            "observation_time_utc": c["observation_time"],
        }

    @mcp.tool()
    async def get_forecast(location: str, days: int = 3) -> list[dict]:
        """Get daily forecast (up to 3 days) for a location via wttr.in."""
        days = max(1, min(days, 3))
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://wttr.in/{location}", params={"format": "j1"}
            )
            r.raise_for_status()
            data = r.json()

        out = []
        for d in data["weather"][:days]:
            out.append({
                "date": d["date"],
                "min_c": d["mintempC"],
                "max_c": d["maxtempC"],
                "sunrise": d["astronomy"][0]["sunrise"],
                "sunset": d["astronomy"][0]["sunset"],
                "description": d["hourly"][4]["weatherDesc"][0]["value"],
            })
        return out
