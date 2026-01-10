from sqlalchemy import Column, Integer, String, Boolean, Float, Numeric, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Klient(Base):
    __tablename__ = "klient"

    id_klienta = Column(Integer, primary_key=True, index=True)
    imie = Column(String(50), nullable=False)
    drugie_imie = Column(String(50), nullable=True)
    nazwisko = Column(String(50), nullable=False)
    adres_email = Column(String(40), unique=True, nullable=False)
    haslo_hash = Column(String(255), nullable=False)
    data_rejestracji = Column(DateTime, default=datetime.now, nullable=False)

class Kategoria(Base):
    __tablename__ = "kategoria"

    id_kategorii = Column(Integer, primary_key=True, index=True)
    nazwa_kategorii = Column(String(50), nullable=False)
    opis_kategorii = Column(String(255))

class ModelProduktu(Base):
    __tablename__ = "model_produktu"

    id_modelu = Column(Integer, primary_key=True, index=True)
    nazwa_modelu = Column(String(100), nullable=False)
    opis = Column(Text, nullable=True)
    cena_katalogowa = Column(Float, nullable=False) 
    zdjecie_url = Column(String(255), nullable=True)
    stan_magazynowy = Column(Integer, default=100)
    
    id_kategorii = Column(Integer, ForeignKey("kategoria.id_kategorii"), nullable=False)

# --- NOWOŚĆ: Tabela Zamówień ---
class Zamowienie(Base):
    __tablename__ = "zamowienie"

    id_zamowienia = Column(Integer, primary_key=True, index=True)
    numer_zamowienia = Column(String(50), unique=True, nullable=False)
    data_zlozenia = Column(DateTime, nullable=False)
    status_zamowienia = Column(String(20), nullable=False)
    suma_calkowita = Column(Float, nullable=False)
    
    # Klucz obcy do klienta
    id_klienta = Column(Integer, ForeignKey("klient.id_klienta"), nullable=False)

# --- NOWOŚĆ: Koszyk w bazie danych ---
class ElementKoszyka(Base):
    __tablename__ = "element_koszyka"

    id_elementu = Column(Integer, primary_key=True, index=True)
    ilosc = Column(Integer, default=1)
    
    # Klucze obce
    id_klienta = Column(Integer, ForeignKey("klient.id_klienta"), nullable=False)
    id_adresu = Column(Integer, nullable=False)
    id_modelu = Column(Integer, ForeignKey("model_produktu.id_modelu"), nullable=False)

    # Relacje (żeby łatwo pobrać nazwę produktu i cenę)
    model = relationship("ModelProduktu")