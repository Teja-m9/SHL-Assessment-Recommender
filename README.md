# SHL Assessment Assistant

This project contains a FastAPI backend and a React frontend for recommending SHL assessments from a curated catalog.

## What is implemented

- FastAPI chat API with health, chat, and session-clear endpoints
- Catalog-grounded assessment recommendations
- Senior Java skills matching and refinement logic
- Session-based chat history persistence with MongoDB support and in-memory fallback
- Optional Groq-based reply enhancement when a Groq API key is present
- Response metadata showing whether the final reply came from the catalog path or Groq enhancement
- Polished chat UI with thread-style messages, timestamps, sidebar history, and clear/new-session actions
- Automated tests and a production frontend build

## Local setup

1. Create a local environment file named .env at the project root.
2. Add your environment values, for example:

```env
MONGODB_URI=mongodb+srv://username:password@cluster0.example.mongodb.net/
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

- Backend: deploy the FastAPI app with the same environment variables as above.
- Frontend: deploy the Vite build output to Vercel, Netlify, or a similar static host.
- Set the frontend API base URL with VITE_API_URL if the backend is not running on the default local port.
- If MongoDB Atlas is temporarily unavailable in production, the backend now falls back to in-memory session storage instead of failing chat requests.

### Netlify configuration for this repo

This repository keeps the frontend inside `frontend/`, so Netlify should not use the repo root as the publish directory.

- Build command: `npm run build`
- Base directory: `frontend`
- Publish directory: `dist`
- Frontend environment variable: `VITE_API_URL=https://shl-assessment-recommender-1rql.onrender.com`

A root [netlify.toml](/abs/path/C:/Users/HP/Desktop/SHL-Assignment/netlify.toml:1) file is included so Netlify can pick up the correct settings automatically.
