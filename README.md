# LRC Maker

A Python desktop tool for synchronizing lyrics to audio and exporting `.lrc` files.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- Load audio in popular formats: `.mp3` `.wav` `.ogg` `.flac` `.m4a` `.aac` `.wma` `.opus`
- Load a plain-text lyrics file (one line per line)
- Scrollable lyrics list — all lines visible, current line highlighted
- **Hold-to-stamp**: press a button (or `Space`) when a line starts singing, release when it ends — timestamps are recorded and the next line is selected automatically
- Seek bar, ±5 s skip, play/pause/stop controls
- Undo last stamp, remove individual entries, or clear all
- Click any line in the list to jump to it
- Exports standard `.lrc` format: `[mm:ss.xx]lyric line`

## Requirements

- Python 3.10+
- [pygame-ce](https://github.com/pygame-community/pygame-ce) (audio playback)
- [mutagen](https://mutagen.readthedocs.io/) (audio duration detection)

## Installation

```bash
pip install -r requirements.txt
```

> **Note:** `requirements.txt` uses `pygame-ce` (the community edition), which ships pre-built wheels for Python 3.12+. It installs under the same `import pygame` namespace as the original package.

## Usage

```bash
python lrc_maker.py
```

1. Click **Load Audio** and pick your audio file.
2. Click **Load Lyrics (.txt)** and pick a plain-text file with one lyric line per line.
3. Click **▶ Play**.
4. For each line: **hold** the `HOLD TO STAMP` button (or `Space`) at the moment the line begins — release it when the line ends. The tool records both timestamps and advances to the next line.
5. Use **Undo Last** if you mis-time a stamp.
6. Click **Save .lrc** when done.

## LRC format

```
[ti:Song Title]
[by:LRC Maker]

[00:12.34]First lyric line
[00:15.78]Second lyric line
```

## License

MIT — see [LICENSE](LICENSE).
