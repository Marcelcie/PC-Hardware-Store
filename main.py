from fastapi import FastAPI, Request, Depends, Form, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
from typing import Optional, List
from fastapi import HTTPException
import json
import uuid

import models
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(SessionMiddleware, secret_key="bardzo-tajny-klucz")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- POMOCNICY ---
def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    user_type = request.session.get("user_type") # Nowy klucz w sesji

    if not user_id:
        return None

    if user_type == "pracownik":
        return db.query(models.Pracownik).filter(models.Pracownik.id_pracownika == user_id).first()
    else:
        # Domyślnie szukamy klienta
        return db.query(models.Klient).filter(models.Klient.id_klienta == user_id).first()

# --- ENDPOINTY ---

@app.get("/")
@app.get("/index.html")
def read_root(
    request: Request, 
    category_id: Optional[int] = None,
    price_min: Optional[float] = None, 
    price_max: Optional[float] = None,
    search: Optional[str] = None, 
    sort: Optional[str] = None,
    db: Session = Depends(get_db)
):
    categories = db.query(models.Kategoria).all()
    query = db.query(models.ModelProduktu)

    if category_id:
        query = query.filter(models.ModelProduktu.id_kategorii == category_id)
    if price_min is not None:
        query = query.filter(models.ModelProduktu.cena_katalogowa >= price_min)
    if price_max is not None:
        query = query.filter(models.ModelProduktu.cena_katalogowa <= price_max)
    if search:
        query = query.filter(models.ModelProduktu.nazwa_modelu.ilike(f"%{search}%"))

    if sort == '1':
        query = query.order_by(models.ModelProduktu.cena_katalogowa.asc())
    elif sort == '2':
        query = query.order_by(models.ModelProduktu.cena_katalogowa.desc())
    elif sort == '3':
        query = query.order_by(models.ModelProduktu.nazwa_modelu.asc())
    elif sort == '4':
        query = query.order_by(models.ModelProduktu.nazwa_modelu.desc())
    else:
        query = query.order_by(models.ModelProduktu.id_modelu.desc())

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
        "search_query": search,
        "current_sort": sort
    })


@app.post("/api/products-details")
def get_products_details_api(ids: List[int] = Body(...), db: Session = Depends(get_db)):
    # Pobiera listę produktów na podstawie listy ID przesłanej z JS
    products = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu.in_(ids)).all()

    result = []
    for p in products:
        result.append({
            "id": p.id_modelu,
            "name": p.nazwa_modelu,
            "price": p.cena_katalogowa,
            "image": p.zdjecie_url,
            "stock": p.stan_magazynowy
        })
    return result

# --- NOWOŚĆ: Strona Podsumowania (Checkout) z autouzupełnianiem ---
@app.get("/podsumowanie")
def checkout_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login.html")
    
    klient_adres_entry = db.query(models.KlientAdres).filter(
        models.KlientAdres.klient2id_klienta == user.id_klienta,
        models.KlientAdres.czy_domyslny == True
    ).first()

    default_address = None
    if klient_adres_entry:
        default_address = db.query(models.Adres).filter(
            models.Adres.id_adresu == klient_adres_entry.adres2id_adresu
        ).first()

    return templates.TemplateResponse("podsumowanie.html", {
        "request": request, 
        "adres": default_address
    })

