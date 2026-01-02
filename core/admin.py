from django.contrib import admin
from .models import OrderItem,Order,Product

admin.site.register(Product)
admin.site.register(Order)    
admin.site.register(OrderItem) 
