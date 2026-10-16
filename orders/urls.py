app_name = "orders"
from django.urls import path
from . import views
from .views import OrdersCreateCheckoutSessionView


urlpatterns = [
    path('place-order/', views.place_order, name='place_order'),
    path('guest-place-order/', views.guest_place_order, name='guest_place_order'),

    # Stripe Payment URLs
    path('create-checkout-session/', OrdersCreateCheckoutSessionView.as_view(), name='create-checkout-session'),
    path('success/', views.payment_success, name='payment_success'),
    path('cancel/', views.payment_cancel, name='payment_cancel'),

    # Return request
    path('request-return/<int:order_id>/', views.request_return, name='request_return'),

    # View all orders
    path('order-history/', views.order_history, name='order_history'),

    # View all returns
    path('return-history/', views.return_history, name='return_history'),
]
