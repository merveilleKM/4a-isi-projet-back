from contextlib import asynccontextmanager
from fastapi import FastAPI
from app import models
from database import create_db_and_tables
from app.routers.users import users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code exécuté au démarrage
    create_db_and_tables()
    yield
    # Code exécuté à l'arrêt (rien pour l'instant)
    print("Arret")


app = FastAPI(
    title="Pol-eat-heck API",
    description="API pour l'application de menus et réservations",
    version="1.0",
    lifespan=lifespan,
)

app.include_router(users.router)


@app.get("/")
def root():
    return {"message": "Bienvenue sur l'API Pol-eat-heck"}


@app.get("/health")
def health_check():
    return {"status": "ok"}