# PocketSmart AI — Smart Budget & Recommendation Assistant

A complete FastAPI/Jinja2/SQLite application based on the supplied PocketSmart project documentation. The documented flow includes login/register, dashboard, Home/Party/Jewelry budget planners, Gemini recommendations, recommendation history, and shopping links. The implementation keeps those core flows while replacing fragile/incomplete snippets with a clean runnable codebase.

## VS Code setup
1. Install Python 3.11+.
2. Open this folder in VS Code.
3. Open Terminal and run:
   `python -m venv .venv`
4. Activate it: Windows PowerShell `.\.venv\Scripts\Activate.ps1`; macOS/Linux `source .venv/bin/activate`.
5. Run `pip install -r requirements.txt`.
6. Copy `.env.example` to `.env` and set `SECRET_KEY`.
7. For Gemini, add `GOOGLE_API_KEY=...` from Google AI Studio. If omitted, the app uses local fallback recommendations for testing.
8. Start: `uvicorn app.main:app --reload`.
9. Open `http://127.0.0.1:8000`.

## Test
`python -m pytest tests_smoke.py -q`
Health check: `http://127.0.0.1:8000/health`

## API endpoints
- POST `/register`
- POST `/token`
- POST `/logout`
- POST `/home-budget`
- POST `/party-budget`
- POST `/jewelry-budget` (multipart; optional image)
- GET `/api/recommendation-history`
- GET `/api/recommendation-details/{id}`
- GET `/session-info`

Never commit `.env` or a real API key.
