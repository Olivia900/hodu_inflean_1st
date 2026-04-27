---
name: use-venv
description: Activate the project venv at venv/ before installing any Python package or running any Python file. Triggers on pip install, pip uninstall, python file.py, python -m, library setup, "라이브러리 설치", "구현", "실행" requests in this project. Never call the global pip or global python here — always go through the venv.
---

# Always work inside the project venv

This project keeps its dependencies in `venv/` (located at `d:/hodu/source/korea_market_test/venv/`). The global Python on this machine is shared with other projects (ccxt, selenium, playwright, etc.) and must NOT be polluted with this project's libraries.

## Rules

1. **Before any pip install / uninstall**, use the venv interpreter explicitly:
   - Bash: `d:/hodu/source/korea_market_test/venv/Scripts/python.exe -m pip install <pkg>`
   - PowerShell (activated): `& d:\hodu\source\korea_market_test\venv\Scripts\Activate.ps1; pip install <pkg>`

2. **Before running any project Python file**, use the venv interpreter:
   - `d:/hodu/source/korea_market_test/venv/Scripts/python.exe path/to/file.py`
   - Or activate first: `& d:\hodu\source\korea_market_test\venv\Scripts\Activate.ps1; python path/to/file.py`

3. **Never** call bare `python ...` or `pip ...` for this project without first confirming the venv is active. On this Windows shell, bare `python` may resolve to the venv only when PATH happens to be set that way — do not rely on it. Use the absolute venv path or activate explicitly.

4. **Do not install this project's dependencies into the global Python** (`C:\Users\sjchoi\AppData\Local\Programs\Python\Python313\`). If a global install is detected, uninstall it from there and reinstall into the venv.

5. When a new dependency is needed for an implementation task, install it into the venv first, then implement.

## Quick verification

To confirm which interpreter you'd be using:

```bash
d:/hodu/source/korea_market_test/venv/Scripts/python.exe -c "import sys; print(sys.executable)"
```

Should print `D:\hodu\source\korea_market_test\venv\Scripts\python.exe`.

## Standard activation snippets

PowerShell (preferred for Korean terminal output, sets UTF-8 encoding):
```powershell
$OutputEncoding=[System.Text.Encoding]::UTF8
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING='utf-8'
& d:\hodu\source\korea_market_test\venv\Scripts\Activate.ps1
```

Bash (Git Bash):
```bash
source d:/hodu/source/korea_market_test/venv/Scripts/activate
```

After activation, plain `python` and `pip` resolve to the venv for the rest of the shell session.
