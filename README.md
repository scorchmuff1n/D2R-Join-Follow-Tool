# D2R Join/Follow Tool

A small Windows helper for Diablo II: Resurrected that creates and joins numbered games (like `baal-1`, `baal-2`, ...) with one hotkey.

![D2R Join/Follow Tool](screenshots/main-window.png)

## Download
Get the latest zip from the [Releases page](https://github.com/scorchmuff1n/D2R_Join_Follow_Tool_v1.0/releases/latest), unzip it and run the tool.

## Features
- Set a game prefix, password, start number and difficulty
- **Create Next Game** / **Join Next Game** buttons
- Auto-create the next game after you exit, with a short delay you can set

## Hotkeys (only while D2R is the active window)
| Key | Action |
|-----|--------|
| `HOME` | Create next game |
| `END` | Join next game |
| `DELETE` | Save and exit (opens the ESC menu and clicks Save and Exit), then auto-create the next game |

## Notes
- Click positions are calibrated for a 1648x924 game window.

## Running from source
Requires Python 3 on Windows (uses only the standard library, tkinter included). Run `Launch_D2R_Join_Follow_Tool.bat` or `python D2R_Join_Follow_Tool.py`.

## License
MIT, see [LICENSE](LICENSE).

## Disclaimer
Fan-made tool, not affiliated with Blizzard Entertainment. Use at your own risk.
