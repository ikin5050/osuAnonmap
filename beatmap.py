"""Anonymising a single extracted .osz entry, and checking the result."""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

ANONYMOUS_CREATOR = "Anonymous"
AUDIO_BASENAME = "audio"
BACKGROUND_BASENAME = "background"

# The only files an anonymised .osz may contain.
ALLOWED_FILE = re.compile(r"^(beatmap \(.+\)\.osu|(audio|background)\d*\.[^./\\]+)$")

# [Events] lines that are kept: backgrounds and break periods. Everything
# else (storyboard sprites, animations, samples, commands, videos) is dropped.
BACKGROUND_EVENTS = {"0", "Background"}
BREAK_EVENTS = {"2", "Break"}

# Sections made of "Key: value" lines. osu! itself writes a space after the
# colon in [General] and [Editor], and none in [Metadata] and [Difficulty].
KEY_VALUE_SECTIONS = {"General": ": ", "Editor": ": ", "Metadata": ":", "Difficulty": ":"}

# Values overwritten in every difficulty, as they can identify the mapper.
EDITOR_RESETS = {
    "Bookmarks": "",
    "DistanceSpacing": "1.4",
    "BeatDivisor": "4",
    "GridSize": "64",
    "TimelineZoom": "2.6",
}
METADATA_RESETS = {
    "Creator": ANONYMOUS_CREATOR,
    "Source": "",
    "Tags": "",
    "BeatmapID": "0",
    "BeatmapSetID": "-1",
}
TAIKO_DIFFICULTY_RESETS = {"CircleSize": "5", "ApproachRate": "5"}

# Metadata describing the contest song: identical for every entry, so it is
# not checked for the creator's name.
SONG_METADATA = {"Title", "TitleUnicode", "Artist", "ArtistUnicode"}


# --------------------------------------------------------------------------
# Reading .osu files
# --------------------------------------------------------------------------

def find_osu_files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".osu")


def read_lines(path: Path) -> list[str]:
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return [line.rstrip("\r\n") for line in f]


def iter_sections(lines: list[str]):
    """Yield (section, line_number, line) for every line that isn't a section header."""
    section = None
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
            continue
        yield section, number, line


def event_type(line: str) -> str:
    return line.split(",", 1)[0]


