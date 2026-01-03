from rest_framework import serializers
from .models import Product,Order,OrderItem,User,Payment




class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ("id", "email", "password")

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"]
        )
        return user



class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [ "id","name", "sku", "description","price", "stock", "status", "created_at"]
        read_only_fields = ["id", "created_at"]
        
    

class OrderItemSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField( source="product", queryset=Product.objects.all())
    product_name = serializers.CharField(source="product.name",read_only=True)

    class Meta:
        model = OrderItem
        fields = ["product_id",'product_name', "quantity", "price"]




class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total_amount = serializers.DecimalField( max_digits=10, decimal_places=2, read_only=True )

    class Meta:
        model = Order
        fields = ["id", "user", "status", "total_amount", "items", "created_at"]
        read_only_fields = ["user", "created_at"]

    
    def create(self, validated_data):
        items_data = validated_data.pop("items")
        user = self.context["request"].user
        order = Order.objects.create(user=user, **validated_data)

        for item in items_data:
            OrderItem.objects.create( order=order, product=item["product"], quantity=item["quantity"], price=item["price"], )
        print("BEFORE UPDATE:", order.total_amount)    
        order.update_total()
        print("AFTER UPDATE:", order.total_amount)
        return order

    
    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

       
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            for item in items_data:
                OrderItem.objects.create(order=instance, product=item["product"], quantity=item["quantity"],  price=item["price"])
        
        instance.update_total()
        return instance





class CreatePaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["order", "provider"]
        
        
        
        
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = "__all__"
        read_only_fields = "__all__"