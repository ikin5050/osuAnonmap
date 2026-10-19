# osuAnonmap
Essentially the same tool as https://github.com/pishifat/contest-anonymization#readme but in Python, using only the standard library (Python 3.10 or newer, nothing to install).

## Setup

1. In the folder containing these Python files, put a zip file named `maps.zip`, formatted like the MPG contest download: a zip containing a folder per entrant (named after the creator), each containing an .osz file.
2. Edit `config.json`:
   - `tournamentName`: used in the output file names.
   - `numberDiffs`: the exact number of difficulties each entry must have. `0` allows any number.
   - `taiko`: set to `"True"` for taiko contests.
3. Create `token.json` with your legacy osu! API key (found under the settings on your profile page):
   ```
   {
     "token": "<your legacy osuAPI token>"
   }
   ```

## Running

Navigate to the folder you stored this code in and run:
```
python ./main.py
```

In the `output` folder you will find:
- `anonmaps.zip`: the anonymised .osz files.
- `masking.csv`: in the exact format MPG requires to undo the anonymisation.

For contest integrity, do NOT share `masking.csv`. Also do NOT share `token.json`, as it holds your personal osu! API key.

## What gets anonymised

Each entry gets a random "Adjective Noun" name, e.g. `Rich Cat`. In each .osz:

- Difficulties are renamed `beatmap (Rich Cat).osu`. Their Version becomes the anonymous name (numbered if there are several difficulties).
- The creator is set to `Anonymous`. Source, tags, bookmarks and beatmap IDs are cleared, and editor settings (distance spacing, beat divisor, grid size, timeline zoom) are reset.
- The audio file is renamed `audio` and the background `background`, keeping their file format (e.g. `audio.mp3`, `audio.ogg`, `background.jpg`). If different difficulties use different files, they are numbered (`background2.jpg`).
- A map without a background (or whose background file is missing) is still anonymised, just without a background.
- Only the .osu files, the audio and the background are kept. Everything else is removed: storyboards (both the .osb file and storyboard events inside the .osu), videos, custom hitsounds, skin elements, subfolders, and any backup or external editor files.
- Break periods are kept. References to removed hitsound files are cleared, so those notes use the default hitsounds.
- Taiko only: CS and AR are set to 5, and circles and spinners are moved to the centre of the playfield.

## Checks

- **Names**: every anonymous name is unique, and never shares a word with any entrant's username (an entrant called "Happy" rules out "Happy Cat" for everyone). The word lists only contain neutral or positive words, so a name can't put judges off an entry.
- **Leaks**: after anonymising, each entry is checked for its creator's name in file names, the remaining metadata and events, for any file other than the .osu files, audio and background, and for leftover storyboard events. An entry that fails this check is left out of the output and listed with the reason, so you can fix it by hand.
- Entries with the wrong number of difficulties, no Creator, or a broken .osz are also left out and reported.
