from myshop.cart.models import CartItem, WishlistItem

def navbar_counts(request):
    cart_count = 0
    wishlist_count = 0
    user = request.user
    if user.is_authenticated:
        cart_count = CartItem.objects.filter(user=user).count()
        wishlist_count = WishlistItem.objects.filter(user=user).count()
    else:
        # For guests, use session cart (adapt if you use different session key)
        cart = request.session.get('cart', {})
        wishlist = request.session.get('wishlist', [])
        cart_count = sum(cart.values()) if cart else 0
        wishlist_count = len(wishlist) if wishlist else 0
    return {
        'navbar_cart_count': cart_count,
        'navbar_wishlist_count': wishlist_count,
    }