# --- NOWOŚĆ: Usuwanie adresu domyślnego (Dezaktywacja flagi) ---
@app.post("/address/remove-default")
def remove_default_address(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return JSONResponse(status_code=401, content={"message": "Zaloguj się"})
    
    defaults = db.query(models.KlientAdres).filter(
        models.KlientAdres.klient2id_klienta == user.id_klienta,
        models.KlientAdres.czy_domyslny == True
    ).all()
    
    for d in defaults:
        d.czy_domyslny = False
    
    db.commit()
    return RedirectResponse(url="/podsumowanie", status_code=303)

# --- NOWOŚĆ: Składanie zamówienia z formularza HTML ---
# Wklej to do main.py (upewnij się, że masz importy: uuid, datetime, json)

@app.post("/order/submit")
def submit_order(
        request: Request,
        ulica: str = Form(...),
        nr_domu: str = Form(...),
        nr_lokalu: str = Form(None),
        kod_pocztowy: str = Form(...),
        miejscowosc: str = Form(...),
        cart_json: str = Form(...),
        db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login.html", status_code=303)

    # Zabezpieczenie: Pracownicy nie mogą zamawiać
    if hasattr(user, "id_roli"):
        return "Jesteś zalogowany jako Pracownik. Zaloguj się jako Klient."

    try:
        cart_items = json.loads(cart_json)
        if not cart_items:
            return "Twój koszyk jest pusty."

        # 1. Adres
        new_adres = models.Adres(
            ulica=ulica, nr_domu=nr_domu, nr_lokalu=nr_lokalu,
            kod_pocztowy=kod_pocztowy, miejscowosc=miejscowosc
        )
        db.add(new_adres)
        db.commit()
        db.refresh(new_adres)

        # 2. Obliczanie sumy
        suma_calkowita = 0.0
        order_items_data = []

        for item in cart_items:
            pid = int(item['id'])
            qty = int(item['qty'])
            prod = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu == pid).first()
            if prod:
                suma_calkowita += prod.cena_katalogowa * qty
                order_items_data.append({"product": prod, "qty": qty, "price": prod.cena_katalogowa})

        # 3. Zamówienie
        numer_zam = f"ZAM-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        new_order = models.Zamowienie(
            numer_zamowienia=numer_zam,
            data_zlozenia=datetime.now(),
            status_zamowienia="Nowe",
            suma_calkowita=suma_calkowita,
            id_klienta=user.id_klienta,
            id_adresu=new_adres.id_adresu,
            email_kontakt_do_zam=user.adres_email
        )
        db.add(new_order)
        db.commit()
        db.refresh(new_order)

        # 4. Pozycje i stan magazynowy
        for data in order_items_data:
            prod = data["product"]
            qty = data["qty"]
            prod.stan_magazynowy -= qty  # Aktualizacja stanu

            pozycja = models.PozycjaZamowienia(
                ilosc=qty,
                cena_w_chwili_zakupu=data["price"],
                id_modelu=prod.id_modelu,
                id_zamowienia=new_order.id_zamowienia
            )
            db.add(pozycja)

        db.commit()

        # --- TU JEST KLUCZOWE PRZEKIEROWANIE ---
        # Kierujemy do endpointu, który wyświetla szczegóły zamówienia
        return RedirectResponse(
            url=f"/zamowienie/{new_order.id_zamowienia}?clear_cart=1",
            status_code=303
        )

    except Exception as e:
        db.rollback()
        print(f"Błąd zamówienia: {e}")
        return f"Wystąpił błąd: {str(e)}"


