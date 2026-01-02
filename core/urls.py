from rest_framework.routers import DefaultRouter
from .views import productViewset,OrderItemViewset,OrderViewset,RegisterUserView
from django.urls import path, include

from rest_framework_simplejwt.views import TokenObtainPairView

router = DefaultRouter()

router.register('products', productViewset, basename='product')
router.register('orders', OrderViewset, basename='order')
router.register('orderitems', OrderItemViewset, basename='orderitems')
router.register('register',RegisterUserView,basename='Register')

urlpatterns =[
    path("",include(router.urls)),
    path("login/",TokenObtainPairView.as_view(),name='login'),
    
]