Using [fastapi-debug-toolbar](https://pypi.org/project/fastapi-debug-toolbar/)

Run the project

Locally

```bash
ROOT_PATH="" uv run uvicorn joke_api:app --host 0.0.0.0 --port 8000 --reload
```

Web Code Server

```bash
ROOT_PATH="/proxy/8000" uv run uvicorn joke_api:app --host 0.0.0.0 --port 8000 --reload
```
