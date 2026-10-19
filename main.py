"""Anonymise osu! mapping contest entries. See README.md for setup."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import beatmap
import mask
from names import NameGenerator

ROOT = Path.cwd()
CONFIG_PATH = ROOT / "config.json"
TOKEN_PATH = ROOT / "token.json"
MAPS_ZIP = ROOT / "maps.zip"
OUTPUT_DIR = ROOT / "output"


class SetupError(Exception):
    pass


@dataclass
class Config:
    tournament_name: str
    number_diffs: int  # 0 means any number is allowed
    taiko: bool


@dataclass
class Entry:
    label: str  # where the .osz came from in maps.zip, for messages
    folder: Path
    creators: list[str] = field(default_factory=list)
    anon_name: str = ""


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in ("false", "0", "no", "")


def load_config(path: Path) -> Config:
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        return Config(
            tournament_name=str(raw["tournamentName"]),
            number_diffs=int(raw.get("numberDiffs", 0)),
            taiko=parse_bool(raw.get("taiko", False)),
        )
    except FileNotFoundError:
        raise SetupError(f"{path.name} not found")
    except (json.JSONDecodeError, KeyError, ValueError) as error:
        raise SetupError(f"{path.name} is not valid: {error}")


def load_api_key(path: Path) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            token = json.load(f)["token"]
    except FileNotFoundError:
        raise SetupError(f"{path.name} not found; see README.md")
    except json.JSONDecodeError:
        raise SetupError(f"{path.name} is not formatted properly, surround the values in double quotation marks")
    except (KeyError, TypeError):
        raise SetupError(f'{path.name} must contain a "token" value')
    if not isinstance(token, str) or not token.strip() or token.startswith("<"):
        raise SetupError(f"{path.name} does not contain a valid API token")
    return token.strip()


def zip_folder(folder: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                zipf.write(path, arcname=path.relative_to(folder).as_posix())


def extract_entries(maps_zip: Path, work_dir: Path) -> list[Entry]:
    """Unpack maps.zip, then every .osz inside it into its own folder."""
    submissions = work_dir / "submissions"
    try:
        with zipfile.ZipFile(maps_zip) as zipf:
            zipf.extractall(submissions)
    except zipfile.BadZipFile:
        raise SetupError(f"{maps_zip.name} is not a valid zip file")

    entries = []
    for path in sorted(submissions.rglob("*")):
        if not path.is_file() or "__MACOSX" in path.parts or path.name.startswith("."):
            continue
        label = path.relative_to(submissions).as_posix()
        if path.suffix.lower() != ".osz":
            print(f"Skipping {label}: not an .osz file")
            continue
        folder = work_dir / "entries" / str(len(entries))
        try:
            with zipfile.ZipFile(path) as zipf:
                zipf.extractall(folder)
        except zipfile.BadZipFile:
            print(f"Error: {label} is not a valid .osz file")
            continue
        entries.append(Entry(label=label, folder=folder))
    return entries


def validate_entry(entry: Entry, config: Config) -> bool:
    osu_files = beatmap.find_osu_files(entry.folder)
    if not osu_files:
        print(f"Error: {entry.label} contains no .osu files")
        return False
    if config.number_diffs and len(osu_files) != config.number_diffs:
        print(f"Error: {entry.label} has {len(osu_files)} .osu files, expected {config.number_diffs}")
        return False
    entry.creators = beatmap.read_creators(osu_files)
    if not entry.creators:
        print(f"Error: {entry.label} has no Creator in its .osu files, so it can't be unmasked later")
        return False
    return True


def run() -> bool:
    config = load_config(CONFIG_PATH)
    api_key = load_api_key(TOKEN_PATH)
    if not MAPS_ZIP.exists():
        raise SetupError(f"{MAPS_ZIP.name} not found in {ROOT}")

    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        found = extract_entries(MAPS_ZIP, work_dir)
        entries = [e for e in found if validate_entry(e, config)]

        names = NameGenerator(creator for e in entries for creator in e.creators)
        for entry in entries:
            entry.anon_name = names.new_name()

        print("Anonymising .osz files")
        osz_dir = work_dir / "anonymised"
        osz_dir.mkdir()
        done = []
        for entry in entries:
            for warning in beatmap.anonymise_entry(entry.folder, entry.anon_name, config.taiko):
                print(f"Warning: {entry.label}: {warning}")

            leaks = beatmap.find_leaks(entry.folder, entry.creators, entry.anon_name)
            if leaks:
                print(f"Error: {entry.label} left out, it may not be fully anonymised:")
                for leak in leaks:
                    print(f"    {leak}")
                continue

            zip_folder(entry.folder, osz_dir / f"{config.tournament_name} ({entry.anon_name}).osz")
            done.append(entry)

        OUTPUT_DIR.mkdir()
        zip_folder(osz_dir, OUTPUT_DIR / "anonmaps.zip")

    mask_ok = mask.write_mask(OUTPUT_DIR / "masking.csv", [(e.creators[0], e.anon_name) for e in done], api_key)

    print(f"\nAnonymised {len(done)} entries into {OUTPUT_DIR / 'anonmaps.zip'}")
    if len(done) < len(found) or not mask_ok:
        print("Some entries need attention; see the errors above.")
    return mask_ok


def main() -> int:
    try:
        return 0 if run() else 1
    except SetupError as error:
        print(f"Error: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
