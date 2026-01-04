# 🚀 Robust E-commerce RESTful API

A high-performance, secure, and feature-rich E-commerce backend built with **Django REST Framework (DRF)**. This project is designed with a focus on data integrity, real-time inventory synchronization, and seamless multi-gateway payment integration.

---

## 💎 Key Highlights

### 🔐 Security & Authentication
* **JWT Authentication:** Implements stateless user authentication using **SimpleJWT** for secure login and signup flows.
* **Environment Protection:** Sensitive credentials (API Keys, Database URI) are managed securely using **django-environ**.

### 🛠️ Advanced Order Engineering
* **Atomic Transactions:** Ensures "All-or-Nothing" operations during order creation. If any part of the process fails, the database rolls back to maintain a clean state.
* **Dynamic Calculations:** `total_amount` is calculated dynamically using custom model methods and database aggregation, ensuring 100% accuracy between orders and items.

### 📦 Inventory & Concurrency Control
* **Real-time Stock Management:** Automatic stock reduction triggered instantly upon successful payment verification.
* **Race-Condition Prevention:** Implements **Database-level Locking** (`select_for_update`) to prevent overselling, ensuring that stock levels remain accurate even under high concurrent traffic.

### 💳 Integrated Payment Ecosystem
* **bKash (Tokenized API):** A full implementation including Token Granting, Payment Initiation, Execution, and Callback handling.
* **Stripe (Secure Checkout):** Card processing with professional **Webhook support** to verify payment events independently of the client-side flow.

---

## 🏗️ Core Database Architecture

The system utilizes four specialized tables designed for relational efficiency:

1. **User:** Managed via Django's auth system with JWT integration.
2. **Product:** Manages inventory, pricing, and item details.
3. **Order:** Tracks purchase lifecycle, payment status, and final amounts.
4. **OrderItem:** Stores snapshots of product price and quantity at the time of purchase.
5. **Payment:** Logs transaction IDs, provider data, and raw responses for auditing.



---

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
https://github.com/imhnoyon/Ecommerce-backend.git
cd your-repo-name
```

### 2. Environment Setup
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configuration (.env)
```Code snippet

DEBUG=True
SECRET_KEY=your_django_secret_key
STRIPE_SECRET_KEY=your_stripe_key
BKASH_APP_KEY=your_bkash_key
BKASH_APP_SECRET=your_bkash_secret
BKASH_USERNAME=your_username
BKASH_PASSWORD=your_password
```
### 4. Database Migration
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## 📡 API Endpoints Overview
| Method | Endpoint | Description | Auth |
|:--- |:--- |:--- |:--- |
| `POST` | `/api/auth/login/` | Obtain JWT Access/Refresh Tokens | No |
| `GET` | `/api/products/` | List all available products | No |
| `POST` | `/api/orders/` | Place a new order (Atomic Transaction) | Yes |
| `POST` | `/api/payment/bkash/initiate/` | Start bKash Payment flow | Yes |
| `POST` | `/api/payment/stripe/session/` | Create Stripe Checkout Session | Yes |
