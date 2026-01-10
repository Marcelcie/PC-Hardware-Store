from fastapi import FastAPI, Request, Depends, Form, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
from typing import Optional, List

import models
from database import engine, get_db

# Tworzenie tabel
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key="bardzo-tajny-klucz")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- POMOCNICY ---
def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.query(models.Klient).filter(models.Klient.id_klienta == user_id).first()

# --- STRONA GŁÓWNA (Z FILTROWANIEM) ---
@app.get("/")
@app.get("/index.html")
def read_root(
    request: Request, 
    category_id: Optional[int] = None,
    price_min: Optional[float] = None, 
    price_max: Optional[float] = None,
    search: Optional[str] = None,  # <--- NOWY PARAMETR
    db: Session = Depends(get_db)
):
    categories = db.query(models.Kategoria).all()
    query = db.query(models.ModelProduktu)

    # 1. Filtr kategorii
    if category_id:
        query = query.filter(models.ModelProduktu.id_kategorii == category_id)
    
    # 2. Filtry ceny
    if price_min is not None:
        query = query.filter(models.ModelProduktu.cena_katalogowa >= price_min)
    if price_max is not None:
        query = query.filter(models.ModelProduktu.cena_katalogowa <= price_max)

    # 3. WYSZUKIWANIE (NOWOŚĆ)
    if search:
        # ilike = case insensitive search (np. %RTX% znajdzie "Karta RTX 4090")
        query = query.filter(models.ModelProduktu.nazwa_modelu.ilike(f"%{search}%"))

    products = query.all()
    user = get_current_user(request, db)
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "products": products,
        "categories": categories,
        "user": user,
        "current_category_id": category_id,
        "price_min": price_min,
        "price_max": price_max,
        "search_query": search # <--- Przekazujemy wpisany tekst z powrotem do HTML
    })

# --- API DLA KOSZYKA (JS pyta o produkty) ---
@app.post("/api/products-details")
async def get_products_details(ids: List[int] = Body(...), db: Session = Depends(get_db)):
    """Pobiera szczegóły produktów na podstawie listy ID z localStorage"""
    products = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu.in_(ids)).all()
    
    # Zwracamy czysty JSON dla JavaScriptu
    return [
        {
            "id": p.id_modelu,
            "name": p.nazwa_modelu,
            "price": p.cena_katalogowa,
            "image": p.zdjecie_url
        }
        for p in products
    ]

# --- SKŁADANIE ZAMÓWIENIA (Z JSON) ---
@app.post("/order/create")
async def create_order(
    request: Request, 
    cart_data: List[dict] = Body(...), # Oczekujemy listy: [{id: 1, qty: 2}, ...]
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse(content={"error": "not_logged_in"}, status_code=401)

    if not cart_data:
        return JSONResponse(content={"error": "Koszyk jest pusty"}, status_code=400)

    # 1. Oblicz sumę całkowitą (bezpiecznie po stronie serwera)
    total_price = 0.0
    order_items = []

    for item in cart_data:
        product_id = item.get('id')
        qty = item.get('qty')
        
        product = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu == product_id).first()
        if product:
            total_price += product.cena_katalogowa * qty
            order_items.append({
                "product": product,
                "qty": qty,
                "price": product.cena_katalogowa
            })

    # 2. Utwórz zamówienie w bazie
    new_order = models.Zamowienie(
        numer_zamowienia=f"ORD-{int(datetime.now().timestamp())}",
        data_zlozenia=datetime.now(),
        status_zamowienia="Nowe",
        suma_calkowita=total_price,
        id_klienta=user.id_klienta,
        id_adresu=1
        # id_adresu=1 # Zakładamy, że masz adres testowy w bazie (np. ID 1)
    )
    db.add(new_order)
    db.flush() # Generuje ID zamówienia

    # 3. Zapisz pozycje zamówienia
    for item in order_items:
        pos = models.PozycjaZamowienia(
            ilosc=item["qty"],
            cena_w_chwili_zakupu=item["price"],
            id_modelu=item["product"].id_modelu,
            id_zamowienia=new_order.id_zamowienia
        )
        db.add(pos)
        # Odejmij ze stanu magazynowego (opcjonalne, jeśli masz trigger w bazie)
        # item["product"].stan_magazynowy -= item["qty"]

    db.commit()
    return JSONResponse(content={"message": "Zamówienie złożone!", "order_id": new_order.id_zamowienia})


# --- POZOSTAŁE ROUTINGI (Bez zmian) ---
@app.get("/login.html")
def login_page(request: Request): return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login_user(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(models.Klient).filter(models.Klient.adres_email == email).first()
    if not user or user.haslo_hash != password:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Błędny email lub hasło"})
    request.session["user_id"] = user.id_klienta
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)

@app.get("/rejestracja.html")
def register_page(request: Request): return templates.TemplateResponse("rejestracja.html", {"request": request})

@app.post("/register")
def register_user(imie: str = Form(...), nazwisko: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(models.Klient).filter(models.Klient.adres_email == email).first(): return "Email zajęty"
    new_user = models.Klient(imie=imie, nazwisko=nazwisko, adres_email=email, haslo_hash=password, data_rejestracji=datetime.now())
    try: db.add(new_user); db.commit()
    except: db.rollback()
    return RedirectResponse(url="/login.html", status_code=303)

@app.get("/konto.html")
def account_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user: return RedirectResponse(url="/login.html")
    orders = db.query(models.Zamowienie).filter(models.Zamowienie.id_klienta == user.id_klienta).order_by(models.Zamowienie.data_zlozenia.desc()).all()
    return templates.TemplateResponse("konto.html", {"request": request, "user": user, "orders": orders})

@app.get("/koszyk.html")
def cart_page(request: Request, db: Session = Depends(get_db)):
    # Koszyk jest dostępny dla wszystkich, dane ładuje JavaScript z localStorage
    user = get_current_user(request, db)
    return templates.TemplateResponse("koszyk.html", {"request": request, "user": user})

@app.get("/szczegoly.html")
def details_page(request: Request, id: int = None, db: Session = Depends(get_db)):
    product = None
    if id: product = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu == id).first()
    return templates.TemplateResponse("szczegoly.html", {"request": request, "product": product})