@app.get("/zamowienie/{order_id}")
def order_details(request: Request, order_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login.html")

    # Rozróżniamy logikę dla Klienta i Pracownika
    if hasattr(user, "id_roli"):
        # PRACOWNIK: Widzi każde zamówienie po jego ID
        order = db.query(models.Zamowienie).filter(
            models.Zamowienie.id_zamowienia == order_id
        ).first()
    else:
        # KLIENT: Widzi tylko SWOJE zamówienia
        order = db.query(models.Zamowienie).filter(
            models.Zamowienie.id_zamowienia == order_id,
            models.Zamowienie.id_klienta == user.id_klienta
        ).first()

    if not order:
        return "Nie znaleziono zamówienia lub brak dostępu."

    adres = db.query(models.Adres).filter(models.Adres.id_adresu == order.id_adresu).first()

    items = db.query(models.PozycjaZamowienia).filter(
        models.PozycjaZamowienia.id_zamowienia == order_id
    ).all()

    return templates.TemplateResponse("szczegoly_zamowienia.html", {
        "request": request,
        "order": order,
        "items": items,
        "adres": adres,
        "user": user
    })


# --- ZMIANA STATUSU ZAMÓWIENIA (DLA WSZYSTKICH PRACOWNIKÓW) ---
@app.post("/api/update-order-status")
def update_order_status(
        request: Request,
        order_id: int = Form(...),
        new_status: str = Form(...),
        db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    # Sprawdzamy czy to pracownik (id_roli istnieje)
    if not user or not hasattr(user, "id_roli"):
        return RedirectResponse(url="/login.html", status_code=303)

    order = db.query(models.Zamowienie).filter(models.Zamowienie.id_zamowienia == order_id).first()
    if order:
        # 1. Zapisz log zmiany (Audyt)
        log = models.LogZmianaStatusu(
            stary_status=order.status_zamowienia,
            nowy_status=new_status,
            data_zmiany=datetime.now(),
            id_zamowienia=order.id_zamowienia,
            id_pracownika=user.id_pracownika
        )
        db.add(log)

        # 2. Zmień status
        order.status_zamowienia = new_status
        db.commit()

    # Przekieruj z powrotem na odpowiedni panel
    referer = request.headers.get("referer")
    return RedirectResponse(url=referer or "/", status_code=303)


# --- ZMIANA CENY (TYLKO SPRZEDAWCA I ADMIN) ---
@app.post("/api/update-price")
def update_price(
        request: Request,
        product_id: int = Form(...),
        new_price: float = Form(...),
        db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    # Rola 1 (Admin) lub 2 (Sprzedawca)
    if not user or getattr(user, "id_roli", 0) not in [1, 2]:
        return JSONResponse(status_code=403, content="Brak uprawnień")

    product = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu == product_id).first()
    if product:
        product.cena_katalogowa = new_price
        db.commit()

    return RedirectResponse(url=request.headers.get("referer"), status_code=303)


# --- ZMIANA STANU MAGAZYNOWEGO (TYLKO MAGAZYNIER I ADMIN) ---
@app.post("/api/update-stock")
def update_stock(
        request: Request,
        product_id: int = Form(...),
        new_stock: int = Form(...),
        db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    # Rola 1 (Admin) lub 3 (Magazynier)
    if not user or getattr(user, "id_roli", 0) not in [1, 3]:
        return JSONResponse(status_code=403, content="Brak uprawnień")

    product = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu == product_id).first()
    if product:
        product.stan_magazynowy = new_stock
        db.commit()

    return RedirectResponse(url=request.headers.get("referer"), status_code=303)


# --- PEŁNA EDYCJA PRODUKTU (ADMIN) ---
@app.post("/admin/edit-product")
def edit_product_full(
        request: Request,
        product_id: int = Form(...),
        nazwa_modelu: str = Form(...),
        cena: float = Form(...),
        stan: int = Form(...),
        category_id: int = Form(...),
        zdjecie_url: str = Form(""),
        opis: str = Form(""),
        db: Session = Depends(get_db)
):
    # Tutaj zakładamy, że tylko admin ma dostęp do tego endpointu (można dodać check jak wyżej)
    product = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu == product_id).first()
    if product:
        product.nazwa_modelu = nazwa_modelu
        product.cena_katalogowa = cena
        product.stan_magazynowy = stan
        product.id_kategorii = category_id
        product.zdjecie_url = zdjecie_url
        product.opis = opis
        db.commit()

    return RedirectResponse(url="/admin.html", status_code=303)

@app.get("/login.html")
def login_page(request: Request): return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login_user(
        request: Request,
        identyfikator: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    # 1. Sprawdzamy KLIENTA
    klient = db.query(models.Klient).filter(models.Klient.adres_email == identyfikator).first()
    if klient and klient.haslo_hash == password:  # Pamiętaj o temacie hashowania później
        request.session["user_id"] = klient.id_klienta
        request.session["user_type"] = "klient"
        return RedirectResponse(url="/", status_code=303)

    # 2. Sprawdzamy PRACOWNIKA
    pracownik = db.query(models.Pracownik).filter(models.Pracownik.login == identyfikator).first()
    if pracownik and pracownik.haslo_hash == password:
        request.session["user_id"] = pracownik.id_pracownika
        request.session["user_type"] = "pracownik"

        # --- LOGIKA PRZEKIEROWAŃ WG ROLI ---
        if pracownik.id_roli == 1:
            return RedirectResponse(url="/admin.html", status_code=303)
        elif pracownik.id_roli == 2:
            return RedirectResponse(url="/sprzedawca.html", status_code=303)
        elif pracownik.id_roli == 3:
            return RedirectResponse(url="/magazynier.html", status_code=303)
        else:
            return "Nieznana rola pracownika"

    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": "Błędny email/login lub hasło"
    })

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
    if not user:
        return RedirectResponse(url="/login.html")

    # --- POPRAWKA: Przekierowanie pracowników ---
    # Sprawdzamy, czy użytkownik to pracownik (ma atrybut id_roli)
    if hasattr(user, "id_roli"):
        if user.id_roli == 1:
            return RedirectResponse(url="/admin.html")
        elif user.id_roli == 2:
            return RedirectResponse(url="/sprzedawca.html")
        elif user.id_roli == 3:
            return RedirectResponse(url="/magazynier.html")

    # --- LOGIKA DLA KLIENTA (bez zmian) ---
    # Jeśli to nie pracownik, zakładamy, że to Klient i pobieramy jego zamówienia
    orders = db.query(models.Zamowienie).filter(
        models.Zamowienie.id_klienta == user.id_klienta
    ).order_by(models.Zamowienie.data_zlozenia.desc()).all()

    return templates.TemplateResponse("konto.html", {
        "request": request,
        "user": user,
        "orders": orders
    })

