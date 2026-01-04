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










