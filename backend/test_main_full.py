import sys
sys.path.insert(0, '.')

from routes import algorithm, dashboard, analysis, bridges, llm, command, external_code
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import ws
import config

app = FastAPI(title="CPDV Dashboard API")

_origins_env = config._env_str(
    "CPDV_ALLOW_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
)
ALLOW_ORIGINS = [o.strip() for o in _origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)

# Include routers exactly like main.py
app.include_router(dashboard.router)
app.include_router(analysis.router)
app.include_router(bridges.router)
app.include_router(llm.router)
app.include_router(command.router)
app.include_router(command._meta_router)
app.include_router(external_code.router)
app.include_router(algorithm.router)
app.include_router(ws.router)

print("App routes:")
for r in app.routes:
    if hasattr(r, 'path'):
        methods = getattr(r, 'methods', '')
        path = r.path
        if path is None:
            path = "NO PATH"
        print(f'  {methods} {path}')