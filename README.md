# LazyWin11Installer

LazyWin11Installer is a **command-line tool** to quickly set up a fresh Windows 11 installation with your favorite presets, browsers, antivirus, and optional system cleanup using Tron. It’s designed to make post-install tuning fast and easy.

## Features

- Select from multiple **presets**:
  - Gamer → Steam, Roblox, Lunar Client
  - Developer → Python, Visual Studio, VS Code, Git, Node.js
  - Secondary PC → 7zip, VLC, Firefox/Chrome, Notepad++
  - Streamer / Content Creator, Productivity / School, Clean Minimalist, Work / Corporate, Kids / Family
- Choose your **browser**: Edge (default), Chrome, Firefox, or Firefox Nightly
- Optional **antivirus installation**
- Optional **Tron cleanup** (removes bloat, cleans registry, optimizes system)
- Supports **dry-run mode** (`--dry-run`) to see what would be installed without making changes
- **Admin elevation** handled automatically

## Requirements

- Windows 11
- Python 3.10+ (or use the packaged EXE)
- Winget installed and working (`winget --version`)

## Usage

### Run from Python
```powershell
py lazywin11_installer.py
