"""Writing the masking.csv that MPG uses to undo the anonymisation."""

from __future__ import annotations

import csv
from pathlib import Path

from osuapi import OsuApiError, get_user_id


def write_mask(path: Path, entries: list[tuple[str, str]], api_key: str) -> bool:
    """Write one "username,user_id,anonymous name" row per entry.

    Returns False if any user id could not be looked up; those rows are
    still written, with an empty id, so they can be filled in by hand.
    """
    print("Looking up user ids for masking.csv")
    ok = True
    rows = []
    for username, anon_name in entries:
        try:
            user_id = get_user_id(api_key, username)
        except OsuApiError as error:
            print(f'Error: could not look up "{username}": {error}')
            user_id, ok = None, False
        else:
            if user_id is None:
                print(f'Error: no osu! user called "{username}"')
                ok = False
        rows.append([username, "" if user_id is None else user_id, anon_name])

    with open(path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows)
    return ok
