@echo off
rem ============================================================
rem  GRB Cloth Inspector - double-click to open the tool window.
rem  (You can also drag one or two cloth .data files onto this
rem   icon to open them straight away.)
rem ============================================================
cd /d "%~dp0"
where pyw >nul 2>nul
if %errorlevel%==0 ( start "" pyw "cloth_inspect_gui.py" %* & exit /b )
where pythonw >nul 2>nul
if %errorlevel%==0 ( start "" pythonw "cloth_inspect_gui.py" %* & exit /b )
where py >nul 2>nul
if %errorlevel%==0 ( start "" py "cloth_inspect_gui.py" %* & exit /b )
where python >nul 2>nul
if %errorlevel%==0 ( start "" python "cloth_inspect_gui.py" %* & exit /b )
echo.
echo   Python was not found on this PC.
echo   Install it from  https://www.python.org/downloads/
echo   (tick "Add python.exe to PATH" during setup), then run this again.
echo.
pause
