from rest_framework.routers import DefaultRouter
from .views import productViewset,OrderItemViewset,OrderViewset
from django.urls import path, include
router = DefaultRouter()

router.register('products', productViewset, basename='product')
router.register('orders', OrderViewset, basename='order')
router.register('orderitems', OrderItemViewset, basename='orderitems')


urlpatterns =[
    path("",include(router.urls)),
]