from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import dashboard, analysis, bridges, llm, command

app = FastAPI(title="CPDV Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(analysis.router)
app.include_router(bridges.router)
app.include_router(llm.router)
app.include_router(command.router)


@app.get("/")
def root():
    return {"status": "ok", "name": "CPDV Dashboard API"}
