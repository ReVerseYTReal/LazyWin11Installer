#!/usr/bin/env python3
"""
LazyWin11Installer - Final CLI release (Python)

Usage:
  py lazywin11_installer.py       # interactive run (will request elevation)
  py lazywin11_installer.py --dry-run   # shows actions but doesn't perform installs
"""

import os
import sys
import subprocess
import ctypes
import time
import logging
from pathlib import Path

# -------------- Config & Logging --------------
APP_NAME = "LazyWin11Installer"
LOG_DIR = Path(r"C:\LazyWin11Installer")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "lazywin11.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(message)s")
console.setFormatter(formatter)
logging.getLogger("").addHandler(console)

DRY_RUN = "--dry-run" in sys.argv

def log(msg, level="info"):
    if level == "info":
        logging.info(msg)
    elif level == "warning":
        logging.warning(msg)
    elif level == "error":
        logging.error(msg)
    else:
        logging.debug(msg)

# -------------- Helpers --------------
def run_cmd(cmd, capture_output=True, shell=True, check=False, dry_run=False):
    log(f"> {cmd}")
    if dry_run:
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="(dry-run)", stderr="")
    try:
        proc = subprocess.run(cmd, capture_output=capture_output, text=True, shell=shell)
        log(f"Return code: {proc.returncode}")
        if proc.stdout:
            logging.debug(proc.stdout.strip())
        if proc.stderr:
            logging.debug(proc.stderr.strip())
        if check and proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, output=proc.stdout, stderr=proc.stderr)
        return proc
    except Exception as e:
        log(f"Command failed: {e}", level="error")
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr=str(e))

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def require_admin():
    if is_admin():
        return True
    # Re-run the script with admin rights
    log("Requesting administrative privileges (UAC)...", level="info")
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    sys.exit(0)

# -------------- Winget helpers --------------
def winget_available():
    return shutil_which("winget") is not None

def shutil_which(cmd):
    # avoid importing shutil at top to keep clarity; this is a tiny reimplementation using PATH
    from shutil import which
    return which(cmd)

def is_installed_winget(pkg_id):
    # Check with `winget list --id <pkg_id>` and look for a result
    cmd = f'winget list --id {pkg_id}'
    proc = run_cmd(cmd, capture_output=True, shell=True, dry_run=DRY_RUN)
    if DRY_RUN:
        return False
    if proc.returncode != 0:
        return False
    out = (proc.stdout or "").lower()
    return pkg_id.lower() in out or ("name" in out and len(out.splitlines()) > 2)

def winget_install(pkg_id, retries=1):
    if DRY_RUN:
        log(f"(dry-run) Would install {pkg_id}")
        return True

    if is_installed_winget(pkg_id):
        log(f"{pkg_id} already installed — skipping.")
        return True

    cmd = f'winget install --silent --accept-source-agreements --accept-package-agreements --id {pkg_id}'
    for attempt in range(1, retries+2):
        proc = run_cmd(cmd, capture_output=True, shell=True, dry_run=False)
        if proc.returncode == 0:
            log(f"Installed {pkg_id} successfully.")
            return True
        else:
            log(f"Attempt {attempt} failed for {pkg_id} (code {proc.returncode}).", level="warning")
            time.sleep(2)
    log(f"Failed to install {pkg_id} after {retries+1} attempts.", level="error")
    return False

# -------------- Tron handler --------------
def run_tron(dry_run=False):
    log("WARNING: Tron is a heavy cleanup tool. Create a VM snapshot / backup before running.", level="warning")
    if dry_run:
        log("(dry-run) Would download and run Tron.")
        return True

    tmp = LOG_DIR / "tron_tmp"
    tmp.mkdir(exist_ok=True)
    zip_path = tmp / "tron.zip"
    url = "https://github.com/bmrf/tron/releases/latest/download/tron.zip"
    cmd_dl = f'powershell -Command "Invoke-WebRequest -Uri {url} -OutFile {zip_path}"'
    run_cmd(cmd_dl, dry_run=False)
    cmd_extract = f'powershell -Command "Expand-Archive -LiteralPath {zip_path} -DestinationPath {tmp} -Force"'
    run_cmd(cmd_extract, dry_run=False)
    # Find the extracted subfolder containing tron.bat
    found = None
    for child in tmp.iterdir():
        if child.is_dir() and any((child / "tron.bat").exists() for _ in [0]):
            if (child / "tron.bat").exists():
                found = child
                break
    if not found:
        # fallback look
        for child in tmp.rglob("tron.bat"):
            found = child.parent
            break
    if not found:
        log("Could not find tron.bat after extracting. Aborting Tron run.", level="error")
        return False
    tron_bat = found / "tron.bat"
    log(f"Running Tron from: {tron_bat}", level="info")
    run_cmd(f'cmd /c "{tron_bat}"', dry_run=False)
    return True

