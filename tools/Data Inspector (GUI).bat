@echo off
rem ============================================================
rem  GRB Data Inspector - double-click to open the tool window.
rem  (You can also drag one or more .data files onto this icon
rem   to inspect them straight away.)
rem ============================================================
cd /d "%~dp0"
where pyw >nul 2>nul
if %errorlevel%==0 ( start "" pyw "data_inspect_gui.py" %* & exit /b )
where pythonw >nul 2>nul
if %errorlevel%==0 ( start "" pythonw "data_inspect_gui.py" %* & exit /b )
where py >nul 2>nul
if %errorlevel%==0 ( start "" py "data_inspect_gui.py" %* & exit /b )
where python >nul 2>nul
if %errorlevel%==0 ( start "" python "data_inspect_gui.py" %* & exit /b )
echo.
echo   Python was not found on this PC.
echo   Install it from  https://www.python.org/downloads/
echo   (tick "Add python.exe to PATH" during setup), then run this again.
echo.
pause
