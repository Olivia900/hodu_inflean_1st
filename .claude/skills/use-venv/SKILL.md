---
name: use-venv
description: Activate the project venv at venv/ before installing any Python package or running any Python file. Triggers on pip install, pip uninstall, python file.py, python -m, library setup, "라이브러리 설치", "구현", "실행" requests in this project. Never call the global pip or global python — always go through the project venv.
---

# Always work inside the project venv

This project keeps its dependencies in a `venv/` directory at the repository root. The user's global Python is shared with other projects and must NOT be polluted with this project's libraries.

> Paths below are written relative to the repository root. On Windows, the venv layout is `venv/Scripts/...`; on macOS/Linux, it's `venv/bin/...`.

## Rules

1. **Before any pip install / uninstall**, use the venv interpreter explicitly:
   - Windows (Bash/PowerShell): `venv/Scripts/python.exe -m pip install <pkg>`
   - macOS/Linux: `venv/bin/python -m pip install <pkg>`

2. **Before running any project Python file**, use the venv interpreter:
   - Windows: `venv/Scripts/python.exe path/to/file.py`
   - macOS/Linux: `venv/bin/python path/to/file.py`
   - Or activate first (see snippets below) and then call `python path/to/file.py`.

3. **Never** call bare `python ...` or `pip ...` for this project without first confirming the venv is active. PATH-resolved `python` is unreliable; prefer the explicit venv path or an explicit activation.

4. **Do not install this project's dependencies into the global Python.** If a global install is detected, uninstall it from there and reinstall into the venv.

5. When a new dependency is needed for an implementation task, install it into the venv first, then implement.

## Quick verification

```bash
# Windows
venv/Scripts/python.exe -c "import sys; print(sys.executable)"

# macOS/Linux
venv/bin/python -c "import sys; print(sys.executable)"
```

The printed path must point inside the project's `venv/` directory.

## Standard activation snippets

PowerShell (preferred on Windows for Korean terminal output, sets UTF-8 encoding):
```powershell
$OutputEncoding=[System.Text.Encoding]::UTF8
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING='utf-8'
& .\venv\Scripts\Activate.ps1
```

Git Bash (Windows):
```bash
source venv/Scripts/activate
```

Bash/Zsh (macOS/Linux):
```bash
source venv/bin/activate
```

After activation, plain `python` and `pip` resolve to the venv for the rest of the shell session.

## Initial venv setup (first clone)

If `venv/` does not exist yet on a fresh clone:
```bash
python -m venv venv
# then activate (see snippets above), then:
pip install requests beautifulsoup4
```
