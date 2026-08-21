/**
 * adminpanel.js — Admin Panel Interactivity
 *
 * 1. Delete Product confirmation modal + AJAX POST to delete endpoint.
 * 2. Mark Notification as Read AJAX POST.
 */

// ── Globals ───────────────────────────────────────────────────────────────────
let _pendingDeleteId = null;

// ── Delete Product Modal ──────────────────────────────────────────────────────

function confirmDelete(productId, productName) {
    _pendingDeleteId = productId;
    const modal = document.getElementById("delete-modal");
    const msg = document.getElementById("delete-modal-message");
    if (msg) {
        msg.textContent = `Are you sure you want to Remove "${productName}"? This cannot be undone.`;
    }
    if (modal) {
        modal.style.display = "flex";
    }
}

function closeDeleteModal() {
    _pendingDeleteId = null;
    const modal = document.getElementById("delete-modal");
    if (modal) modal.style.display = "none";
}

document.addEventListener("DOMContentLoaded", function () {

    // Close modal on background overlay click
    const deleteModal = document.getElementById("delete-modal");
    if (deleteModal) {
        deleteModal.addEventListener("click", function (e) {
            if (e.target === deleteModal) closeDeleteModal();
        });
    }

    // Confirm delete button
    const confirmBtn = document.getElementById("modal-confirm-btn");
    if (confirmBtn) {
        confirmBtn.addEventListener("click", function () {
            if (!_pendingDeleteId) return;

            const productId = _pendingDeleteId;
            closeDeleteModal();

            fetchJSON(`/adminpanel/products/${productId}/delete/`, { method: "POST" })
                .then(data => {
                    if (data.success) {
                        const row = document.getElementById(`product-row-${productId}`);
                        if (row) {
                            row.style.transition = "opacity 0.3s";
                            row.style.opacity = "0";
                            setTimeout(() => row.remove(), 320);
                        }
                    } else {
                        alert(data.error || "Failed to delete product. Please try again.");
                    }
                })
                .catch(err => {
                    console.error("Delete error:", err);
                    alert("An error occurred while deleting. Please try again.");
                });
        });
    }

    // ── Mark Notification as Read ─────────────────────────────────────────────
    document.querySelectorAll(".btn-mark-read").forEach(btn => {
        btn.addEventListener("click", function () {
            const notifId = this.dataset.notifId;
            if (!notifId) return;

            fetchJSON(`/adminpanel/notifications/${notifId}/read/`, { method: "POST" })
                .then(data => {
                    if (data.success) {
                        const card = document.getElementById(`notif-${notifId}`);
                        if (card) {
                            card.classList.add("notif-read");
                            // Replace button with read label
                            const actionsDiv = card.querySelector(".notif-actions");
                            if (actionsDiv) {
                                actionsDiv.innerHTML = '<span class="read-label">✓ Read</span>';
                            }
                        }
                    } else {
                        alert("Could not mark notification as read.");
                    }
                })
                .catch(err => console.error("Mark-read error:", err));
        });
    });
});
