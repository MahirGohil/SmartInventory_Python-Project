# Smart Inventory — Django Web Application

A full-stack Django e-commerce and smart inventory management application built with vanilla JavaScript, HTML5, custom CSS, ReportLab PDF generation, and automated stock & sales forecasting.

---

## Features & App Structure

The project is structured into six decoupled Django applications:

1. **`accounts`**: Custom user registration, authentication, profile management, and 6-digit email OTP password recovery.
2. **`catalog`**: Product catalog browsing, category filtering, search, dynamic card state steppers, and "Previously Bought" product history.
3. **`cart`**: Session-persisted cart state, real-time totals, 10% first-order discount, ₹200 free delivery threshold, and session delivery ETA pinning.
4. **`orders`**: Checkout validation, COD & simulated UPI order placement, OrderItem snapshots, automated PDF bill generation (ReportLab), and order history.
5. **`adminpanel`**: Superuser-only product management (Add, Edit, Delete with modal confirmation), quick stats dashboard, and low-stock/expiry notification center.
6. **`predictions`**: Admin-only sales & stock forecasting using Weighted Moving Average (WMA) models with Chart.js visualizations and automated caching commands.

---

## Setup & Local Installation

### 1. Prerequisites
- Python 3.10+ installed on your system.

### 2. Virtual Environment Setup
```bash
# Clone or navigate to project directory
cd "SmartInventory_Python Project"

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup & Seeding
```bash
# Run database migrations
python manage.py migrate

# Seed demo catalog data & create default Admin user (Admin / Admin@123)
python manage.py seed_demo_data
```

### 5. Run Development Server
```bash
python manage.py runserver
```
Navigate to `http://127.0.0.1:8000/` in your browser.

---

## Environment Configuration

Copy `.env.example` to `.env` in the project root:

```bash
cp .env.example .env
```

### Required Variables Reference

| Variable | Description | Development Default |
|---|---|---|
| `SECRET_KEY` | Django secret key | `django-insecure-dev-key...` |
| `DEBUG` | Enable/disable debug mode | `True` |
| `ALLOWED_HOSTS` | Comma-separated allowed hostnames | `*` |
| `EMAIL_BACKEND` | Email backend for OTP delivery | `django.core.mail.backends.console.EmailBackend` |
| `EMAIL_HOST` | SMTP server host | `smtp.gmail.com` |
| `EMAIL_PORT` | SMTP port | `587` |
| `EMAIL_HOST_USER` | SMTP username | `""` |
| `EMAIL_HOST_PASSWORD` | SMTP password / API Key | `""` |
| `GOOGLE_PLACES_API_KEY` | Google Maps Places API key | `""` (Stubbed) |
| `UPI_MERCHANT_ID` | UPI Merchant VPA | `""` (Simulated) |
| `DELIVERY_CHARGE` | Standard delivery charge in INR | `40.00` |

---

## External Integrations Status

| Feature | Status | Notes |
|---|---|---|
| **OTP Email Delivery** | **Development** | Uses Django console backend by default (OTP printed to stdout). Switch `EMAIL_BACKEND` to SMTP for production. |
| **PDF Bill Generation** | **Fully Live** | Uses pure-Python `ReportLab` to render downloadable PDF invoices attached to `Bill` objects. |
| **Static File Serving** | **Fully Live** | Uses `WhiteNoise` with manifest compression (`DEBUG=False` compatible). |
| **Google Places Autocomplete** | **Stubbed** | Receiver address field is currently a plain text input. Code comment TODOs in `checkout.html` and `checkout.js` outline API key attachment steps. |
| **UPI Payment Gateway** | **Simulated** | Simulates instant payment success for checkout testing. Marked with clear comments in `orders/views.py` where real gateway SDK calls will be wired. |
