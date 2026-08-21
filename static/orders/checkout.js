/**
 * checkout.js — Checkout Form Client-Side Validation
 *
 * Enables the "Proceed to Pay" button only when all required fields are
 * non-empty and the receiver mobile number passes a basic 10-digit check.
 *
 * NOTE (Google Places Autocomplete):
 *   The #id_formatted_address field is currently a plain text input (TODO stub).
 *   When integrating the Google Places API later:
 *   1. Load the Places SDK script in checkout.html.
 *   2. Replace the plain input with a Places Autocomplete widget initialized here.
 *   3. Store the lat/lng from the place_changed callback into hidden fields:
 *      <input type="hidden" name="address_lat" id="id_address_lat">
 *      <input type="hidden" name="address_lng" id="id_address_lng">
 *   4. The validateForm() function below already handles the address as a required
 *      text field — no structural changes needed, just add the autocomplete binding.
 */

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("checkout-form");
    const proceedBtn = document.getElementById("btn-proceed");

    if (!form || !proceedBtn) return;

    const requiredFields = [
        "id_receiver_name",
        "id_formatted_address",
        "id_receiver_mobile",
    ];

    function validateForm() {
        // Check all text fields are non-empty
        const textFieldsFilled = requiredFields.every(fieldId => {
            const el = document.getElementById(fieldId);
            return el && el.value.trim().length > 0;
        });

        // Validate receiver mobile: exactly 10 digits
        const mobileEl = document.getElementById("id_receiver_mobile");
        const mobileValid = mobileEl && /^\d{10}$/.test(mobileEl.value.trim());

        // Receiver name minimum 2 chars
        const nameEl = document.getElementById("id_receiver_name");
        const nameValid = nameEl && nameEl.value.trim().length >= 2;

        // Address minimum 5 chars (prevents blank spacebar tricks)
        const addrEl = document.getElementById("id_formatted_address");
        const addrValid = addrEl && addrEl.value.trim().length >= 5;

        // At least one payment method selected
        const paymentSelected = document.querySelector('input[name="payment_method"]:checked') !== null;

        const isValid = textFieldsFilled && mobileValid && nameValid && addrValid && paymentSelected;

        proceedBtn.disabled = !isValid;
        proceedBtn.style.opacity = isValid ? "1" : "0.65";
        proceedBtn.style.cursor = isValid ? "pointer" : "not-allowed";
    }

    // Attach live validation listeners
    requiredFields.forEach(fieldId => {
        const el = document.getElementById(fieldId);
        if (el) {
            el.addEventListener("input", validateForm);
            el.addEventListener("change", validateForm);
        }
    });

    // Also watch payment method radio buttons
    document.querySelectorAll('input[name="payment_method"]').forEach(radio => {
        radio.addEventListener("change", validateForm);
    });

    // Run initial validation to set the correct button state on page load
    validateForm();
});
