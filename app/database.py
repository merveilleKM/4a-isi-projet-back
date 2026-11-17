from sqlmodel import SQLModel, create_engine, Session

# Nom du fichier de la base de données SQLite
sqlite_file_name = "database.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

# Création du moteur de connexion
engine = create_engine(sqlite_url, echo=True)

def create_db_and_tables():
    """Crée toutes les tables définies avec SQLModel"""
    SQLModel.metadata.create_all(engine)

def get_session():
    """Fournit une session de base de données (utile pour les dépendances FastAPI)"""
    with Session(engine) as session:
        yield session