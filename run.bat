@echo off

:: Get the path of the script
set "SCRIPT_PATH=%~dp0"

:: Check if the script is running with Administrator privileges
net session >nul 2>&1
if %errorlevel% equ 0 (
    :: Load REMOTE_MOUNT from .env file
    set "REMOTE_MOUNT="

    for /f "usebackq tokens=1,* delims==" %%A in ("%SCRIPT_PATH%.env") do (
        if /i "%%A"=="REMOTE_MOUNT" (
            set "REMOTE_MOUNT=%%B"
        )
    )

    if defined REMOTE_MOUNT (
        :: Unmap anything already on Z
        :: net use Z: /delete

        :: Map the REMOTE_MOUNT location to Z
        net use Z: %REMOTE_MOUNT%
    )

    :: Run the Python script
    call "%SCRIPT_PATH%env\Scripts\activate"
    python "%SCRIPT_PATH%cli.py"
    deactivate

    pause
) else (
    echo Script must be run with Administrator privileges.
    pause
)
