from sqlalchemy import Column, Integer, String, Boolean, Float, Numeric, DateTime, Text, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

# --- TABELE ---

class Adres(Base):
    __tablename__ = "adres"
    id_adresu = Column(Integer, primary_key=True, index=True)
    ulica = Column(String(100))
    nr_domu = Column(String(10), nullable=False)
    nr_lokalu = Column(String(10), nullable=True)
    kod_pocztowy = Column(String(6), nullable=False)
    miejscowosc = Column(String(50), nullable=False)

class Rola(Base):
    __tablename__ = "rola"
    id_roli = Column(Integer, primary_key=True, index=True)
    nazwa_roli = Column(String(30), nullable=False)

class Klient(Base):
    __tablename__ = "klient"
    id_klienta = Column(Integer, primary_key=True, index=True)
    imie = Column(String(50), nullable=False)
    drugie_imie = Column(String(50), nullable=True)
    nazwisko = Column(String(50), nullable=False)
    adres_email = Column(String(40), unique=True, nullable=False)
    haslo_hash = Column(String(255), nullable=False)
    data_rejestracji = Column(DateTime, default=datetime.now, nullable=False)

class KlientAdres(Base):
    __tablename__ = "klient_adres"
    # Klucz złożony (composite key) zgodnie z Twoim SQL
    klient2id_klienta = Column(Integer, ForeignKey("klient.id_klienta"), primary_key=True)
    adres2id_adresu = Column(Integer, ForeignKey("adres.id_adresu"), primary_key=True)
    czy_domyslny = Column(Boolean, default=False)

class Pracownik(Base):
    __tablename__ = "pracownik"
    id_pracownika = Column(Integer, primary_key=True, index=True)
    login = Column(String(50), unique=True, nullable=False)
    haslo_hash = Column(String(255), nullable=False)
    imie = Column(String(50), nullable=False)
    nazwisko = Column(String(50), nullable=False)
    plec = Column(Text, nullable=True)
    id_roli = Column(Integer, ForeignKey("rola.id_roli"), nullable=False)

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

class Zamowienie(Base):
    __tablename__ = "zamowienie"
    id_zamowienia = Column(Integer, primary_key=True, index=True)
    numer_zamowienia = Column(String(50), unique=True, nullable=False)
    data_zlozenia = Column(DateTime, nullable=False)
    status_zamowienia = Column(String(20), nullable=False)
    suma_calkowita = Column(Float, nullable=False)
    
    telefon_kontakt_do_zam = Column(String(9), nullable=True)
    email_kontakt_do_zam = Column(String(40), nullable=True)

    id_klienta = Column(Integer, ForeignKey("klient.id_klienta"), nullable=False)
    id_adresu = Column(Integer, ForeignKey("adres.id_adresu"), nullable=False)

class PozycjaZamowienia(Base):
    __tablename__ = "pozycja_zamowienia"
    id_pozycji = Column(Integer, primary_key=True, index=True)
    ilosc = Column(Integer, nullable=False)
    cena_w_chwili_zakupu = Column(Float, nullable=False)
    
    id_modelu = Column(Integer, ForeignKey("model_produktu.id_modelu"), nullable=False)
    id_zamowienia = Column(Integer, ForeignKey("zamowienie.id_zamowienia"), nullable=False)

    model = relationship("ModelProduktu")

class LogZmianaStatusu(Base):
    __tablename__ = "log_zmiana_statusu"
    id_logu = Column(Integer, primary_key=True, index=True)
    stary_status = Column(Text)
    nowy_status = Column(Text)
    data_zmiany = Column(Date)
    id_zamowienia = Column(Integer, ForeignKey("zamowienie.id_zamowienia"), nullable=False)
    id_pracownika = Column(Integer, ForeignKey("pracownik.id_pracownika"), nullable=False)