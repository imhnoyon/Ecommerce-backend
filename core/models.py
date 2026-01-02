from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import UserManager
from django.conf import settings
from django.db.models import Sum, F

class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email
    
    


class Product(models.Model):
    STATUS_CHOICES = (
        ("active", "Active"),
        ("inactive", "Inactive"),
    )

    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField()
    status = models.CharField( max_length=10, choices=STATUS_CHOICES,  default="active")
    created_at = models.DateTimeField(auto_now_add=True)

    def reduce_stock(self, quantity):
        if self.stock < quantity:
            raise ValueError("Insufficient stock")
        self.stock -= quantity
        self.save(update_fields=["stock"])

    def __str__(self):
        return self.name






class Order(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("canceled", "Canceled"),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="order")
    total_amount = models.DecimalField( max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_total(self):
        total = self.items.aggregate(
            total=Sum(F("price") * F("quantity"))
        )["total"]
        return total or 0

    def update_total(self):
        self.total_amount = self.calculate_total()
        self.save(update_fields=["total_amount"])

    def __str__(self):
        return f"Order #{self.id}"


class OrderItem(models.Model):
    order = models.ForeignKey( Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey( Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price = models.DecimalField( max_digits=10, decimal_places=2 )

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"







class Payment(models.Model):
    PROVIDER_CHOICES = (
        ("stripe", "Stripe"),
        ("bkash", "bKash"),
    )

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("success", "Success"),
        ("failed", "Failed"),
    )

    order = models.ForeignKey( Order, on_delete=models.CASCADE, related_name="payments" )
    provider = models.CharField( max_length=20, choices=PROVIDER_CHOICES )
    transaction_id = models.CharField( max_length=255, unique=True )
    status = models.CharField( max_length=20, choices=STATUS_CHOICES, default="pending")
    raw_response = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.provider} | {self.transaction_id}"

