@echo off
rem ============================================================
rem  GRB Forge Inspector - drag .forge files ONTO this icon:
rem      one forge  = summary (types, entry count)
rem      two forges = diff by file ID (mod conflicts / overrides)
rem  (Prefer a window? Use "Forge Inspector (GUI).bat" instead.)
rem ============================================================
cd /d "%~dp0"
if "%~1"=="" (
  echo.
  echo   Drag one or two GRB .forge files onto this icon.
  echo     one forge  = summary
  echo     two forges = diff by file ID (conflict check)
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
%PYEXE% "forge_inspect.py" %*
echo.
pause
