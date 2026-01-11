document.addEventListener('DOMContentLoaded', () => {
    // --- ZMIENNE ---
    const cartCountElement = document.querySelector('.cart-count');
    const backToTopBtn = document.getElementById('back-to-top');
    
    // --- 1. ZARZĄDZANIE KOSZYKIEM (LOCAL STORAGE) ---
    
    // Pobierz koszyk z pamięci przeglądarki
    function getCart() {
        return JSON.parse(localStorage.getItem('myShopCart')) || [];
    }

    // Zapisz koszyk do pamięci
    function saveCart(cart) {
        localStorage.setItem('myShopCart', JSON.stringify(cart));
        updateBadge();
    }

    // Aktualizuj licznik w nagłówku
    function updateBadge() {
        const cart = getCart();
        const totalQty = cart.reduce((sum, item) => sum + item.qty, 0);
        if (cartCountElement) cartCountElement.innerText = totalQty;
    }

    // Dodaj produkt
    function addToCart(id, qty = 1) {
        let cart = getCart();
        const existingItem = cart.find(item => item.id === id);
        
        if (existingItem) {
            existingItem.qty += qty;
        } else {
            cart.push({ id: id, qty: qty });
        }
        
        saveCart(cart);
        updateBadge();
        window.showToast("Dodano produkt do koszyka!");
    }

    // --- 2. OBSŁUGA PRZYCISKÓW NA STRONIE (WSZYSTKICH) ---
    
    // Guziki "Dodaj do koszyka" na liście produktów (index.html)
    document.querySelectorAll('.cart-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault(); // Żeby nie wchodziło w link szczegółów
            // Szukamy ID w linku rodzica lub atrybucie
            const card = btn.closest('.product-card');
            const link = card.querySelector('.card-link').getAttribute('href'); // np. "szczegoly.html?id=5"
            const id = parseInt(link.split('=')[1]);
            
            addToCart(id, 1);
        });
    });

    // Guzik "Dodaj do koszyka" na stronie szczegółów (szczegoly.html)
    const btnAddBig = document.querySelector('.add-to-cart-big');
    if (btnAddBig) {
        btnAddBig.addEventListener('click', () => {
            const urlParams = new URLSearchParams(window.location.search);
            const id = parseInt(urlParams.get('id'));
            const qtyInput = document.querySelector('.qty-input');
            const qty = parseInt(qtyInput.value) || 1;
            
            addToCart(id, qty);
        });
    }

    // --- 3. LOGIKA STRONY KOSZYKA (koszyk.html) ---
    const cartTableBody = document.querySelector('.cart-table tbody');
    if (cartTableBody) {
        renderCartPage();
    }

    async function renderCartPage() {
        const cart = getCart();
        const emptyMsg = document.getElementById('empty-cart-msg');
        const cartContent = document.getElementById('cart-content');

        if (cart.length === 0) {
            if(cartContent) cartContent.style.display = 'none';
            if(emptyMsg) emptyMsg.style.display = 'block';
            return;
        }

        // Pobierz szczegóły produktów z backendu (Python)
        const ids = cart.map(item => item.id);
        
        try {
            const response = await fetch('/api/products-details', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(ids)
            });
            const products = await response.json();

            // Generuj HTML tabeli
            cartTableBody.innerHTML = '';
            let totalSum = 0;

            cart.forEach(cartItem => {
                const product = products.find(p => p.id === cartItem.id);
                if (!product) return; // Produkt mógł zostać usunięty z bazy

                const subtotal = product.price * cartItem.qty;
                totalSum += subtotal;

                const row = `
                    <tr data-id="${cartItem.id}">
                        <td class="product-img">
                            <img src="${product.image || 'https://placehold.co/80x60'}" width="80">
                        </td>
                        <td class="product-name">
                            <a href="szczegoly.html?id=${product.id}">${product.name}</a>
                        </td>
                        <td class="product-price">${product.price} zł</td>
                        <td class="product-qty">
                            <div class="qty-control">
                                <button class="qty-minus">-</button>
                                <input type="number" class="qty-input" value="${cartItem.qty}" readonly>
                                <button class="qty-plus">+</button>
                            </div>
                        </td>
                        <td class="product-subtotal">${subtotal.toFixed(2)} zł</td>
                        <td class="product-remove">
                            <button class="btn-remove"><i class="fa-solid fa-trash"></i></button>
                        </td>
                    </tr>
                `;
                cartTableBody.insertAdjacentHTML('beforeend', row);
            });

            document.querySelector('.summary-subtotal').innerText = totalSum.toFixed(2) + ' zł';
            document.querySelector('.summary-total span:last-child').innerText = totalSum.toFixed(2) + ' zł';

            // Obsługa guzików wewnątrz koszyka (+, -, usuń)
            attachCartEvents();

        } catch (error) {
            console.error("Błąd pobierania koszyka:", error);
        }
    }

    function attachCartEvents() {
        // Minus
        document.querySelectorAll('.qty-minus').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.closest('tr').dataset.id);
                let cart = getCart();
                const item = cart.find(i => i.id === id);
                if (item && item.qty > 1) {
                    item.qty--;
                    saveCart(cart);
                    renderCartPage(); // Odśwież widok
                }
            });
        });

        // Plus
        document.querySelectorAll('.qty-plus').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.closest('tr').dataset.id);
                let cart = getCart();
                const item = cart.find(i => i.id === id);
                if (item) {
                    item.qty++;
                    saveCart(cart);
                    renderCartPage();
                }
            });
        });

        // Usuń
        document.querySelectorAll('.btn-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.closest('tr').dataset.id);
                let cart = getCart();
                cart = cart.filter(i => i.id !== id);
                saveCart(cart);
                renderCartPage();
            });
        });
    }

    // --- 4. PRZEKIEROWANIE DO PODSUMOWANIA ---
    const checkoutBtn = document.querySelector('.checkout-btn');
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', () => {
            const cart = getCart();
            if (cart.length === 0) {
                alert("Twój koszyk jest pusty!");
                return;
            }
            // Zamiast wysyłać od razu POST, idziemy do formularza wyboru adresu
            window.location.href = "/podsumowanie";
        });
    }

    // --- 5. INITIALIZACJA ---
    updateBadge(); // Uruchom przy starcie każdej strony

    // --- 6. TOASTY ---
    window.showToast = function(msg) {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `<i class="fa-solid fa-circle-check"></i> <span>${msg}</span>`;
        container.appendChild(toast);
        setTimeout(() => { toast.remove(); }, 3000);
    };
    
    // --- 7. FILTRY, SZUKANIE I SORTOWANIE (ZINTEGROWANE) ---
    
    // Elementy DOM
    const applyFiltersBtn = document.getElementById('apply-filters');
    const resetFiltersBtn = document.getElementById('reset-filters');
    const sortSelect = document.getElementById('sort-select');
    const searchInput = document.querySelector('.search-bar input');
    const searchBtn = document.querySelector('.search-bar .search-btn');

    // A. USTAWIENIE STANU POCZĄTKOWEGO (Po przeładowaniu)
    // Jeśli w URL jest ?sort=2, ustawiamy select na 2, żeby użytkownik widział co wybrał
    if (sortSelect) {
        const params = new URLSearchParams(window.location.search);
        const currentSort = params.get('sort');
        if (currentSort) {
            sortSelect.value = currentSort;
        }
    }

    // B. FUNKCJA APLIKUJĄCA WSZYSTKIE FILTRY (Cena + Sortowanie + Szukanie + Kategoria)
    function applyAllFilters() {
        const urlParams = new URLSearchParams(window.location.search);
        
        // 1. Ceny
        const min = document.getElementById('price-min').value;
        const max = document.getElementById('price-max').value;

        if (min) urlParams.set('price_min', min);
        else urlParams.delete('price_min');

        if (max) urlParams.set('price_max', max);
        else urlParams.delete('price_max');

        // 2. Sortowanie
        if (sortSelect) {
            const sortVal = sortSelect.value;
            if (sortVal !== "0") urlParams.set('sort', sortVal);
            else urlParams.delete('sort');
        }

        // 3. Wyszukiwanie (jeśli jest wpisane w headerze)
        if (searchInput && searchInput.value.trim() !== "") {
            urlParams.set('search', searchInput.value.trim());
        }

        // (Kategoria jest już w urlParams, jeśli tam była, więc jej nie ruszamy)

        // Przeładowanie strony z nowymi parametrami
        window.location.search = urlParams.toString();
    }

    // C. OBSŁUGA GUZIKA "ZASTOSUJ"
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', (e) => {
            e.preventDefault();
            applyAllFilters();
        });
    }

    // D. OBSŁUGA GUZIKA "WYCZYŚĆ FILTRY" (Czerwony tekst)
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const urlParams = new URLSearchParams(window.location.search);
            
            // Usuwamy tylko filtry cenowe i sortowanie
            // Zostawiamy kategorię (żeby nie wyrzucało do "Wszystkie") i szukanie
            urlParams.delete('price_min');
            urlParams.delete('price_max');
            urlParams.delete('sort');
            
            // Jeśli chcesz czyścić też szukanie, odkomentuj linię poniżej:
            // urlParams.delete('search');

            window.location.search = urlParams.toString();
        });
    }

    // E. OBSŁUGA WYSZUKIWANIA (Enter lub Klik)
    function performSearch() {
        const query = searchInput.value.trim();
        const urlParams = new URLSearchParams(window.location.search);
        
        if (query) {
            urlParams.set('search', query);
        } else {
            urlParams.delete('search');
        }
        
        // Zazwyczaj przy nowym wyszukiwaniu resetuje się filtry ceny, 
        // ale w tym rozwiązaniu zostawiamy je, aby można było szukać w przedziale cenowym.
        
        window.location.search = urlParams.toString();
    }

    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }

    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                performSearch();
            }
        });
    }
});