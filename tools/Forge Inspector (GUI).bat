@echo off
rem ============================================================
rem  GRB Forge Inspector - double-click to open the tool window.
rem  Inspect a .forge, or compare two forges to find mod conflicts.
rem ============================================================
cd /d "%~dp0"
where pyw >nul 2>nul
if %errorlevel%==0 ( start "" pyw "forge_inspect_gui.py" %* & exit /b )
where pythonw >nul 2>nul
if %errorlevel%==0 ( start "" pythonw "forge_inspect_gui.py" %* & exit /b )
where py >nul 2>nul
if %errorlevel%==0 ( start "" py "forge_inspect_gui.py" %* & exit /b )
where python >nul 2>nul
if %errorlevel%==0 ( start "" python "forge_inspect_gui.py" %* & exit /b )
echo.
echo   Python was not found on this PC.
echo   Install it from  https://www.python.org/downloads/
echo   (tick "Add python.exe to PATH" during setup), then run this again.
echo.
pause
