from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import dashboard

app = FastAPI(title="CPDV Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)


@app.get("/")
def root():
    return {"status": "ok", "name": "CPDV Dashboard API"}
