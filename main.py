from fastapi import FastAPI
from app.database import create_db_and_tables

app = FastAPI(
    title="Pol-eat-heck API",
    description="API pour l'application de menus et réservations",
    version="1.0"
)

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

@app.get("/")
def root():
    return {"message": "Bienvenue sur l'API Pol-eat-heck"}

@app.get("/health")
def health_check():
    return {"status": "ok"}