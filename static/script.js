document.addEventListener('DOMContentLoaded', () => {
    // --- ZMIENNE ---
    const cartCountElement = document.querySelector('.cart-count');
    const backToTopBtn = document.getElementById('back-to-top');
    const modal = document.getElementById('product-modal');
    const openBtn = document.getElementById('open-product-modal');
    const closeBtn = document.querySelector('.close-modal');
    const togglePassword = document.querySelector('#togglePassword');
    const passwordInput = document.querySelector('#password');

    // --- 1. ZARZĄDZANIE KOSZYKIEM (LOCAL STORAGE) ---
    
    function getCart() {
        return JSON.parse(localStorage.getItem('myShopCart')) || [];
    }

    function saveCart(cart) {
        localStorage.setItem('myShopCart', JSON.stringify(cart));
        updateBadge();
    }

    function updateBadge() {
        const cart = getCart();
        const totalQty = cart.reduce((sum, item) => sum + item.qty, 0);
        if (cartCountElement) cartCountElement.innerText = totalQty;
    }

    // Funkcja dodawania do koszyka ze sprawdzaniem stanu magazynowego
    function addToCart(id, qty = 1, maxStock = 9999) {
        let cart = getCart();
        const existingItem = cart.find(item => item.id === id);
        
        let currentQty = existingItem ? existingItem.qty : 0;
        
        // Sprawdzamy dostępność (czy nowa ilość nie przekroczy stanu)
        if (currentQty + qty > maxStock) {
            window.showToast(`Mamy tylko ${maxStock} szt. tego produktu! Masz już ${currentQty} w koszyku.`);
            return;
        }

        if (existingItem) {
            existingItem.qty += qty;
        } else {
            cart.push({ id: id, qty: qty });
        }
        
        saveCart(cart);
        updateBadge();
        window.showToast("Dodano produkt do koszyka!");
    }

    // --- 2. OBSŁUGA PRZYCISKÓW NA STRONIE GŁÓWNEJ (LISTA PRODUKTÓW) ---
    document.querySelectorAll('.cart-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault(); 
            const card = btn.closest('.product-card');
            const link = card.querySelector('.card-link').getAttribute('href'); 
            const id = parseInt(link.split('=')[1]);
            const stock = parseInt(btn.getAttribute('data-stock')) || 9999; 

            addToCart(id, 1, stock);
        });
    });

    // --- OBSŁUGA PRZYCISKU "DODAJ DO KOSZYKA" NA STRONIE SZCZEGÓŁÓW ---
    const btnAddBig = document.querySelector('.add-to-cart-big');
    if (btnAddBig) {
        btnAddBig.addEventListener('click', () => {
            const urlParams = new URLSearchParams(window.location.search);
            const id = parseInt(urlParams.get('id'));
            
            // Pobieramy ilość wpisaną w input
            const qtyInput = document.querySelector('.purchase-section .qty-input');
            const qty = parseInt(qtyInput.value) || 1;
            
            const stock = parseInt(btnAddBig.getAttribute('data-stock')) || 9999;
            
            addToCart(id, qty, stock);
        });
    }
    // --- OBSŁUGA OKA (WIDOCZNOŚĆ HASŁA) ---
