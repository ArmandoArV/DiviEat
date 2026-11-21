# DiviEat


## Backend
Install uv if it is not already installed:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Set up the virtual environment:

```powershell
cd backend
uv sync --locked
```

Activate it in PowerShell:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uv run uvicorn app:app --reload
```

Activate it in Command Prompt (CMD):

```bat
cd backend
.\.venv\Scripts\activate.bat
uv run uvicorn app:app --reload
```

