import requests
from django.conf import settings


def get_bkash_token():
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

    response = requests.post(url, json=payload, headers=headers)
    data = response.json()

    return data.get("id_token")
