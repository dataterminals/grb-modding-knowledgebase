@echo off
rem ============================================================
rem  GRB Cloth Inspector - drag one or two cloth .data files
rem  ONTO this icon:
rem      one file  = inspect it
rem      two files = compare them side by side
rem  (Prefer a window? Use "Cloth Inspector (GUI).bat" instead.)
rem ============================================================
cd /d "%~dp0"
if "%~1"=="" (
  echo.
  echo   Drag one or two GRB cloth .data files onto this icon.
  echo     one file  = inspect it
  echo     two files = compare them
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
%PYEXE% "cloth_inspect.py" %*
echo.
pause
