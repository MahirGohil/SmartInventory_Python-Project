/**
 * cart.js — Smart Inventory Cart Page Interactivity
 *
 * Handles live quantity adjustments, Discard Cart, and the Buy confirmation modal.
 * Uses shared fetchJSON() wrapper from js/csrf.js for CSRF-protected calls.
 */

document.addEventListener("DOMContentLoaded", function () {

    // ── Discard Cart ──────────────────────────────────────────────────────────
    const discardBtn = document.getElementById("btn-discard-cart");
    if (discardBtn) {
        discardBtn.addEventListener("click", function () {
            if (confirm("Are you sure you want to discard your entire cart?")) {
                fetchJSON("/cart/discard/", { method: "POST" })
                    .then(data => {
                        if (data.success) {
                            window.location.reload();
                        } else {
                            alert(data.error || "Could not discard cart.");
                        }
                    })
                    .catch(err => console.error("Discard cart error:", err));
            }
        });
    }

    // ── Quantity Steppers on Cart Page ────────────────────────────────────────
    document.querySelectorAll(".cart-qty-plus").forEach(button => {
        button.addEventListener("click", function () {
            const productId = parseInt(this.dataset.productId, 10);
            const qtySpan = document.getElementById(`cart-qty-${productId}`);
            const currentQty = parseInt(qtySpan.textContent, 10);
            const newQty = currentQty + 1;

            fetchJSON("/cart/update/", { method: "POST", body: { product_id: productId, quantity: newQty } })
                .then(data => {
                    if (data.success) {
                        window.location.reload();
                    } else {
                        alert(data.error || "Could not update quantity.");
                    }
                })
                .catch(err => console.error("Cart update error:", err));
        });
    });

    document.querySelectorAll(".cart-qty-minus").forEach(button => {
        button.addEventListener("click", function () {
            const productId = parseInt(this.dataset.productId, 10);
            const qtySpan = document.getElementById(`cart-qty-${productId}`);
            const currentQty = parseInt(qtySpan.textContent, 10);
            const newQty = currentQty - 1;

            if (newQty <= 0) {
                fetchJSON("/cart/remove/", { method: "POST", body: { product_id: productId } })
                    .then(data => {
                        if (data.success) {
                            window.location.reload();
                        } else {
                            alert(data.error || "Could not remove item.");
                        }
                    })
                    .catch(err => console.error("Cart remove error:", err));
            } else {
                fetchJSON("/cart/update/", { method: "POST", body: { product_id: productId, quantity: newQty } })
                    .then(data => {
                        if (data.success) {
                            window.location.reload();
                        } else {
                            alert(data.error || "Could not update quantity.");
                        }
                    })
                    .catch(err => console.error("Cart update error:", err));
            }
        });
    });

    // ── Buy Button Confirmation Modal (spec §3.2) ──────────────────────────────
    const buyBtn = document.getElementById("btn-buy-now");
    const buyModal = document.getElementById("buy-confirm-modal");
    const modalYes = document.getElementById("modal-yes-btn");
    const modalNo = document.getElementById("modal-no-btn");

    if (buyBtn && buyModal) {
        buyBtn.addEventListener("click", function (e) {
            e.preventDefault();
            buyModal.style.display = "flex";
        });

        modalNo.addEventListener("click", function () {
            buyModal.style.display = "none";
        });

        modalYes.addEventListener("click", function () {
            buyModal.style.display = "none";
            // Navigate to buy confirmation endpoint which redirects to orders:checkout
            window.location.href = "/cart/buy/";
        });

        // Close modal on background overlay click
        buyModal.addEventListener("click", function (e) {
            if (e.target === buyModal) {
                buyModal.style.display = "none";
            }
        });
    }
});
