"""Small helpers that talk to the operating system: folder picker and 'open folder'."""
import os
import subprocess
import sys


def pick_folder(prompt="Choose the folder with your photos"):
    """Open the system folder dialog and return the chosen path ('' if cancelled)."""
    try:
        if sys.platform == "darwin":
            script = f'POSIX path of (choose folder with prompt "{prompt}")'
            r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=900)
            return r.stdout.strip().rstrip("/") if r.returncode == 0 else ""
        if sys.platform.startswith("win"):
            ps = ("Add-Type -AssemblyName System.Windows.Forms;"
                  "$f=New-Object System.Windows.Forms.FolderBrowserDialog;"
                  f"$f.Description='{prompt}';"
                  "if($f.ShowDialog() -eq 'OK'){$f.SelectedPath}")
            r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               capture_output=True, text=True, timeout=900)
            return r.stdout.strip()
        r = subprocess.run(["zenity", "--file-selection", "--directory", f"--title={prompt}"],
                           capture_output=True, text=True, timeout=900)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def open_folder(path):
    """Show a folder in Finder / Explorer."""
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        elif sys.platform.startswith("win"):
            os.startfile(str(path))  # noqa
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        pass
