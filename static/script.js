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

    // --- 4. SKŁADANIE ZAMÓWIENIA ---
    const checkoutBtn = document.querySelector('.checkout-btn');
    if (checkoutBtn) {
        checkoutBtn.addEventListener('click', async () => {
            const cart = getCart();
            if (cart.length === 0) return;

            try {
                const response = await fetch('/order/create', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(cart)
                });

                if (response.ok) {
                    const data = await response.json();
                    localStorage.removeItem('myShopCart'); // Wyczyść koszyk
                    updateBadge();
                    window.location.href = "/konto.html"; // Przekieruj do zamówień
                } else {
                    if (response.status === 401) {
                        alert("Musisz się zalogować, aby złożyć zamówienie!");
                        window.location.href = "/login.html";
                    } else {
                        alert("Wystąpił błąd podczas składania zamówienia.");
                    }
                }
            } catch (error) {
                console.error(error);
            }
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
    
    // --- 7. FILTRY (PRZYCISK) ---
    const applyFiltersBtn = document.getElementById('apply-filters');
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', () => {
            const min = document.getElementById('price-min').value;
            const max = document.getElementById('price-max').value;
            
            // Pobieramy obecne parametry URL (żeby nie zgubić kategorii)
            const urlParams = new URLSearchParams(window.location.search);
            
            if (min) urlParams.set('price_min', min);
            else urlParams.delete('price_min');
            
            if (max) urlParams.set('price_max', max);
            else urlParams.delete('price_max');
            
            window.location.search = urlParams.toString();
        });
    }
// ... reszta Twojego kodu ...

    // --- 8. WYSZUKIWANIE PRODUKTÓW ---
    const searchInput = document.querySelector('.search-bar input');
    const searchBtn = document.querySelector('.search-bar .search-btn');

    function performSearch() {
        const query = searchInput.value.trim();
        const urlParams = new URLSearchParams(window.location.search);

        if (query) {
            // Ustaw parametr ?search=...
            urlParams.set('search', query);
        } else {
            // Jeśli puste, usuń parametr search
            urlParams.delete('search');
        }

        // Przeładuj stronę z nowym adresem
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

// Tu kończy się Twój document.addEventListener
});