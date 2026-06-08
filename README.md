# LRC Maker

A Python desktop tool for synchronizing lyrics to audio and exporting `.lrc` files.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- Load audio in popular formats: `.mp3` `.wav` `.ogg` `.flac` `.m4a` `.aac` `.wma` `.opus` `.mp4`
- Load a plain-text lyrics file (one line per line)
- **Two-panel layout** — left panel shows all lyrics with the current line highlighted; right panel shows timed entries as they are stamped
- **Hold-to-stamp**: press the `HOLD TO STAMP` button (or `Space`) when a line starts — release when it ends. The start timestamp is recorded and the next line is selected automatically
- Seek bar with drag-to-seek support
- Transport controls: restart (⏮), ±5 s skip, play/pause, stop
- Volume slider
- Prev / Next line buttons to manually navigate the lyrics list
- Click any line in the lyrics list to jump to it
- Undo last stamp, remove individual timed entries, or clear all stamps
- Line counter showing current position (e.g. `3 / 12`)
- Status bar with live feedback
- Exports standard `.lrc` format sorted by timestamp: `[mm:ss.xx]lyric line`

## Download

Pre-built Windows executable (no Python required):

👉 **[LyricsMaker.exe](dist/LyricsMaker.exe)**

## Requirements

- Python 3.10+
- [pygame-ce](https://github.com/pygame-community/pygame-ce) (audio playback)
- [mutagen](https://mutagen.readthedocs.io/) (audio duration detection)

## Installation

```bash
pip install -r requirements.txt
```

> **Note:** `requirements.txt` uses `pygame-ce` (the community edition), which ships pre-built wheels for Python 3.12+ and installs under the same `import pygame` namespace as the original package.

## Usage

```bash
python lrc_maker.py
```

1. Click **Load Audio** and pick your audio file.
2. Click **Load Lyrics (.txt)** and pick a plain-text file with one lyric line per line.
3. Click **▶ Play**.
4. For each line: **hold** the `HOLD TO STAMP` button (or `Space`) at the moment the line begins — release it when the line ends. The start timestamp is recorded and the cursor advances to the next line.
5. Use **Undo Last** if you mis-time a stamp, or select a timed entry and click **Remove Selected** to delete it individually.
6. Click **Save .lrc** when done.

## LRC format

```
[ti:Song Title]
[by:LRC Maker]

[00:12.34]First lyric line
[00:15.78]Second lyric line
```

## Building the executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name LyricsMaker lrc_maker.py
```

The resulting `dist/LyricsMaker.exe` bundles Python and all dependencies and runs without any installation.

## License

MIT — see [LICENSE](LICENSE).