# -------------- Presets (mapping preset name -> list of winget IDs) --------------
PRESETS = {
    "Gamer": [
        "Valve.Steam",
        "Roblox.Roblox",
        "Moonsworth.LunarClient"
    ],
    "Developer": [
        "Python.Python.3",
        "Microsoft.VisualStudio.2022.Community",
        "Microsoft.VisualStudioCode",
        "Git.Git",
        "OpenJS.NodeJS"
    ],
    "Secondary PC": [
        "7zip.7zip",
        "VideoLAN.VLC",
        "Mozilla.Firefox",
        "Google.Chrome",
        "Notepad++.Notepad++"
    ],
    "Streamer / Content Creator": [
        "OBSProject.OBSStudio",
        "Streamlabs.Streamlabs",
        "Discord.Discord",
        "Audacity.Audacity",
        "DaVinciResolve.DaVinciResolve",
        "Spotify.Spotify",
        "VideoLAN.VLC"
    ],
    "Productivity / School": [
        # Microsoft.Office may not be available via winget in all regions (store-based). We'll attempt it but it might fail.
        "Microsoft.Office",
        "Notion.Notion",
        "Google.Drive",
        "Zoom.Zoom",
        "Spotify.Spotify"
    ],
    "Clean Minimalist": [
        "7zip.7zip",
        "Notepad++.Notepad++",
        "Mozilla.Firefox",
        "voidtools.Everything",
        "VideoLAN.VLC"
    ],
    "Work / Corporate": [
        "Google.Chrome",
        "Microsoft.Office",
        "Microsoft.Teams",
        "Zoom.Zoom",
        "SlackTechnologies.Slack",
        "Git.Git"
    ],
    "Kids / Family Mode": [
        "Minecraft.MinecraftLauncher",
        "Roblox.Roblox",
        "Google.Chrome",
        "Spotify.Spotify",
        "VideoLAN.VLC"
    ]
}

# Antivirus mapping: friendly label -> winget ID (if available)
ANTIVIRUS_OPTIONS = {
    "None": None,
    "Malwarebytes": "Malwarebytes.Malwarebytes",
    "Avast": "Avast.AntivirusFree",
    "Bitdefender": "Bitdefender.TotalSecurity"  # might be different — winget can fail depending on vendor listing
}

# Browser mapping label -> winget id
BROWSERS = {
    "Edge (keep default)": None,
    "Chrome": "Google.Chrome",
    "Firefox": "Mozilla.Firefox",
    "Firefox Nightly": "Mozilla.Firefox.Nightly"
}

# -------------- Interactive helpers --------------
def ask(question, options):
    print()
    print(question)
    for i, opt in enumerate(options, 1):
        print(f"  {i}. {opt}")
    while True:
        choice = input("> ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        print("Invalid choice. Pick the number.")

def apply_preset(preset_name, dry_run=False):
    if preset_name not in PRESETS:
        log(f"Preset '{preset_name}' not recognized.", level="error")
        return
    pkgs = PRESETS[preset_name]
    log(f"Applying preset '{preset_name}' ({len(pkgs)} packages).")
    for pkg in pkgs:
        success = winget_install(pkg)
        if not success:
            log(f"Package {pkg} failed to install. You can re-run the script later or install manually.", level="warning")

def install_browser(browser_label):
    pkg = BROWSERS.get(browser_label)
    if not pkg:
        log("Keeping Microsoft Edge as default.")
        return
    winget_install(pkg)

def install_antivirus(av_label):
    pkg = ANTIVIRUS_OPTIONS.get(av_label)
    if not pkg:
        log("Skipping antivirus (using Windows Defender).")
        return
    winget_install(pkg)

# -------------- Main --------------
def main():
    log(f"{APP_NAME} starting. Dry-run={DRY_RUN}")

    # Quick sanity: check winget exists (we'll still try even if not present, user will get error)
    if not shutil_which("winget"):
        log("WARNING: 'winget' not found on this system PATH. Winget operations will fail.", level="warning")

    preset = ask("Select a preset:", list(PRESETS.keys()) + ["None"])
    if preset == "None":
        preset = None

    browser = ask("Pick a browser:", list(BROWSERS.keys()))
    av = ask("Install antivirus?", list(ANTIVIRUS_OPTIONS.keys()))
    tron_choice = ask("Run Tron cleanup script? (advanced - recommended only in VM)", ["No", "Yes"])

    print("\n=== SUMMARY ===")
    print(f"Preset: {preset or 'None'}")
    print(f"Browser: {browser}")
    print(f"Antivirus: {av}")
    print(f"Run Tron: {tron_choice}")
    print("--------------------------")
    input("Press ENTER to begin (or Ctrl-C to cancel)...")

    # Elevate (restarts the script under admin if needed)
    if not is_admin():
        if DRY_RUN:
            log("(dry-run) skipping UAC elevation.")
        else:
            require_admin()

    # Apply preset
    if preset:
        apply_preset(preset, dry_run=DRY_RUN)

    # Browser
    install_browser(browser)

    # Antivirus
    install_antivirus(av)

    # Tron
    if tron_choice == "Yes":
        run_tron(dry_run=DRY_RUN)

    log("All requested actions finished. Check the log for details: " + str(LOG_FILE))
    print("\nDone. If anything failed, consult the log above and re-run the script or install manually.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("User canceled.", level="warning")
        print("\nCanceled by user.")
    except Exception as e:
        log(f"Unhandled exception: {e}", level="error")
        raise
