from fastapi import FastAPI, Request, Depends, Form, Body
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware
from datetime import datetime
from typing import Optional, List
import json

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
    if not user_id:
        return None
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
async def get_products_details(ids: List[int] = Body(...), db: Session = Depends(get_db)):
    products = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu.in_(ids)).all()
    return [{"id": p.id_modelu, "name": p.nazwa_modelu, "price": p.cena_katalogowa, "image": p.zdjecie_url} for p in products]

# --- NOWOŚĆ: Strona Podsumowania (Checkout) z autouzupełnianiem ---
@app.get("/podsumowanie")
def checkout_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login.html")
    
    # Szukamy adresu domyślnego w tabeli łączącej klient_adres
    # 1. Znajdź wpis w klient_adres gdzie czy_domyslny = True dla tego klienta
    klient_adres_entry = db.query(models.KlientAdres).filter(
        models.KlientAdres.klient2id_klienta == user.id_klienta,
        models.KlientAdres.czy_domyslny == True
    ).first()

    default_address = None
    if klient_adres_entry:
        # 2. Jeśli znaleziono, pobierz właściwy obiekt adresu
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
    
    # Znajdź obecny domyślny i usuń flagę
    defaults = db.query(models.KlientAdres).filter(
        models.KlientAdres.klient2id_klienta == user.id_klienta,
        models.KlientAdres.czy_domyslny == True
    ).all()
    
    for d in defaults:
        d.czy_domyslny = False
    
    db.commit()
    # Przeładuj stronę
    return RedirectResponse(url="/podsumowanie", status_code=303)

# --- NOWOŚĆ: Składanie zamówienia z formularza HTML ---
@app.post("/order/submit")
async def submit_order(
    request: Request,
    ulica: str = Form(...),
    nr_domu: str = Form(...),
    nr_lokalu: str = Form(None),
    kod_pocztowy: str = Form(...),
    miejscowosc: str = Form(...),
    save_default: bool = Form(False), # Checkbox
    cart_json: str = Form(...),       # Koszyk jako JSON string z ukrytego pola
    db: Session = Depends(get_db)
):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login.html", status_code=303)

    try:
        cart_data = json.loads(cart_json)
    except:
        return "Błąd danych koszyka"

    if not cart_data:
        return "Koszyk pusty"

    # 1. Tworzymy nowy adres w bazie dla tego zamówienia (bezpieczeństwo historii)
    #    lub można szukać duplikatu, ale dla prostoty tworzymy nowy.
    new_address = models.Adres(
        ulica=ulica,
        nr_domu=nr_domu,
        nr_lokalu=nr_lokalu,
        kod_pocztowy=kod_pocztowy,
        miejscowosc=miejscowosc
    )
    db.add(new_address)
    db.flush() # Żeby dostać ID adresu

    # 2. Obsługa adresu domyślnego
    # Jeśli użytkownik chce zapisać jako domyślny, musimy powiązać ten adres z klientem
    if save_default:
        # Najpierw "odznaczamy" poprzedni domyślny adres
        existing_defaults = db.query(models.KlientAdres).filter(
            models.KlientAdres.klient2id_klienta == user.id_klienta,
            models.KlientAdres.czy_domyslny == True
        ).all()
        for ka in existing_defaults:
            ka.czy_domyslny = False
        
        # Tworzymy nowe powiązanie w klient_adres
        new_link = models.KlientAdres(
            klient2id_klienta=user.id_klienta,
            adres2id_adresu=new_address.id_adresu,
            czy_domyslny=True
        )
        db.add(new_link)
    
    # Możemy też dodać powiązanie bez "czy_domyslny", żeby klient miał historię adresów,
    # ale skupmy się na wymaganiu.

    # 3. Obliczamy sumę
    total_price = 0.0
    order_items_objs = []

    for item in cart_data:
        p_id = int(item['id'])
        qty = int(item['qty'])
        product = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu == p_id).first()
        if product:
            total_price += product.cena_katalogowa * qty
            order_items_objs.append({
                "product": product,
                "qty": qty,
                "price": product.cena_katalogowa
            })

    # 4. Tworzymy zamówienie
    new_order = models.Zamowienie(
        numer_zamowienia=f"ORD-{int(datetime.now().timestamp())}",
        data_zlozenia=datetime.now(),
        status_zamowienia="Nowe",
        suma_calkowita=total_price,
        id_klienta=user.id_klienta,
        id_adresu=new_address.id_adresu,
        email_kontakt_do_zam=user.adres_email
    )
    db.add(new_order)
    db.flush()

    # 5. Pozycje zamówienia
    for item in order_items_objs:
        pos = models.PozycjaZamowienia(
            ilosc=item["qty"],
            cena_w_chwili_zakupu=item["price"],
            id_modelu=item["product"].id_modelu,
            id_zamowienia=new_order.id_zamowienia
        )
        db.add(pos)
        # Opcjonalnie: zmniejsz stan magazynowy
        item["product"].stan_magazynowy -= item["qty"]

    db.commit()

    # Przekierowanie do szczegółów tego zamówienia + czyszczenie koszyka (frontend musi wyczyścić po redirectcie,
    # ale tutaj robimy proste przekierowanie. JS na stronie sukcesu może wyczyścić localStorage).
    # Prostszą metodą jest przekierowanie do strony z parametrem ?clear_cart=1
    return RedirectResponse(url=f"/zamowienie/{new_order.id_zamowienia}?clear_cart=1", status_code=303)


@app.get("/zamowienie/{order_id}")
def order_details(request: Request, order_id: int, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse(url="/login.html")
    
    order = db.query(models.Zamowienie).filter(
        models.Zamowienie.id_zamowienia == order_id,
        models.Zamowienie.id_klienta == user.id_klienta
    ).first()
    
    if not order:
        return "Nie znaleziono zamówienia."
    
    # Pobierz adres powiązany z zamówieniem
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

# --- POZOSTAŁE (Login, Register, itp) ---
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
    user = get_current_user(request, db)
    return templates.TemplateResponse("koszyk.html", {"request": request, "user": user})

@app.get("/szczegoly.html")
def details_page(request: Request, id: int = None, db: Session = Depends(get_db)):
    product = None
    if id: product = db.query(models.ModelProduktu).filter(models.ModelProduktu.id_modelu == id).first()
    return templates.TemplateResponse("szczegoly.html", {"request": request, "product": product})