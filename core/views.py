from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from .models import Product,OrderItem,Order,User
from .serializers import ProductSerializer,OrderSerializer,OrderItemSerializer,RegisterSerializer
from .permissions import IsAdminOrReadOnly

from rest_framework.pagination import PageNumberPagination

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
    
    
    
    
class OrderViewset(ModelViewSet):
    queryset=Order.objects.all()
    serializer_class=OrderSerializer
    
    
