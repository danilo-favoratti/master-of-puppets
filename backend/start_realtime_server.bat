@echo off
rem Start the realtime agent server

rem Activate the virtual environment if it exists
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

rem Check if Deepgram API key is set
if "%DEEPGRAM_API_KEY%"=="" (
    echo Warning: DEEPGRAM_API_KEY environment variable is not set.
    echo It will be loaded from .env file if available.
)

rem Run the server
python -m backend.main_realtime 