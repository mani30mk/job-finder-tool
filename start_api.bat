@echo off
echo Starting Job Hunter API...

if not exist .env (
    echo Warning: .env file not found! Copy .env.example to .env and fill in your API keys.
)

set PORT=8000
uvicorn api.main:app --host 0.0.0.0 --port %PORT% --reload
