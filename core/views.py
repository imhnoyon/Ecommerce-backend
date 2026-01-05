from .payments_system import create_stripe_checkout_session, create_bkash_payment, execute_bkash_payment, query_bkash_payment
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
from django.http import HttpResponse,JsonResponse
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
    permission_classes=[IsAuthenticated]
    
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Order.objects.all()
        return Order.objects.filter(user=user)
    
    
    
class OrderViewset(ModelViewSet):
    queryset=Order.objects.all()
    serializer_class=OrderSerializer
    permission_classes=[IsAuthenticated]
    
    
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
        
        for item in order.items.all():
            if item.product.stock < item.quantity:
                return Response({
                    "error": f"stock out: {item.product.name}",
                    "available_stock": item.product.stock
                }, status=400)
        

        try:
            success_url = request.build_absolute_uri('/success/')
            cancel_url = request.build_absolute_uri('/cancel/')
            checkout_session = create_stripe_checkout_session(order, success_url, cancel_url)
            return Response({'session_url': checkout_session.url, 'session_id': checkout_session.id})
        except Exception as e:
            return Response({'msg': 'Something went wrong while creating stripe session', 'error': str(e)}, status=500)




@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_SECRET_WEBHOOK
        )
    except Exception as e:
        logger.error(f"Webhook signature error: {e}")
        return HttpResponse(status=400)

    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        success = handle_successful_payment(session)
        if not success:
            return HttpResponse(status=500)

    return HttpResponse(status=200)

def handle_successful_payment(session):
    try:
        order_id = session['metadata'].get('order_id')
        if not order_id:
            return False

        with transaction.atomic():
            
            order = Order.objects.select_for_update().get(id=order_id)
            
            if order.status == 'pending':
                
                for item in order.items.all():
                    if item.product.stock < item.quantity:
                        logger.error(f"Stock insufficient for {item.product.name}")
                        return False 
                    item.product.reduce_stock(item.quantity)
                order.update_total()
                order.status = 'paid'
                order.save()

                Payment.objects.create(
                    order=order,
                    provider='stripe',
                    transaction_id=session.get('payment_intent', session['id']),
                    status='success',
                    raw_response=session
                )
                return True
            else:
                logger.warning(f"Order {order.id} already processed.")
                return True 
    except Exception as e:
        logger.error(f"Error handling payment: {str(e)}")
        return False





# bKash Payment Views
class BkashPaymentInitView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id, *args, **kwargs):
        return Response({"message": f"bKash payment init for order {order_id}. Use POST with payer_reference."})

    def post(self, request, order_id, *args, **kwargs):
        print(f"bKash init: user={request.user}, order_id={order_id}") 
         
        try:
            if request.user.is_staff or request.user.is_superuser:
                order = Order.objects.get(id=order_id)
            else:
                order = Order.objects.get(id=order_id, user=request.user)
                payer_reference = str(order.id) 
            print(f"Order found: {order.id}, status={order.status}")
        except Order.DoesNotExist:
            print(f"Order not found for user {request.user} and order_id {order_id}")
            return Response({"error": "Order not found"}, status=404)

        if order.status != 'pending':
            return Response({"error": "Order is not pending"}, status=400)
            
        for item in order.items.all():
            if item.product.stock < item.quantity:
                return Response({
                    "error": f"Insufficient stock for {item.product.name}",
                    "product_id": item.product.id,
                    "available_stock": item.product.stock
                }, status=400)
                
        subtotal = sum(item.subtotal() for item in order.items.all())   
        payment_data = create_bkash_payment(subtotal, order.id, payer_reference)
        if payment_data:
            return Response(payment_data)
        else:
            return Response({"error": "Failed to create bKash payment"}, status=500)


class BkashPaymentExecuteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        payment_id = request.data.get('payment_id')
        if not payment_id:
            return Response({"error": "Payment ID required"}, status=400)

        execute_data = execute_bkash_payment(payment_id)
        if execute_data:
            return Response(execute_data)
        else:
            return Response({"error": "Failed to execute bKash payment"}, status=500)






@csrf_exempt
def bkash_callback(request):
    payment_id = request.GET.get('paymentID')
    status = request.GET.get('status')

    if status == 'success':
        execute_data = execute_bkash_payment(payment_id)
        
        if execute_data and execute_data.get('statusCode') == '0000':
            order_id = execute_data.get('merchantInvoiceNumber')
            trx_id = execute_data.get('trxID')
            
            try:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(id=order_id)
                    
                    if order.status == 'pending':
                        
                        
                        for item in order.items.all():
                            if item.product.stock < item.quantity:
                                Response({"error": "Insufficient stock"}, status=500)

                        for item in order.items.all():
                            product = item.product 
                            product.reduce_stock(item.quantity)

                        
                        order.update_total()
                        order.status = 'paid'
                        order.save()

                        Payment.objects.create(
                            order=order,
                            provider='bkash',
                            transaction_id=trx_id,
                            status='success',
                            raw_response=execute_data
                        )
                        
                        return HttpResponse(f"Payment successful and order processed and transaction_id-->{trx_id}.")
                    else:
                        return HttpResponse("Order already processed.")
            
            except Order.DoesNotExist:
                return HttpResponse("Order not found in database", status=404)
            except Exception as e:
                logger.error(f"bKash callback processing error: {e}")
                return HttpResponse(f"Error processing payment: {str(e)}", status=500)
        else:
            error_msg = execute_data.get('statusMessage') if execute_data else "API Connection Failed"
            return HttpResponse(f"Payment execution failed: {error_msg}", status=400)

    elif status == 'cancel':
        return JsonResponse({ "status": status,"message": f"Payment {status}" }, status=400)
    return JsonResponse({ "status": status,"message": f"Payment Payment Failed!" }, status=400)
















