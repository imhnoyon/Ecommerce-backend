from rest_framework import serializers
from .models import Product,Order,OrderItem

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = [ "id","name", "sku", "description","price", "stock", "status", "created_at"]
        read_only_fields = ["id", "created_at"]



class OrderItemSerializer(serializers.ModelSerializer):
    product = serializers.StringRelatedField(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        source="product",
        write_only=True
    )
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_id",
            "quantity",
            "price",
            "subtotal",
        ]

    def get_subtotal(self, obj):
        return obj.subtotal()






class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)
    total_amount = serializers.DecimalField( max_digits=10,  decimal_places=2,  read_only=True )

    class Meta:
        model = Order
        fields = [ "id", "user", "status", "total_amount", "items", "created_at", ]
        read_only_fields = ["user", "created_at"]
        
        
        def create(self, validated_data):
            items_data = validated_data.pop("items")
            user = self.context["request"].user

            order = Order.objects.create(user=user, **validated_data)

            for item in items_data:
                OrderItem.objects.create( order=order, product=item["product"], quantity=item["quantity"], price=item["price"], )

            order.update_total()
            return order



