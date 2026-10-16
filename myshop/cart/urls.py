from django.urls import path
from . import views

app_name = "cart"

urlpatterns = [
    path("", views.cart_view, name="cart_view"),
    path("add/<slug:slug>/", views.add_to_cart, name="add_to_cart"),
    path("update/<slug:slug>/", views.update_cart, name="update_cart"),
    path("remove/<slug:slug>/", views.remove_from_cart, name="remove_from_cart"),
    path("empty/", views.empty_cart, name="empty_cart"),
    path(
        "move-to-wishlist/<slug:slug>/",
        views.move_to_wishlist,
        name="move_to_wishlist",
    ),


    # Wishlist URLs
    path("wishlist/", views.wishlist_view, name="wishlist_view"),
    path("wishlist/add/<slug:slug>/", views.add_to_wishlist, name="add_to_wishlist"),
    path("wishlist/remove/<slug:slug>/", views.remove_from_wishlist, name="remove_from_wishlist"),
    path("wishlist/move-to-cart/<slug:slug>/", views.move_to_cart_from_wishlist, name="move_to_cart_from_wishlist"),
    path("add-all-to-cart/", views.add_all_to_cart_from_wishlist, name="move_all_to_cart"),
    path("wishlist/clear/", views.clear_wishlist, name="clear_wishlist"),
]
