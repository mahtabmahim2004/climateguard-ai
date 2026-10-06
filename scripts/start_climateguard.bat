@echo off
setlocal

rem Local convenience launcher only. It does not install dependencies, create environments,
rem change project data, or retrain models.
for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
set "DASHBOARD_URL=http://127.0.0.1:8000"
set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
set "LAUNCH_LOG=%TEMP%\ClimateGuardAI-server.log"

cd /d "%PROJECT_ROOT%" || (
    call :show_error "Could not open the ClimateGuard AI project folder."
    exit /b 1
)

rem If anything already answers at the configured dashboard URL, reuse it.
call :server_available
if not errorlevel 1 (
    start "" "%DASHBOARD_URL%"
    exit /b 0
)

if not exist "%PYTHON_EXE%" (
    call :show_error "The existing project interpreter was not found:%CRLF%%PYTHON_EXE%%CRLF%%CRLF%This launcher will not create or install an environment."
    exit /b 1
)

set "PATH=%PROJECT_ROOT%\.venv\Scripts;%PATH%"
set "PYTHONPATH=src"

rem Start only the project's existing webapp; keep its output outside project data.
start "" /B "%PYTHON_EXE%" -m climateguard.webapp >>"%LAUNCH_LOG%" 2>&1

rem Wait up to 45 seconds for the existing app to answer before opening the browser.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $until=(Get-Date).AddSeconds(45); do { try { $r=Invoke-WebRequest -UseBasicParsing -Uri '%DASHBOARD_URL%/api/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; Start-Sleep -Milliseconds 500 } while ((Get-Date) -lt $until); exit 1"
if errorlevel 1 (
    call :show_error "ClimateGuard AI did not become available at %DASHBOARD_URL%.%CRLF%The startup log is:%CRLF%%LAUNCH_LOG%"
    exit /b 1
)

start "" "%DASHBOARD_URL%"
exit /b 0

:server_available
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; try { $r=Invoke-WebRequest -UseBasicParsing -Uri '%DASHBOARD_URL%/api/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } } catch {}; exit 1" >nul 2>&1
exit /b %errorlevel%

:show_error
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Add-Type -AssemblyName System.Windows.Forms; [void][System.Windows.Forms.MessageBox]::Show('%~1','ClimateGuard AI launcher','OK','Error')"
exit /b 0
