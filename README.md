# Aegis

Autonomous multi-agent orbital collision de-confliction system — FastAPI + WebSocket backend, React/Vite + react-globe.gl frontend.

See [AGENTS.md](AGENTS.md) and the [`context/`](context/) folder before writing any code.

## Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```
