from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
import stripe
from .models import Product,OrderItem,Order,User,Payment
from .serializers import ProductSerializer,OrderSerializer,OrderItemSerializer,RegisterSerializer,CreatePaymentSerializer,PaymentSerializer
from .permissions import IsAdminOrReadOnly

from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
import uuid

class productPagination(PageNumberPagination):
    page_size = 3


class RegisterUserView(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    
    


class productViewset(ModelViewSet):
    queryset=Product.objects.all()
    serializer_class= ProductSerializer
    pagination_class = productPagination
    permission_classes = [IsAdminOrReadOnly]
    
    def perfrom_create(self,serializer):
        return serializer.save(user=self.request.user)
    
    
class OrderItemViewset(ModelViewSet):
    queryset=OrderItem.objects.all()
    serializer_class= OrderItemSerializer
    permission_classes=[IsAdminOrReadOnly]
    
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Order.objects.all()
        return Order.objects.filter(user=user)
    
    
    
class OrderViewset(ModelViewSet):
    queryset=Order.objects.all()
    serializer_class=OrderSerializer
    permission_classes=[IsAdminOrReadOnly]
    
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Order.objects.all()
        return Order.objects.filter(user=user)
    
    
    
    
class PaymentViewSet(ModelViewSet):
    queryset = Payment.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == "create":
            return CreatePaymentSerializer
        return PaymentSerializer
    
    
    def perform_create(self, serializer):
        serializer.save( transaction_id=str(uuid.uuid4()), status="pending", raw_response={})
 
 


















        
#chatGpt theke niye try korar jonno        
        
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
import requests
from .payments_system import get_bkash_token, create_bkash_payment, execute_bkash_payment, create_stripe_payment_intent, confirm_stripe_payment_intent, retrieve_stripe_payment_intent
    
class BkashPaymentInitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")

        #  Order check
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        #  Create Payment (DB)
        transaction_id = str(uuid.uuid4())

        payment = Payment.objects.create(
            order=order,
            provider="bkash",
            transaction_id=transaction_id,
            status="pending",
            raw_response={}
        )

        #  bKash token
        token = get_bkash_token()
        if not token:
            return Response({"error": "bKash token failed"}, status=400)
        payload = {
            "mode": "0011",
            "payerReference": request.user.email,
            "callbackURL": getattr(settings, "BKASH_CALLBACK_URL", "http://127.0.0.1:8000/api/payment/bkash/callback/"),
            "amount": str(order.total_amount),
            "currency": "BDT",
            "intent": "sale",
            "merchantInvoiceNumber": transaction_id,
        }

        data = create_bkash_payment(token, payload)
        if data is None:
            payment.raw_response = {"error": "create request failed"}
            payment.status = "failed"
            payment.save()
            return Response({"error": "bKash create payment failed"}, status=400)

        #  Save gateway response
        payment.raw_response = data
        payment.save()

        # Return redirect URL (sandbox flows usually provide bkashURL/paymentID)
        return Response({
            "paymentID": data.get("paymentID"),
            "bkashURL": data.get("bkashURL"),
            "transaction_id": transaction_id
        })




class PaymentSuccessView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        transaction_id = request.data.get("transaction_id")

        payment = Payment.objects.get(transaction_id=transaction_id)

        # ✔ payment success
        payment.status = "success"
        payment.save()

        # ✔ order paid
        order = payment.order
        order.status = "paid"
        order.save()

        return Response({"message": "Payment successful"})









class BkashPaymentExecuteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        paymentID = request.data.get("paymentID")
        token = get_bkash_token()
        if not token:
            return Response({"error": "bKash token failed"}, status=400)

        payload = {"paymentID": paymentID}
        data = execute_bkash_payment(token, payload)
        if data is None:
            return Response({"error": "bKash execute failed"}, status=400)

        transaction_id = data.get("merchantInvoiceNumber") or data.get("merchantInvoiceNo") or data.get("merchantInvoice")

        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        # statusCode '0000' indicates success in many bKash APIs
        if data.get("statusCode") == "0000" or data.get("status") == "success":
            payment.status = "success"
            payment.raw_response = data
            payment.save()

            order = payment.order
            order.status = "paid"
            order.save()

            return Response({"message": "bKash payment successful"})

        payment.status = "failed"
        payment.raw_response = data
        payment.save()

        return Response({"message": "Payment failed"}, status=400)



from rest_framework.decorators import api_view

@api_view(["GET", "POST"])
def bkash_callback(request):
    # bKash may call this endpoint with POST data or query params
    data = request.data if request.method == "POST" else request.GET

    # try to find merchantInvoiceNumber or similar field
    transaction_id = data.get("merchantInvoiceNumber") or data.get("merchantInvoiceNo") or data.get("merchantInvoice") or data.get("merchantInvoiceNumber")

    if not transaction_id:
        return Response({"error": "merchant invoice not provided"}, status=400)

    try:
        payment = Payment.objects.get(transaction_id=transaction_id)
    except Payment.DoesNotExist:
        return Response({"error": "Payment not found"}, status=404)

    # Try to determine success from status code or provided status
    status_code = data.get("statusCode") or data.get("status")
    payment.raw_response = data
    if status_code == "0000" or str(status_code).lower() == "success":
        payment.status = "success"
        payment.save()
        order = payment.order
        order.status = "paid"
        order.save()
        return Response({"message": "Payment marked as success"})

    payment.status = "failed"
    payment.save()
    return Response({"message": "Payment updated"})


# Stripe Payment Views
class StripePaymentInitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("StripePaymentInitView called")  # Debug
        order_id = request.data.get("order_id")
        print(f"order_id: {order_id}")  # Debug

        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        if order.total_amount <= 0:
            return Response({"error": "Order total amount must be greater than 0"}, status=400)

        print(f"Order total: {order.total_amount}, type: {type(order.total_amount)}")  # Debug
        transaction_id = str(uuid.uuid4())
        payment = Payment.objects.create(
            order=order,
            provider="stripe",
            transaction_id=transaction_id,
            status="pending",
            raw_response={}
        )

        # Create Stripe PaymentIntent
        try:
            intent = create_stripe_payment_intent(
                amount=order.total_amount,
                currency="bdt",  # Using BDT for Bangladesh
                metadata={"order_id": str(order.id), "transaction_id": transaction_id}
            )
            print(f"Stripe intent created: {intent.id if intent else 'None'}")  # Debug
        except Exception as exc:
            print(f"Stripe error: {exc}")  # Debug
            payment.status = "failed"
            payment.raw_response = {"error": str(exc)}
            payment.save()
            return Response({"error": "Stripe payment init failed", "details": str(exc)}, status=400)

        if not intent:
            payment.status = "failed"
            payment.raw_response = {"error": "Stripe PaymentIntent creation failed"}
            payment.save()
            return Response({"error": "Stripe payment init failed"}, status=400)

        payment.raw_response = {
            "payment_intent_id": intent.id,
            "client_secret": intent.client_secret,
            "amount": intent.amount,
            "currency": intent.currency,
        }
        payment.save()

        return Response({
            "payment_intent_id": intent.id,
            "client_secret": intent.client_secret,
            "transaction_id": transaction_id
        })

class StripePaymentConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        print("StripePaymentConfirmView called")  # Debug
        payment_intent_id = request.data.get("payment_intent_id")
        payment_method_id = request.data.get("payment_method_id")  # For backend confirmation
        print(f"payment_intent_id: {payment_intent_id}, payment_method_id: {payment_method_id}")  # Debug

        if not payment_intent_id:
            return Response({"error": "payment_intent_id required"}, status=400)

        # Retrieve and confirm the PaymentIntent
        if payment_method_id:
            # Update the PaymentIntent with payment method
            stripe.PaymentIntent.modify(
                payment_intent_id,
                payment_method=payment_method_id,
            )
        
        intent = confirm_stripe_payment_intent(
            payment_intent_id, 
            return_url="http://127.0.0.1:8000/payment/success/"
        )

        if not intent:
            return Response({"error": "Stripe confirm failed"}, status=400)

        # Find payment by transaction_id from metadata
        transaction_id = intent.metadata.get("transaction_id")
        if not transaction_id:
            return Response({"error": "Transaction ID not found in metadata"}, status=400)

        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
        except Payment.DoesNotExist:
            return Response({"error": "Payment not found"}, status=404)

        if intent.status == "succeeded":
            payment.status = "success"
            payment.raw_response = {
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount_received": intent.amount_received,
            }
            payment.save()

            order = payment.order
            order.status = "paid"
            order.save()

            return Response({"message": "Stripe payment successful"})

        payment.status = "failed"
        payment.raw_response = {
            "payment_intent_id": intent.id,
            "status": intent.status,
            "last_payment_error": getattr(intent.last_payment_error, 'message', None) if intent.last_payment_error else None,
        }
        payment.save()

        return Response({"message": "Payment failed"}, status=400)
    

import json
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@api_view(["POST"])
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        return HttpResponse(status=400)

    # Handle the event
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        transaction_id = payment_intent['metadata'].get('transaction_id')
        if transaction_id:
            try:
                payment = Payment.objects.get(transaction_id=transaction_id)
                payment.status = "success"
                payment.raw_response = payment_intent
                payment.save()
                order = payment.order
                order.status = "paid"
                order.save()
            except Payment.DoesNotExist:
                pass  # Log or handle

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        transaction_id = payment_intent['metadata'].get('transaction_id')
        if transaction_id:
            try:
                payment = Payment.objects.get(transaction_id=transaction_id)
                payment.status = "failed"
                payment.raw_response = payment_intent
                payment.save()
            except Payment.DoesNotExist:
                pass

    return HttpResponse(status=200)