@app.get("/koszyk.html")
def cart_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    return templates.TemplateResponse("koszyk.html", {"request": request, "user": user})

@app.get("/szczegoly.html")
def details_page(request: Request, id: int = None, db: Session = Depends(get_db)):
    product = None
    if id: product = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu == id).first()
    return templates.TemplateResponse("szczegoly.html", {"request": request, "product": product})

@app.get("/admin.html")
@app.get("/admin.html")
def admin_panel(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)

    # Zabezpieczenie: Tylko Admin (id_roli = 1)
    if not user or getattr(user, "id_roli", 0) != 1:
        return RedirectResponse(url="/login.html")

    products = db.query(models.ModelProduktu).all()
    categories = db.query(models.Kategoria).all()
    # NOWOŚĆ: Admin musi widzieć zamówienia
    orders = db.query(models.Zamowienie).order_by(models.Zamowienie.data_zlozenia.desc()).all()

    return templates.TemplateResponse("admin.html", {
        "request": request,
        "user": user,  # Przekazujemy obiekt użytkownika
        "products": products,
        "categories": categories,
        "orders": orders  # Przekazujemy zamówienia
    })


# --- PANEL SPRZEDAWCY ---
@app.get("/sprzedawca.html")
def sprzedawca_panel(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or getattr(user, "id_roli", None) != 2: return RedirectResponse(url="/login.html")

    orders = db.query(models.Zamowienie).order_by(models.Zamowienie.data_zlozenia.desc()).all()
    products = db.query(models.ModelProduktu).all()  # <--- DODANO

    return templates.TemplateResponse("sprzedawca.html", {
        "request": request, "user": user, "orders": orders, "products": products  # <--- PRZEKAŻ PRODUKTY
    })


@app.get("/magazynier.html")
def magazynier_panel_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user or getattr(user, "id_roli", None) != 3: return RedirectResponse(url="/login.html")

    orders = db.query(models.Zamowienie).order_by(models.Zamowienie.data_zlozenia.asc()).all()
    products = db.query(models.ModelProduktu).all()  # <--- DODANO

    return templates.TemplateResponse("magazynier.html", {
        "request": request, "user": user, "orders": orders, "products": products  # <--- PRZEKAŻ PRODUKTY
    })

@app.get("/magazyn.html")
def magazynier_panel(request: Request, db: Session = Depends(get_db)):
    orders = db.query(models.Zamowienie).order_by(models.Zamowienie.data_zlozenia.desc()).all()
    return templates.TemplateResponse("magazynier.html", {
        "request": request, 
        "orders": orders
    })

@app.delete("/admin/delete-product/{product_id}")
def delete_product_endpoint(product_id: int, db: Session = Depends(get_db)):
    product = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu == product_id).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="Produkt nie znaleziony")   
    try:
        db.delete(product)
        db.commit()
        return {"status": "success", "message": "Produkt usunięty"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Nie można usunąć produktu (może jest w zamówieniach?): {str(e)}")
    
@app.post("/admin/add-product")
def add_product_endpoint(
    request: Request,
    category_id: int = Form(...),
    db: Session = Depends(get_db)
):
    new_product = models.ModelProduktu(
        nazwa_modelu="Nowy Produkt (Edytuj mnie)",
        opis="Opis produktu...",
        cena_katalogowa=0.0,
        stan_magazynowy=0,
        id_kategorii=category_id,
        zdjecie_url="" 
    )
    
    db.add(new_product)
    db.commit()
    return RedirectResponse(url="/admin.html", status_code=303)