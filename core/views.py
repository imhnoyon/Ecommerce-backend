from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .models import Product,OrderItem,Order
from .serializers import ProductSerializer,OrderSerializer,OrderItemSerializer

class productViewset(ModelViewSet):
    queryset=Product.objects.all()
    serializer_class= ProductSerializer
    
    
    
class OrderItemViewset(ModelViewSet):
    queryset=OrderItem.objects.all()
    serializer_class= OrderItemSerializer
    
    
    
class OrderViewset(ModelViewSet):
    queryset=Order.objects.all()
    serializer_class=OrderSerializer
    
    
