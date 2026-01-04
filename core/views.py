from .payments_system import create_stripe_checkout_session

from django.shortcuts import redirect, render
from requests import Response
from rest_framework.viewsets import ModelViewSet
import stripe
from .models import Product,OrderItem,Order,User,Payment
from .serializers import ProductSerializer,OrderSerializer,OrderItemSerializer,RegisterSerializer,CreatePaymentSerializer,PaymentSerializer
from .permissions import IsAdminOrReadOnly

import logging
logger = logging.getLogger(__name__)

from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import json
from django.db import transaction

from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
import uuid

from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings

from rest_framework import status



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
    # permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == "create":
            return CreatePaymentSerializer
        return PaymentSerializer
    
    
    def perform_create(self, serializer):
        serializer.save( transaction_id=str(uuid.uuid4()), status="pending", raw_response={})
 
 




class StripeCreateSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        order_id = kwargs.get('id')  # Get order id from URL
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        if order.status != 'pending':
            return Response({"error": "Order is not pending"}, status=400)

        try:
            success_url = request.build_absolute_uri('/success/')
            cancel_url = request.build_absolute_uri('/cancel/')
            checkout_session = create_stripe_checkout_session(order, success_url, cancel_url)
            return Response({'session_url': checkout_session.url, 'session_id': checkout_session.id})
        except Exception as e:
            return Response({'msg': 'Something went wrong while creating stripe session', 'error': str(e)}, status=500)






@csrf_exempt
def stripe_webhook(request):
    print("Stripe webhook called")
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_SECRET_WEBHOOK
        )
    except ValueError as e:
        # Invalid payload
        print(f"Invalid payload: {e}")
        logger.error(f"Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        print(f"Invalid signature: {e}")
        logger.error(f"Invalid signature: {e}")
        return HttpResponse(status=400)

    print(f"Received event: {event['type']}")
    logger.info(f"Received event: {event['type']}")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        print(f"Processing payment for session: {session['id']}")
        logger.info(f"Processing payment for session: {session['id']}")
        handle_successful_payment(session)
        print("**************",session)

    return HttpResponse(status=200)


def handle_successful_payment(session):
    print(f"Handling payment for session: {session['id']}")
    order_id = int(session['metadata']['order_id'])
    print(f"Order ID from metadata: {order_id}")
    logger.info(f"Handling payment for order_id: {order_id}")
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)
            print(f"Order found: {order.id}, current status: {order.status}")
            logger.info(f"Order found: {order.id}, current status: {order.status}")
            if order.status == 'pending':
                order.status = 'paid'
                order.save()
                print(f"Order {order.id} status updated to paid")
                logger.info(f"Order {order.id} status updated to paid")

                # Reduce stock
                for item in order.items.all():
                    print(f"Reducing stock for product {item.product.name}: {item.quantity}")
                    logger.info(f"Reducing stock for product {item.product.name}: {item.quantity}")
                    item.product.reduce_stock(item.quantity)

                # Create Payment record
                Payment.objects.create(
                    order=order,
                    provider='stripe',
                    transaction_id=session.get('payment_intent', session['id']),
                    status='success',
                    raw_response=session
                )
                print(f"Payment record created for order {order.id}")
                logger.info(f"Payment record created for order {order.id}")
            else:
                print(f"Order {order.id} is not pending, status: {order.status}")
                logger.warning(f"Order {order.id} is not pending, status: {order.status}")
    except Order.DoesNotExist:
        print(f"Order {order_id} does not exist")
        logger.error(f"Order {order_id} does not exist")
    except Exception as e:
        print(f"Error handling payment: {e}")
        logger.error(f"Error handling payment: {e}")





















