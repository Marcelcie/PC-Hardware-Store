from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# 1. Załaduj zmienne z pliku .env
load_dotenv()

# 2. Pobierz adres bazy danych
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Zabezpieczenie na wypadek braku wpisu w .env
if not SQLALCHEMY_DATABASE_URL:
    raise ValueError("BŁĄD: Nie znaleziono DATABASE_URL w pliku .env")

# 3. Utwórz silnik bazy danych (engine)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 4. Utwórz fabrykę sesji (to pozwala na zapytania do bazy)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 5. Baza dla modeli
Base = declarative_base()

# 6. Funkcja (Dependency), której używamy w main.py do pobrania sesji
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()