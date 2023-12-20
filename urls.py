from django.urls import path
from . import views
urlpatterns = [
    path('',views.index,name='index'),
    path('checkseats/',views.checkseats,name='checkseats'),
    path('booking/',views.booking,name='booking'),
    path('transaction/',views.transaction,name='transaction'),
    path('mpesa',views.mpesa,name='mpesa'),
    path('stk_push',views.stk_push_callback,name='stk_push')
    
]
