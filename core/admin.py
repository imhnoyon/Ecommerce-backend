from django.contrib import admin
from .models import OrderItem,Order,Product,User


admin.site.register(User)
admin.site.register(Product)
admin.site.register(Order)    
admin.site.register(OrderItem) 