def is_kept_event(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("//"):
        return True
    return event_type(line) in BACKGROUND_EVENTS | BREAK_EVENTS


def split_hit_sample(line: str) -> tuple[str, list[str]] | None:
    """Split a hit object into (everything before the hitSample, hitSample fields).

    hitSample is "normalSet:additionSet:index:volume:filename"; returns None
    for hit objects written without one.
    """
    head, _, last = line.rpartition(",")
    fields = last.split(":")
    if not head or "|" in last or len(fields) != 5:
        return None
    return head, fields


def split_key_value(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    key, _, value = line.partition(":")
    return key.strip(), value.strip()


def read_creators(osu_files: list[Path]) -> list[str]:
    """The distinct Creator values across all difficulties, in file order."""
    creators: list[str] = []
    for path in osu_files:
        for section, _, line in iter_sections(read_lines(path)):
            pair = split_key_value(line) if section == "Metadata" else None
            if pair and pair[0] == "Creator" and pair[1] and pair[1] not in creators:
                creators.append(pair[1])
    return creators


# --------------------------------------------------------------------------
# Renaming audio and background files
# --------------------------------------------------------------------------

def find_file(folder: Path, reference: str) -> Path | None:
    """Resolve a filename referenced in an .osu file, ignoring case like osu! on Windows."""
    parts = [p for p in reference.replace("\\", "/").split("/") if p not in ("", ".")]
    if not parts or ".." in parts:
        return None
    current = folder
    for part in parts:
        if (current / part).exists():
            current = current / part
            continue
        if not current.is_dir():
            return None
        matches = [child for child in current.iterdir() if child.name.lower() == part.lower()]
        if not matches:
            return None
        current = matches[0]
    return current if current.is_file() else None


class AssetRenamer:
    """Collects the audio and background files referenced by the difficulties
    and gives them neutral names: audio.mp3, background.jpg, and so on.

    Every difficulty that uses the same file gets the same new name. A set
    with several different audio or background files gets numbered names
    (background.jpg, background2.jpg, ...). The original extension is kept.
    """

    def __init__(self, folder: Path):
        self.folder = folder
        self._by_source: dict[Path, str] = {}
        self._counts: dict[str, int] = {}

    def rename(self, reference: str, basename: str) -> str | None:
        """The new name for a referenced file, or None if the file doesn't exist."""
        source = find_file(self.folder, reference)
        if source is None:
            return None
        if source not in self._by_source:
            count = self._counts.get(basename, 0) + 1
            self._counts[basename] = count
            suffix = "" if count == 1 else str(count)
            self._by_source[source] = f"{basename}{suffix}{source.suffix}"
        return self._by_source[source]

    @property
    def new_names(self) -> set[str]:
        return set(self._by_source.values())

    def apply(self) -> None:
        """Move every referenced file to its new name in the top-level folder."""
        # Move everything aside first, so one rename can't overwrite a file
        # another rename still needs (e.g. two diffs with swapped names).
        staged = []
        for index, (source, new_name) in enumerate(self._by_source.items()):
            temporary = self.folder / f".anonymise-{index}"
            source.rename(temporary)
            staged.append((temporary, self.folder / new_name))
        for temporary, target in staged:
            if target.exists():
                target.unlink()  # an unreferenced file that happens to share the name
            temporary.rename(target)


# --------------------------------------------------------------------------
# Rewriting a difficulty
# --------------------------------------------------------------------------

class DifficultyRewriter:
    """Rewrites the lines of one .osu file. Lines it drops are left out."""

    def __init__(self, version: str, taiko: bool, renamer: AssetRenamer):
        self.version = version
        self.taiko = taiko
        self.renamer = renamer
        self.warnings: list[str] = []

    def rewrite(self, lines: list[str]) -> list[str]:
        output = []
        section = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                section = stripped[1:-1]
            elif section in KEY_VALUE_SECTIONS:
                line = self.key_value(section, line)
            elif section == "Events":
                line = self.event(line)
            elif section == "HitObjects" and stripped:
                line = self.hit_object(line)
            if line is not None:
                output.append(line)
        return output

    def key_value(self, section: str, line: str) -> str:
        pair = split_key_value(line)
        if pair is None:
            return line
        key, value = pair

        new_value = None
        if section == "General" and key == "AudioFilename" and value:
            new_value = self.renamer.rename(value, AUDIO_BASENAME)
            if new_value is None:
                self.warnings.append(f'audio file "{value}" is referenced but missing')
                new_value = AUDIO_BASENAME + os.path.splitext(value)[1]
        elif section == "Editor":
            new_value = EDITOR_RESETS.get(key)
        elif section == "Metadata":
            new_value = self.version if key == "Version" else METADATA_RESETS.get(key)
        elif section == "Difficulty" and self.taiko:
            new_value = TAIKO_DIFFICULTY_RESETS.get(key)

        if new_value is None:
            return line
        return f"{key}{KEY_VALUE_SECTIONS[section]}{new_value}"

    def event(self, line: str) -> str | None:
        """Keep breaks, rename the background, drop storyboard and video events."""
        if not is_kept_event(line):
            return None
        if event_type(line) in BACKGROUND_EVENTS:
            return self.background(line)
        return line

    def background(self, line: str) -> str | None:
        """Rename the file in 0,0,"filename",xOffset,yOffset. Dropped if the file is missing."""
        parts = line.split(",", 2)
        if len(parts) < 3:
            return None
        rest = parts[2].lstrip()
        if rest.startswith('"'):
            end = rest.find('"', 1)
            filename, tail = (rest[1:end], rest[end + 1:]) if end != -1 else ("", "")
        else:
            filename, separator, tail = rest.partition(",")
            tail = separator + tail

        new_name = self.renamer.rename(filename.strip(), BACKGROUND_BASENAME) if filename.strip() else None
        if new_name is None:
            return None  # no usable background: the map simply goes without one
        return f'{parts[0]},{parts[1]},"{new_name}"{tail}'

    def hit_object(self, line: str) -> str:
        # Custom hitsound files are not kept, so drop their filenames too.
        split = split_hit_sample(line)
        if split and split[1][4]:
            head, sample = split
            line = f"{head},{':'.join(sample[:4])}:"

        if self.taiko:
            # Move circles and spinners to the playfield centre (sliders untouched).
            fields = line.split(",")
            try:
                is_slider = int(fields[3]) & 2
            except (IndexError, ValueError):
                return line
            if not is_slider:
                line = ",".join(["256", "192", *fields[2:]])
        return line


# --------------------------------------------------------------------------
# Whole entry
# --------------------------------------------------------------------------

def anonymise_entry(folder: Path, anon_name: str, taiko: bool) -> list[str]:
    """Anonymise an extracted .osz in place, leaving only the difficulties,
    the audio and the background. Returns any warnings."""
    osu_files = find_osu_files(folder)
    renamer = AssetRenamer(folder)
    warnings: list[str] = []

    difficulties = []
    for number, path in enumerate(osu_files, start=1):
        version = anon_name if len(osu_files) == 1 else f"{anon_name} {number}"
        rewriter = DifficultyRewriter(version, taiko, renamer)
        difficulties.append((version, rewriter.rewrite(read_lines(path))))
        warnings += [w for w in rewriter.warnings if w not in warnings]

    renamer.apply()

    # Remove everything else: original difficulties, storyboards, videos,
    # hitsounds, skin elements, subfolders, editor and backup files.
    for path in folder.iterdir():
        if path.name in renamer.new_names:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    for version, lines in difficulties:
        with open(folder / f"beatmap ({version}).osu", "w", encoding="utf-8", newline="\n") as f:
            f.writelines(line + "\n" for line in lines)

    return warnings


# --------------------------------------------------------------------------
# Leak check
# --------------------------------------------------------------------------

def mentions(text: str, name: str) -> bool:
    """True if `name` appears in `text` as a standalone token, ignoring case."""
    pattern = r"(?<![a-z0-9])" + re.escape(name.lower()) + r"(?![a-z0-9])"
    return re.search(pattern, text.lower()) is not None


def texts_to_check(lines: list[str]):
    """Yield (line_number, text) for the parts of an .osu file a mapper could put their name in."""
    for section, number, line in iter_sections(lines):
        if section == "Metadata":
            pair = split_key_value(line)
            if pair and pair[0] in SONG_METADATA:
                continue
            yield number, line
        elif section in ("General", "Events"):
            yield number, line
        elif section == "HitObjects":
            split = split_hit_sample(line)
            if split and split[1][4]:
                yield number, split[1][4]


def find_leaks(folder: Path, creators: list[str], anon_name: str) -> list[str]:
    """Check an anonymised entry. Returns a list of problems; empty means it is clean."""
    problems = []

    for path in sorted(folder.rglob("*")):
        relative = path.relative_to(folder).as_posix()
        if path.is_dir() or not ALLOWED_FILE.match(relative):
            problems.append(f'unexpected file "{relative}"')
        for creator in creators:
            if mentions(relative, creator):
                problems.append(f'file name "{relative}" contains "{creator}"')

    for path in find_osu_files(folder):
        lines = read_lines(path)
        for section, number, line in iter_sections(lines):
            pair = split_key_value(line) if section == "Metadata" else None
            if pair and pair[0] == "Creator" and pair[1] != ANONYMOUS_CREATOR:
                problems.append(f'{path.name} line {number}: Creator is "{pair[1]}"')
            if pair and pair[0] == "Version" and not pair[1].startswith(anon_name):
                problems.append(f'{path.name} line {number}: Version is "{pair[1]}"')
            if section == "Events" and not is_kept_event(line):
                problems.append(f"{path.name} line {number}: storyboard event remains")

        for creator in creators:
            if not any(c.isalpha() for c in creator):
                continue  # all-digit names match timestamps and coordinates
            for number, text in texts_to_check(lines):
                if mentions(text, creator):
                    problems.append(f'{path.name} line {number} contains "{creator}": {text.strip()}')

    return problems
