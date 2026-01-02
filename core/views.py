from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .models import Product,OrderItem,Order,User
from .serializers import ProductSerializer,OrderSerializer,OrderItemSerializer,RegisterSerializer

from rest_framework.permissions import IsAuthenticated



class RegisterUserView(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    


class productViewset(ModelViewSet):
    queryset=Product.objects.all()
    serializer_class= ProductSerializer
    permission_classes= [IsAuthenticated]
    
    
    #for each product filtering method
    # def get_queryset(self): 
    #     return super().get_queryset().filter(user=self.request.user)
    
    def perfrom_create(self,serializer):
        return serializer.save(user=self.request.user)
    
    
class OrderItemViewset(ModelViewSet):
    queryset=OrderItem.objects.all()
    serializer_class= OrderItemSerializer
    
    
    
    
class OrderViewset(ModelViewSet):
    queryset=Order.objects.all()
    serializer_class=OrderSerializer
    
    
