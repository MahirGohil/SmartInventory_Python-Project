/**
 * catalog.js — Smart Inventory catalog page interactivity
 *
 * DEPENDENCY NOTE:
 *   The fetchJSON() calls below POST to cart app endpoints:
 *     /cart/add/     → cart:add   (must match cart/urls.py when cart app is built)
 *     /cart/update/  → cart:update
 *     /cart/remove/  → cart:remove
 *   CSRF protection is handled via the shared fetchJSON() wrapper from js/csrf.js.
 */

document.addEventListener("DOMContentLoaded", function () {

    // ── Cart bar helper ───────────────────────────────────────────────────────
    function updateCartBar(totalItems) {
        const cartBar = document.getElementById("cart-bar");
        if (!cartBar) return;
        if (totalItems > 0) {
            cartBar.style.display = "block";
            cartBar.textContent = `🛒 View Your Cart (${totalItems} item${totalItems !== 1 ? "s" : ""})`;
        } else {
            cartBar.style.display = "none";
        }
    }

    let cartTotalItems = 0;

    // ── Build stepper HTML ────────────────────────────────────────────────────
    function buildStepper(productId, quantity) {
        return `
            <div class="qty-stepper">
                <button class="qty-minus" data-product-id="${productId}" aria-label="Decrease quantity">−</button>
                <span class="qty-display" id="qty-${productId}">${quantity}</span>
                <button class="qty-plus" data-product-id="${productId}" aria-label="Increase quantity">+</button>
            </div>`;
    }

    function buildAddButton(productId) {
        return `<button class="add-btn" data-product-id="${productId}">Add</button>`;
    }

    // ── Event delegation ──────────────────────────────────────────────────────
    function attachGridListeners(grid) {
        if (!grid) return;

        grid.addEventListener("click", function (e) {
            const target = e.target;

            // ── ADD BUTTON ──
            if (target.classList.contains("add-btn")) {
                const productId = parseInt(target.dataset.productId, 10);
                const card = target.closest(".product-card");

                target.disabled = true;
                target.textContent = "Adding…";

                fetchJSON("/cart/add/", { method: "POST", body: { product_id: productId, quantity: 1 } })
                    .then(data => {
                        if (data.success) {
                            const cardBody = card.querySelector(".card-body");
                            const btn = cardBody.querySelector(".add-btn");
                            btn.outerHTML = buildStepper(productId, data.quantity ?? 1);
                            cartTotalItems = data.cart_total_items ?? (cartTotalItems + 1);
                            updateCartBar(cartTotalItems);
                        } else {
                            target.disabled = false;
                            target.textContent = "Add";
                            alert(data.error ?? "Could not add item.");
                        }
                    })
                    .catch(err => {
                        console.error("cart:add error", err);
                        target.disabled = false;
                        target.textContent = "Add";
                    });
            }

            // ── PLUS BUTTON ──
            if (target.classList.contains("qty-plus")) {
                const productId = parseInt(target.dataset.productId, 10);
                const qtyDisplay = document.getElementById(`qty-${productId}`);
                const currentQty = parseInt(qtyDisplay.textContent, 10);
                const newQty = currentQty + 1;

                fetchJSON("/cart/update/", { method: "POST", body: { product_id: productId, quantity: newQty } })
                    .then(data => {
                        if (data.success) {
                            qtyDisplay.textContent = data.quantity ?? newQty;
                            cartTotalItems = data.cart_total_items ?? (cartTotalItems + 1);
                            updateCartBar(cartTotalItems);
                        } else {
                            alert(data.error ?? "Could not update quantity.");
                        }
                    })
                    .catch(err => console.error("cart:update (+) error", err));
            }

            // ── MINUS BUTTON ──
            if (target.classList.contains("qty-minus")) {
                const productId = parseInt(target.dataset.productId, 10);
                const card = target.closest(".product-card");
                const qtyDisplay = document.getElementById(`qty-${productId}`);
                const currentQty = parseInt(qtyDisplay.textContent, 10);
                const newQty = currentQty - 1;

                if (newQty === 0) {
                    fetchJSON("/cart/remove/", { method: "POST", body: { product_id: productId } })
                        .then(data => {
                            if (data.success) {
                                const stepper = card.querySelector(".qty-stepper");
                                stepper.outerHTML = buildAddButton(productId);
                                cartTotalItems = data.cart_total_items ?? Math.max(0, cartTotalItems - 1);
                                updateCartBar(cartTotalItems);
                            } else {
                                alert(data.error ?? "Could not remove item.");
                            }
                        })
                        .catch(err => console.error("cart:remove error", err));
                } else {
                    fetchJSON("/cart/update/", { method: "POST", body: { product_id: productId, quantity: newQty } })
                        .then(data => {
                            if (data.success) {
                                qtyDisplay.textContent = data.quantity ?? newQty;
                                cartTotalItems = data.cart_total_items ?? Math.max(0, cartTotalItems - 1);
                                updateCartBar(cartTotalItems);
                            } else {
                                alert(data.error ?? "Could not update quantity.");
                            }
                        })
                        .catch(err => console.error("cart:update (-) error", err));
                }
            }
        });
    }

    attachGridListeners(document.getElementById("product-grid"));
    attachGridListeners(document.getElementById("previously-bought-grid"));

    // ── Search bar — 400ms debounce ───────────────────────────────────────────
    const searchInput = document.getElementById("search-input");
    if (searchInput) {
        let debounceTimer = null;
        searchInput.addEventListener("input", function () {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                searchInput.closest("form").submit();
            }, 400);
        });
    }
});
