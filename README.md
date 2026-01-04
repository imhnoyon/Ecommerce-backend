🛒 Modern E-commerce REST API Backend
A robust, scalable, and secure E-commerce Backend built with Django REST Framework (DRF). This project implements advanced features like JWT authentication, real-time inventory management with race-condition prevention, and multi-gateway payment integrations (bKash & Stripe).

🚀 Key Features
🔐 Security & Authentication
JWT Authentication: Implements stateless user authentication using SimpleJWT for secure login and signup flows.

Environment Protection: Sensitive credentials (API Keys, Database URI) are managed securely using django-environ.

🛠️ Advanced Order Engineering
Atomic Transactions: Ensures "All-or-Nothing" operations during order creation. If any part of the process fails, the database rolls back to maintain a clean state.

Dynamic Calculations: total_amount is calculated dynamically using custom model methods and database aggregation, ensuring 100% accuracy between orders and items.

📦 Inventory & Concurrency Control
Real-time Stock Management: Automatic stock reduction triggered instantly upon successful payment verification.

Race-Condition Prevention: Implements Database-level Locking (select_for_update) to prevent overselling, ensuring that stock levels remain accurate even under high concurrent traffic.

💳 Integrated Payment Ecosystem
bKash (Tokenized API): A full implementation including Token Granting, Payment Initiation, Execution, and Callback handling.

Stripe (Secure Checkout): Card processing with professional Webhook support to verify payment events independently of the client-side flow.

🏗️ Core Database Architecture
The system utilizes four specialized tables designed for relational efficiency:

User: Managed via Django's auth system with JWT integration.

Product: Manages inventory, pricing, and item details.

Order: Tracks purchase lifecycle, payment status, and final amounts.

OrderItem: Stores snapshots of product price and quantity at the time of purchase.

Payment: Logs transaction IDs, provider data, and raw responses for auditing.


🛠️ Tech Stack
Framework: Django 4.2+, Django REST Framework (DRF)

Database: PostgreSQL (Production), SQLite (Dev)

Auth: JSON Web Tokens (JWT)

Tools: Python-dotenv, Django-environ, Stripe-python

🧪 Testing bKash Sandbox
Test Wallet: 01770618575

OTP: 123456

PIN: 12121


📋 Installation & Setup
Clone the Repository:

Bash

git clone https://github.com/yourusername/ecommerce-backend.git
cd ecommerce-backend
Create Virtual Environment:

Bash

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install Dependencies:

Bash

pip install -r requirements.txt
Environment Setup: Create a .env file in the root directory:

env

SECRET_KEY=your_secret_key
DEBUG=True
BKASH_APP_KEY=your_bkash_key
BKASH_APP_SECRET=your_bkash_secret
STRIPE_SECRET_KEY=your_stripe_key

Database Migration:
Bash

python manage.py migrate
python manage.py createsuperuser
Run Server:

Bash

python manage.py runserver
