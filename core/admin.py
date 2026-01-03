from django.contrib import admin
from .models import OrderItem,Order,Product,User,Payment


# admin.site.register(User)
# admin.site.register(Product)
# admin.site.register(Order)    
# admin.site.register(OrderItem) 
# admin.site.register(Payment)



@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email","is_staff","is_active","created_at")
    
    
@admin.register(Product)
class UserAdmin(admin.ModelAdmin):
    list_display = ("name","sku","description","price","stock","status","created_at")
    
    
@admin.register(Order)
class UserAdmin(admin.ModelAdmin):
    list_display = ("user","total_amount","status","created_at")
    
    
@admin.register(OrderItem)
class UserAdmin(admin.ModelAdmin):
    list_display = ("order","product","quantity","price","subtotal")
    
    
    
@admin.register(Payment)
class UserAdmin(admin.ModelAdmin):
    list_display = ("order","provider","transaction_id","status","raw_response","created_at")