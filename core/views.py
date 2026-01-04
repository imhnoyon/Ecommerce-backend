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
                # Lock the products to prevent race conditions
                product_ids = order.items.values_list('product_id', flat=True)
                products = Product.objects.select_for_update().filter(id__in=product_ids)
                product_dict = {p.id: p for p in products}
                
                
                # Reduce stock
                for item in order.items.all():
                    if item.product.stock < item.quantity:
                        return HttpResponse(f"Insufficient stock for {item.product.name}", status=400)

                for item in order.items.all():
                    item.product.reduce_stock(item.quantity) 

                order.status = 'paid'
                order.save()
                print(f"Order {order.id} status updated to paid")
                logger.info(f"Order {order.id} status updated to paid")
   

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
                return HttpResponse(f"<h1>Payment Successful!</h1><p>Transaction ID: {order.id}</p>")
                
            else:
                print(f"Order {order.id} is not pending, status: {order.status}")
                logger.warning(f"Order {order.id} is not pending, status: {order.status}")
    except Order.DoesNotExist:
        print(f"Order {order_id} does not exist")
        logger.error(f"Order {order_id} does not exist")
    except Exception as e:
        print(f"Error handling payment: {e}")
        logger.error(f"Error handling payment: {e}")




# bKash Payment Views
class BkashPaymentInitView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, order_id, *args, **kwargs):
        return Response({"message": f"bKash payment init for order {order_id}. Use POST with payer_reference."})

    def post(self, request, order_id, *args, **kwargs):
        print(f"bKash init: user={request.user}, order_id={order_id}") 
        payer_reference = request.data.get('payer_reference', '017XXXXXXXX')  # Example mobile number
        try:
            if request.user.is_staff or request.user.is_superuser:
                order = Order.objects.get(id=order_id)
            else:
                order = Order.objects.get(id=order_id, user=request.user)
            print(f"Order found: {order.id}, status={order.status}")
        except Order.DoesNotExist:
            print(f"Order not found for user {request.user} and order_id {order_id}")
            return Response({"error": "Order not found"}, status=404)

        if order.status != 'pending':
            return Response({"error": "Order is not pending"}, status=400)
        total=0
        for item in order.items.all():
            total +=int(item.price * item.quantity * 100)
            
        payment_data = create_bkash_payment(total, order.id, payer_reference)
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




from django.http import HttpResponse
from django.db import transaction

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
                    # select_for_update ব্যবহার করা হয়েছে যাতে একই সময়ে অন্য কেউ স্টক আপডেট না করতে পারে
                    order = Order.objects.select_for_update().get(id=order_id)
                    
                    if order.status == 'pending':
                        
                        # ১. ভ্যালিডেশন: আগে চেক করুন সব আইটেমের স্টক পর্যাপ্ত আছে কিনা
                        for item in order.items.all():
                            if item.product.stock < item.quantity:
                                # যদি স্টক কম থাকে, এখান থেকেই এরর মেসেজ দিন (পেমেন্ট রেকর্ড হবে না)
                                return HttpResponse(
                                    f"<h1>Payment Failed!</h1><p>Insufficient stock for {item.product.name}. "
                                    f"Available: {item.product.stock}, Requested: {item.quantity}</p>", 
                                    status=400
                                )

                        # ২. যদি উপরের লুপে কোনো সমস্যা না থাকে, তবে স্টক কমান
                        for item in order.items.all():
                            product = item.product 
                            product.reduce_stock(item.quantity)

                        # ৩. অর্ডার স্ট্যাটাস এবং পেমেন্ট রেকর্ড আপডেট
                        order.status = 'paid'
                        order.save()

                        Payment.objects.create(
                            order=order,
                            provider='bkash',
                            transaction_id=trx_id,
                            status='success',
                            raw_response=execute_data
                        )
                        
                        return HttpResponse(f"<h1>Payment Successful!</h1><p>Transaction ID: {trx_id}</p>")
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
        return HttpResponse("<h1>Payment Cancelled!</h1><p>You have cancelled the payment.</p>")
    
    return HttpResponse("<h1>Payment Failed!</h1>", status=400)
















