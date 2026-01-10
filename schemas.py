from pydantic import BaseModel
from typing import Optional
from decimal import Decimal

# --- Produkty ---
class ProductBase(BaseModel):
    nazwa_modelu: str
    cena_katalogowa: Decimal
    zdjecie_url: Optional[str] = None
    stan_magazynowy: int

    class Config:
        orm_mode = True

# --- Rejestracja ---
class UserCreate(BaseModel):
    imie: str
    nazwisko: str
    email: str
    password: str

# --- Login (Token) ---
class Token(BaseModel):
    access_token: str
    token_type: str