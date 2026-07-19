# Courtside

Tennis analytics platform.

- `backend/` — FastAPI + SQLAlchemy (async) + Alembic, PostgreSQL (Supabase)
- `frontend/` — Next.js (App Router, TypeScript, Tailwind)

## Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload   # http://localhost:8000

# Frontend
cd frontend
npm install
npm run dev                 # http://localhost:3000
```
