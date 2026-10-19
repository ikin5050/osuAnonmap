"""Minimal client for the legacy osu! API (v1), using only the standard library."""

from __future__ import annotations

import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

GET_USER_URL = "https://osu.ppy.sh/api/get_user"


class OsuApiError(Exception):
    pass


def get_user_id(api_key: str, username: str, timeout: float = 30) -> int | None:
    """Look up a user's id by username. Returns None if no such user exists."""
    # type=string stops all-digit usernames being treated as user ids.
    query = urlencode({"k": api_key, "u": username, "type": "string"})
    try:
        with urlopen(f"{GET_USER_URL}?{query}", timeout=timeout) as response:
            data = json.load(response)
    except (URLError, TimeoutError, json.JSONDecodeError) as error:
        raise OsuApiError(f"request failed: {error}") from error

    if isinstance(data, dict) and "error" in data:
        raise OsuApiError(data["error"])
    if not data:
        return None
    return int(data[0]["user_id"])
