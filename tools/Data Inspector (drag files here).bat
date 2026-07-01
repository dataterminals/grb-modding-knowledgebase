@echo off
rem ============================================================
rem  GRB Data Inspector - drag one or more GRB .data files
rem  ONTO this icon to list the typed resources inside each.
rem  (Prefer a window? Use "Data Inspector (GUI).bat" instead.)
rem ============================================================
cd /d "%~dp0"
if "%~1"=="" (
  echo.
  echo   Drag one or more GRB .data files onto this icon
  echo   to list the typed resources inside each.
  echo.
  pause
  exit /b
)
set "PYEXE="
where py >nul 2>nul && set "PYEXE=py"
if not defined PYEXE ( where python >nul 2>nul && set "PYEXE=python" )
if not defined PYEXE (
  echo.
  echo   Python was not found on this PC.
  echo   Install it from  https://www.python.org/downloads/  then try again.
  echo.
  pause
  exit /b
)
%PYEXE% "data_inspect.py" %*
echo.
pause
