# SHL Assessment Assistant

This project contains a FastAPI backend and a React frontend for recommending SHL assessments from a local catalog snapshot.

## What is implemented

- `GET /health` returns `{"status": "ok"}`
- `POST /chat` is stateless and only accepts the full `messages` history
- Response schema matches the assignment contract:
  - `reply`
  - `recommendations`
  - `end_of_conversation`
- Extended metadata for UI and evaluation:
  - `state`
  - `comparison_summary`
  - `reply_source`
  - `llm_model`
- Clarification, recommendation, refinement, comparison, and in-scope refusal behavior
- Catalog-grounded recommendations only
- Confidence scores per recommendation
- Optional Groq rewriting without changing the response schema
- React frontend that sends the full conversation history on every request
- Frontend badges for response source/model and state
- Evaluation harness includes multi-persona recruiter trace suite
- Automated backend tests and a production frontend build

## Catalog format

The runtime app reads [app/catalog.json](/abs/path/C:/Users/HP/Desktop/SHL-Assignment/app/catalog.json:1).

The repo also includes `app/services/catalog_import_service.py`, which imports a prepared SHL catalog export into the normalized app format. That keeps the app offline-friendly while letting you swap in a fuller catalog snapshot without changing the agent logic.

## Local setup

1. Create a local `.env` file at the project root.
2. Add your environment values, for example:

```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-8b-instant
GROQ_TEMPERATURE=0.2
GROQ_MAX_TOKENS=220
```

3. Install backend dependencies:

```bash
uv pip install -r requirements.txt
```

4. Start the backend:

```bash
uv run uvicorn app.main:app --reload
```

5. Start the frontend:

```bash
cd frontend
npm install
npm run dev
```

## Test and build

Backend tests:

```bash
uv run python -m pytest -q
```

Frontend production build:

```bash
cd frontend
npm run build
```

## Deployment notes

- Backend: deploy the FastAPI app as-is.
- Frontend: deploy `frontend/dist` to Netlify, Vercel, or a similar static host.
- Set `VITE_API_URL` if the backend is not running on `http://127.0.0.1:8000`.
- `netlify.toml` is already configured for the `frontend/` subdirectory.
