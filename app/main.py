from contextlib import asynccontextmanager
from fastapi import FastAPI

from app import models  # noqa: F401  (l'import suffit à enregistrer les tables)
from app.database import create_db_and_tables
from app.routers import users, products


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Démarrage : création des tables
    create_db_and_tables()
    yield
    # Arrêt : rien à nettoyer pour l'instant


app = FastAPI(
    title="Pol-eat-heck API",
    description="API pour l'application de menus et réservations",
    version="1.0",
    lifespan=lifespan,
)

app.include_router(users.router)
app.include_router(products.router)


@app.get("/")
def root():
    return {"message": "Bienvenue sur l'API Pol-eat-heck"}


@app.get("/health")
def health_check():
    return {"status": "ok"}