if (togglePassword && passwordInput) {
    togglePassword.addEventListener('click', function() {
        // Przełączanie typu pola (password <-> text)
        const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
        passwordInput.setAttribute('type', type);
        
        // Przełączanie ikony (FontAwesome)
        this.classList.toggle('fa-eye');
        this.classList.toggle('fa-eye-slash');
    });
}
    // --- 3. LOGIKA STRONY KOSZYKA (Tabela) ---
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

        const ids = cart.map(item => item.id);
        
        try {
            const response = await fetch('/api/products-details', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(ids)
            });
            const products = await response.json();

            cartTableBody.innerHTML = '';
            let totalSum = 0;

            cart.forEach(cartItem => {
                const product = products.find(p => p.id === cartItem.id);
                if (!product) return; 

                const subtotal = product.price * cartItem.qty;
                totalSum += subtotal;

                const isMaxed = cartItem.qty >= product.stock;
                const plusDisabled = isMaxed ? 'disabled style="opacity: 0.5; cursor: not-allowed;"' : '';

                const row = `
                    <tr data-id="${cartItem.id}" data-stock="${product.stock}">
                        <td class="product-img">
                            <img src="${product.image || 'https://placehold.co/80x60'}" width="80">
                        </td>
                        <td class="product-name">
                            <a href="szczegoly.html?id=${product.id}">${product.name}</a>
                            ${isMaxed ? '<div style="color: red; font-size: 11px;">Max dostępna ilość</div>' : ''}
                        </td>
                        <td class="product-price">${product.price} zł</td>
                        <td class="product-qty">
                            <div class="qty-control">
                                <button class="qty-minus">-</button>
                                <input type="number" class="qty-input" value="${cartItem.qty}" readonly>
                                <button class="qty-plus" ${plusDisabled}>+</button>
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

            attachCartEvents();

        } catch (error) {
            console.error("Błąd pobierania koszyka:", error);
        }
    }

    function attachCartEvents() {
        // Obsługa guzików wewnątrz tabeli koszyka
        document.querySelectorAll('.cart-table .qty-minus').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const row = e.target.closest('tr');
                const id = parseInt(row.dataset.id);
                let cart = getCart();
                const item = cart.find(i => i.id === id);
                if (item && item.qty > 1) {
                    item.qty--;
                    saveCart(cart);
                    renderCartPage(); 
                }
            });
        });

        document.querySelectorAll('.cart-table .qty-plus').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const row = e.target.closest('tr');
                const id = parseInt(row.dataset.id);
                const stock = parseInt(row.dataset.stock); 
                
                let cart = getCart();
                const item = cart.find(i => i.id === id);
                
                if (item) {
                    if (item.qty < stock) {
                        item.qty++;
                        saveCart(cart);
                        renderCartPage();
                    } else {
                        window.showToast("Osiągnięto limit magazynowy!");
                    }
                }
            });
        });

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
            window.location.href = "/podsumowanie";
        });
    }

    // --- 5. INITIALIZACJA ---
    updateBadge(); 

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
    
    // --- 7. FILTRY, SZUKANIE I SORTOWANIE ---
    const applyFiltersBtn = document.getElementById('apply-filters');
    const resetFiltersBtn = document.getElementById('reset-filters');
    const sortSelect = document.getElementById('sort-select');
    const searchInput = document.querySelector('.search-bar input');
    const searchBtn = document.querySelector('.search-bar .search-btn');

    if (sortSelect) {
        const params = new URLSearchParams(window.location.search);
        const currentSort = params.get('sort');
        if (currentSort) {
            sortSelect.value = currentSort;
        }
    }

    function applyAllFilters() {
        const urlParams = new URLSearchParams(window.location.search);
        
        const min = document.getElementById('price-min').value;
        const max = document.getElementById('price-max').value;

        if (min) urlParams.set('price_min', min);
        else urlParams.delete('price_min');

        if (max) urlParams.set('price_max', max);
        else urlParams.delete('price_max');

        if (sortSelect) {
            const sortVal = sortSelect.value;
            if (sortVal !== "0") urlParams.set('sort', sortVal);
            else urlParams.delete('sort');
        }

        if (searchInput && searchInput.value.trim() !== "") {
            urlParams.set('search', searchInput.value.trim());
        }

        window.location.search = urlParams.toString();
    }

    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', (e) => {
            e.preventDefault();
            applyAllFilters();
        });
    }

    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.delete('price_min');
            urlParams.delete('price_max');
            urlParams.delete('sort');
            window.location.search = urlParams.toString();
        });
    }

    function performSearch() {
        const query = searchInput.value.trim();
        const urlParams = new URLSearchParams(window.location.search);
        
        if (query) {
            urlParams.set('search', query);
        } else {
            urlParams.delete('search');
        }
        
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

    // --- 10. OBSŁUGA ILOŚCI NA STRONIE SZCZEGÓŁÓW (NOWOŚĆ) ---
    // Ten kod działa TYLKO na stronie szczegoly.html, gdzie jest .purchase-section
    const detailQtyControl = document.querySelector('.purchase-section .qty-control');
    if (detailQtyControl) {
        const input = detailQtyControl.querySelector('.qty-input');
        const btnMinus = detailQtyControl.querySelector('.qty-minus');
        const btnPlus = detailQtyControl.querySelector('.qty-plus');
        
        // Pobieramy maksymalny stan z atrybutu max inputa (został tam wstawiony przez Jinja2)
        // lub z przycisku dodawania (jeśli input nie ma max)
        const maxStock = parseInt(input.getAttribute('max')) || 9999;

        btnMinus.addEventListener('click', () => {
            let val = parseInt(input.value);
            if (val > 1) {
                input.value = val - 1;
            }
        });

        btnPlus.addEventListener('click', () => {
            let val = parseInt(input.value);
            if (val < maxStock) {
                input.value = val + 1;
            } else {
                window.showToast("Maksymalna dostępna ilość!");
            }
        });
    }
    // Ozywienie okna w panelu administratora

if (openBtn) {
    openBtn.addEventListener('click', () => {
        modal.classList.add('active'); 
    });
}


if (closeBtn) {
    closeBtn.addEventListener('click', () => {
        modal.classList.remove('active');
    });
}


window.addEventListener('click', (e) => {
    if (e.target === modal) {
        modal.classList.remove('active');
    }
});
});