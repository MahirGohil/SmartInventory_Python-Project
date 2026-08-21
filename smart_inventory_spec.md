# Smart Inventory — Full Project Specification
**Tech Stack:** Django (Python) | SQLite/PostgreSQL | HTML/CSS/JS templates | Chart.js (or similar) for graphs

> This document merges and clarifies all requirement notes into one build-ready spec for an AI coding IDE (Antigravity). Ambiguities in the original notes have been resolved and called out in *Notes* boxes so the IDE/developer knows the intended behavior.

---

## 0. App Structure Recommendation (Django)

Suggested Django apps to keep the codebase modular:

| App | Responsibility |
|---|---|
| `accounts` | Login, Register, OTP, password reset, profile |
| `catalog` | Products, categories, product cards |
| `cart` | Cart, cart items, discount/delivery logic |
| `orders` | Checkout, order history, billing/PDF generation |
| `adminpanel` | Custom admin dashboard (Manage, Notifications, Predictions) |
| `predictions` | Sales prediction & stock prediction logic |

Suggested core models (minimum viable set):

- `User` (extend Django's `AbstractUser` with `mobile_number`, `joining_date`, `profile_picture`)
- `OTP` (`user`, `code`, `created_at`, `expires_at`, `is_used`)
- `Category`
- `Product` (`name`, `product_id`, `price`, `quantity`, `category`, `photo`, `expiry_date`)
- `Cart`, `CartItem`
- `Order`, `OrderItem` (`order`, `product`, `quantity`, `price_at_purchase`)
- `Bill` (linked 1:1 with `Order`, stores generated PDF/file path, timestamps)

---

## 1. Authentication Module

### 1.1 Landing Page
- First page shown when the site opens.
- Full-screen background image (`shopPhoto.png`).
- Two vertically stacked buttons:
  - **Login** (Blue) → goes to Login page.
  - **Sign Up** (Red) → goes to Registration page.

> **Note:** The original spec labeled the second button "Sign-In," but its fields and workflow describe account *creation*. It is treated here as **Registration/Sign Up** to avoid confusion with the actual Login flow. Rename consistently across templates as "Sign Up."

### 1.2 Registration (Sign Up) Page
**Fields:** Email ID, Mobile Number, Username, Password

**Validation:**
- Email must be a valid email format.
- Mobile number: exactly 10 digits, numeric only.
- Password: minimum 8 characters, at least one special character and at least one digit.
- Username must be unique (recommended addition — enforce at DB level).

**Workflow:**
- Validate all fields (client-side + server-side Django form validation).
- On success: create user record, redirect to the main shopping page (auto-login recommended).
- On failure: show inline field errors.

### 1.3 Login Page
**Fields:** Username, Password

**Workflow:**
- Validate credentials against the database (Django's `authenticate()`).
- On success: redirect to the main shopping page.
- On failure: show a generic invalid-credentials error (do not reveal whether username or password was wrong, for security).

- Blue **"Forgot Password?"** link displayed below the password field.

### 1.4 Forgot Password
**Fields:** Username, Email ID

**Workflow:**
- Validate that the username and email match an existing account.
- Generate a random 6-digit OTP.
- Email the OTP to the registered address.
- Store OTP with a 1-minute expiry tied to the user.

### 1.5 OTP Verification
- Six separate single-digit input boxes (auto-advance focus recommended).
- OTP length: 6 digits.
- Validity: 1 minute from generation.
- Visible countdown timer displayed on screen.

**Resend OTP:**
- Button shown below the OTP boxes.
- Generates a new 6-digit OTP.
- Emails the new OTP.
- Invalidates the previous OTP immediately.
- Resets the countdown timer to 1 minute.

**Outcomes:**
- Correct + not expired → proceed to Reset Password page.
- Expired → block submission, prompt user to resend/request a new OTP.
- Incorrect → show inline error, allow retry until expiry.

### 1.6 Reset Password
**Fields:** New Password, Confirm Password

**Validation:**
- Both fields must match exactly.
- Apply the same password strength rule as registration (min 8 chars, 1 special char, 1 digit).

**Workflow:**
- Update the stored (hashed) password.
- Invalidate the OTP.
- Redirect to the Login page.

---

## 2. Main Shopping Page

- **Yellow top strip** containing:
  - Search bar (center) — search products by name.
  - Profile icon (top-right, round).
- **Category tabs** below the top strip:
  - Default/active tab: **All** (shows every product).
  - Additional tabs: Grocery, Makeup, Snacks, Electronics, and any other categories added by the admin.
  - Clicking a tab filters the product grid to that category only.
- **Product grid:** cards displayed in rows of **exactly 3 per row** (responsive breakpoints should collapse gracefully on smaller screens, but desktop default is 3/row).
- Every product card has a hover effect (e.g., slight elevation/shadow or zoom).
- **Previously Bought** section: visible only to users with at least one past order; displays products they've bought before (pull from `OrderItem` history).

### 2.1 Product Card
**Displays:** product image, product name, product price, **Add** button.

**Add button behavior:**
- Click → adds 1 unit of the product to the cart.
- The **Add** button is replaced by a **quantity stepper**: `-  [qty]  +`.
- `+` increases quantity in the cart; `-` decreases it (removes the item and restores the Add button if quantity reaches 0).

---

## 3. Cart

- Supports multiple distinct products simultaneously.
- The moment the first product is added, a **green "View Your Cart" bar** appears fixed at the bottom of the page (persists while shopping).
- Quantities are adjustable at any time via `+`/`-` on the product cards or from within the cart page itself.

### 3.1 Cart Page
Opened by clicking the "View Your Cart" bar. Displays:
- All cart products with name, quantity, and price (line totals).
- Discount applied, if applicable (see §4.1).
- Delivery charge or "Free Delivery" label, per the rule in §4.1.
- **Final total** (after discount and delivery charge).
- **Estimated delivery time**: randomly generated, always **1–2 hours after the current order time** (e.g., ordered at 14:00 → delivery window 15:00–16:00). Generate this once per cart/checkout session and keep it consistent through checkout and the final bill.

### 3.2 Cart Actions
- **Discard** button (above Buy): empties the entire cart immediately.
- **Buy** button (green, below Discard):
  - On click, show confirmation dialog: *"Are you sure you want to buy?"* with **Yes** / **No** options.
  - **No** → dismiss dialog, stay on cart page.
  - **Yes** → proceed to Checkout page.

---

## 4. Discounts & Delivery Charges

### 4.1 Rules
- **First-order discount:** 10% off, applied automatically only on a user's very first *successful* order. Not available on any subsequent order. (Track via a boolean flag or by checking whether `Order.objects.filter(user=user, status='completed').exists()`.)
- **Free delivery threshold:** if cart subtotal ≥ ₹200, delivery is free.
- **Delivery charge:** if cart subtotal < ₹200, apply a delivery charge (define a fixed value, e.g., ₹40 — confirm exact amount with stakeholder; not specified in original notes).
- These rules are evaluated and displayed on the Cart page before checkout, and re-validated server-side at checkout to prevent tampering.

---

## 5. Checkout

Reached via Cart → Buy → Yes.

**Fields:**
- Name
- Address (see §5.1 — Google Maps-validated)
- User Mobile Number (auto-filled from profile, editable or locked — recommend read-only)
- Receiver Mobile Number
- Delivery Time (auto-filled, exactly matching the value shown on the Cart page)

**Payment Method:** radio buttons — **UPI** / **COD**

**Proceed button:**
- Green.
- Disabled until every required field is validly filled.

### 5.1 Address Field
- Only addresses recognized by Google Maps are accepted (integrate **Google Places Autocomplete API**).
- Show live address suggestions as the user types.
- Store the resolved place (formatted address + lat/lng) rather than raw free text.

### 5.2 Order Completion
- **COD selected:** show blue confirmation message: *"Thank you for Placing Order. Your Order will be delivered Shortly."*
- **UPI selected:**
  - Process payment via a UPI payment gateway integration (e.g., Razorpay/UPI intent — to be selected during implementation).
  - On success, show blue message: *"Thank you for Purchasing."*
  - Automatically generate and download the bill (PDF).

---

## 6. Billing

Triggered after a successful order (UPI: automatic; COD: bill still generated and stored, download may be manual from Order History).

**Bill contents:**
- Product list (name, quantity, price per line)
- Bill generation date
- Bill generation time
- Delivery charge (or "Free")
- Discount applied (if first order)
- Net amount (final total)

**Order History:**
- Every completed order's bill is stored under **Profile → Order History**.
- Users can view or re-download any past bill.

---

## 7. Profile

Accessed via the round profile icon (top-right).

**Displays:**
- Profile picture
- Mobile number
- Username
- Order history (list of past orders/bills)
- Joining date
- Red **Logout** button

---

## 8. Admin Module

### 8.1 Admin Login
- Username: `Admin`
- Password: `Admin@123`
- Credentials pre-seeded in the database (e.g., via a Django data migration or `manage.py` seed command). Hash the password properly even though it's a fixed seed value.

### 8.2 Admin Main Website
Admin sees the normal shopping site plus additional controls:
- **Top-left buttons:** Manage, Notification, Sales Prediction, Stock Prediction.
- **Top-center:** Search bar (shared with normal user view).
- **Top-right:** Profile icon.

### 8.3 Notifications
1. **Low Stock Warning** — triggers when a product's stock reaches 20 units; shows product name and details.
2. **Expiry Warning** — triggers when a product will expire within 7 days; shows expiry date, product name, and details.
3. **Product Expired** — shows name and details of any already-expired product.

> Implementation note: run this as a periodic check (e.g., Django management command + cron/Celery beat) rather than only on page load, so notifications stay current.

### 8.4 Manage Products
Lists every product with: Product Name, Product ID, Quantity, **Edit**, **Delete**.

- **Delete:** confirmation popup — *"Are you sure you want to Remove [Product Name]?"* — **Yes** removes only that product; **No** cancels.
- **Edit:** opens an edit form scoped to the selected product only.
  - Editable fields: Product Name, Product ID, Quantity, Category.
  - Green **Done** button saves changes and returns to the Manage page.
- **Add Product:** button at the bottom of the Manage page.
  - Opens an Add Product form: name, ID, price, quantity, category, expiry date, product photo, etc.
  - Green **Done** button saves the product to the database and makes it immediately visible to all users on the main shopping site.

---

## 9. Predictions

### 9.1 Sales Prediction
Navigation: clicking **Sales Prediction** opens the Sales Prediction page.

**Page contents:**
- Graph: total sales per month, for every month of the current year.
- Graph: total sales per week, for every week of the current month.
- Predicted sales for the **next week**, generated from historical order data (e.g., simple moving average, linear regression, or a lightweight time-series model such as Holt-Winters/Prophet — pick based on available data volume).

### 9.2 Stock Prediction
Navigation: clicking **Stock Prediction** opens the Stock Prediction page.

**Page contents:**
- A predicted list of products required for the next week.
- Per product: Product Name, Predicted Quantity Required.
- Purpose: forecast next week's stock needs from historical sales data, so purchasing avoids overstocking or stockouts.

---

## 10. Open Items to Confirm Before/During Build
These were not fully specified in the source notes and should be decided during implementation:
1. Exact flat delivery charge amount when subtotal < ₹200.
2. Choice of UPI payment gateway/SDK for integration.
3. Whether registration requires email verification before first login (currently not required by spec).
4. Exact forecasting method/library for Sales & Stock Prediction (depends on data volume once real usage data exists).
5. Responsive/mobile layout rules for the 3-cards-per-row grid on small screens.
