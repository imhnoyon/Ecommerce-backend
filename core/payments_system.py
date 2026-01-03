import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def get_bkash_token():
    """Request a bKash token and return it or None on failure."""
    url = f"{settings.BKASH_BASE_URL}/tokenized/checkout/token/grant"

    headers = {
        "username": settings.BKASH_USERNAME,
        "password": settings.BKASH_PASSWORD,
        "Content-Type": "application/json",
    }

    payload = {
        "app_key": settings.BKASH_APP_KEY,
        "app_secret": settings.BKASH_APP_SECRET,
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # sandbox/production sometimes differ in naming
        token = data.get("id_token") or data.get("idToken") or data.get("token")
        return token
    except Exception as exc:
        logger.exception("Failed to get bKash token: %s", exc)
        return None


def create_bkash_payment(token, payload):
    url = f"{settings.BKASH_BASE_URL}/tokenized/checkout/create"
    headers = {
        "Authorization": token,
        "X-APP-Key": settings.BKASH_APP_KEY,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.exception("bKash create payment failed: %s", exc)
        return None


def execute_bkash_payment(token, payload):
    url = f"{settings.BKASH_BASE_URL}/tokenized/checkout/execute"
    headers = {
        "Authorization": token,
        "X-APP-Key": settings.BKASH_APP_KEY,
        "Content-Type": "application/json",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.exception("bKash execute payment failed: %s", exc)
        return None


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


def retrieve_stripe_payment_intent(payment_intent_id):
    """Retrieve a Stripe PaymentIntent."""
    intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    return intent










