import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# Stripe integration
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


def create_stripe_payment_intent(amount, currency="bdt", metadata=None):
    """Create a Stripe PaymentIntent."""
    intent = stripe.PaymentIntent.create(
        amount=int(amount * 100),  # Stripe expects amount in cents/paisa
        currency=currency,
        metadata=metadata or {},
    )
    return intent


def confirm_stripe_payment_intent(payment_intent_id, payment_method=None, return_url=None):
    """Confirm a Stripe PaymentIntent."""
    kwargs = {}
    if payment_method:
        kwargs['payment_method'] = payment_method
    if return_url:
        kwargs['return_url'] = return_url
    intent = stripe.PaymentIntent.confirm(payment_intent_id, **kwargs)
    return intent


def create_stripe_checkout_session(order, success_url, cancel_url):
    """Create a Stripe Checkout Session for an order."""
    line_items = []
    for item in order.items.all():
        line_items.append({
            'price_data': {
                'currency': 'bdt',
                'product_data': {
                    'name': item.product.name,
                },
                'unit_amount': int(item.price * 100),
            },
            'quantity': item.quantity,
        })

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        metadata={"order_id": order.id, "user_id": order.user.id},
        success_url=success_url,
        cancel_url=cancel_url,
    )
    return session





# bKash integration
def get_bkash_token():
    """Get bKash access token."""
    url = f"{settings.BKASH_BASE_URL}/tokenized/checkout/token/grant"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'username': settings.BKASH_USERNAME,
        'password': settings.BKASH_PASSWORD,
    }
    data = {
        'app_key': settings.BKASH_APP_KEY,
        'app_secret': settings.BKASH_APP_SECRET,
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"bKash token error: {response.text}")
        return None


def create_bkash_payment(amount, order_id, payer_reference):
    """Create bKash payment."""
    token_data = get_bkash_token()
    if not token_data:
        print("DEBUG: Token generation failed!")
        return None

    url = f"{settings.BKASH_BASE_URL}/tokenized/checkout/create"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': token_data['id_token'],
        'X-APP-key': settings.BKASH_APP_KEY,
    }
    data = {
        'amount': str(amount),
        'currency': 'BDT',
        'intent': 'sale',
        'merchantInvoiceNumber': str(order_id),
        'payerReference': payer_reference,
        'callbackURL': 'http://127.0.0.1:8000/api/payment/bkash/callback/', 
        'mode': '0011'
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"bKash create payment error: {response.text}")
        return None

def execute_bkash_payment(payment_id):
    """Execute bKash payment - v1.2.0-beta version."""
    token_data = get_bkash_token()
    if not token_data:
        logger.error("bKash execute failed: Could not get token")
        return None

    # ১. URL অবশ্যই /tokenized/checkout/execute হতে হবে
    url = f"{settings.BKASH_BASE_URL}/tokenized/checkout/execute"
    
    # ২. হেডার কী-গুলো স্ট্যান্ডার্ড ফরম্যাটে লিখুন (Authorization, X-APP-Key)
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': token_data['id_token'], # 'A' বড় হাতের
        'X-APP-Key': settings.BKASH_APP_KEY,     # 'K' বড় হাতের
    }
    
    # ৩. পেমেন্ট আইডি বডিতে পাঠাতে হবে
    payload = {
        "paymentID": payment_id
    }
    
    try:
        # ৪. json=payload ব্যবহার করুন
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Execute API Debug: {response.json()}") # চেক করার জন্য প্রিন্ট
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"bKash execute payment error: {response.text}")
            return None
    except Exception as e:
        logger.error(f"bKash execute connection error: {e}")
        return None

def query_bkash_payment(payment_id):
    """Query bKash payment status."""
    token_data = get_bkash_token()
    if not token_data:
        return None

    url = f"{settings.BKASH_BASE_URL}/checkout/payment/query/{payment_id}"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'authorization': token_data['id_token'],
        'x-app-key': settings.BKASH_APP_KEY,
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"bKash query payment error: {response.text}")
        return None










