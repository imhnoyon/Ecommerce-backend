from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
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
from .payments_system import get_bkash_token
    
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

        #  REAL bKash CREATE PAYMENT API
        url = f"{settings.BKASH_BASE_URL}/tokenized/checkout/create"

        headers = {
            "Authorization": token,
            "X-APP-Key": settings.BKASH_APP_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "mode": "0011",
            "payerReference": request.user.email,
            "callbackURL": "http://127.0.0.1:8000/api/payment/bkash/callback/",
            "amount": str(order.total_amount),
            "currency": "BDT",
            "intent": "sale",
            "merchantInvoiceNumber": transaction_id,
        }

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        #  Save gateway response
        payment.raw_response = data
        payment.save()

        # Return redirect URL
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

        url = f"{settings.BKASH_BASE_URL}/tokenized/checkout/execute"

        headers = {
            "Authorization": token,
            "X-APP-Key": settings.BKASH_APP_KEY,
            "Content-Type": "application/json",
        }

        payload = {
            "paymentID": paymentID
        }

        response = requests.post(url, json=payload, headers=headers)
        data = response.json()

        transaction_id = data.get("merchantInvoiceNumber")

        payment = Payment.objects.get(transaction_id=transaction_id)

        if data.get("statusCode") == "0000":
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
    return requests.Response({"message": "Callback received"})