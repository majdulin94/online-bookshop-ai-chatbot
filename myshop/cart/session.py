from django.conf import settings
from myshop.cart.models import WishlistItem

SESSION_CART_KEY = "cart"
SESSION_WISHLIST_KEY = "wishlist"

# --- CART SESSION ---

def get_cart_session(request):
    """
    Returns the cart as a dict: {slug: quantity}
    If it doesn't exist, returns an empty dict.
    """
    return request.session.get(SESSION_CART_KEY, {})

def save_cart_session(request, cart):
    """
    Updates the session with the new cart dict.
    """
    request.session[SESSION_CART_KEY] = cart
    request.session.modified = True

def add_to_cart_session(request, slug, quantity=1):
    """
    Adds a book (by slug) to the session cart.
    If it already exists, increases the quantity.
    """
    cart = get_cart_session(request)
    slug = str(slug)
    cart[slug] = cart.get(slug, 0) + quantity
    save_cart_session(request, cart)

def remove_from_cart_session(request, slug):
    """
    Removes a book (by slug) from the session cart.
    """
    cart = get_cart_session(request)
    slug = str(slug)
    if slug in cart:
        del cart[slug]
    save_cart_session(request, cart)

def update_cart_session(request, slug, quantity):
    """
    Updates the quantity for a specific book in the cart.
    Removes the book if quantity < 1.
    """
    cart = get_cart_session(request)
    slug = str(slug)
    if quantity < 1:
        cart.pop(slug, None)
    else:
        cart[slug] = quantity
    save_cart_session(request, cart)

def clear_cart_session(request):
    """
    Removes the cart from the session.
    """
    if SESSION_CART_KEY in request.session:
        del request.session[SESSION_CART_KEY]
        request.session.modified = True

# --- WISHLIST SESSION ---

def get_wishlist_session(request):
    """Return wishlist as set of slugs (string) for guest."""
    # Stored as list of slugs in session
    return set(request.session.get(SESSION_WISHLIST_KEY, []))

def save_wishlist_session(request, wishlist_slugs):
    request.session[SESSION_WISHLIST_KEY] = list(map(str, wishlist_slugs))
    request.session.modified = True

def add_to_wishlist_session(request, slug):
    wishlist = get_wishlist_session(request)
    wishlist.add(str(slug))
    save_wishlist_session(request, wishlist)

def remove_from_wishlist_session(request, slug):
    wishlist = get_wishlist_session(request)
    wishlist.discard(str(slug))
    save_wishlist_session(request, wishlist)

def clear_wishlist_session(request):
    if SESSION_WISHLIST_KEY in request.session:
        del request.session[SESSION_WISHLIST_KEY]
        request.session.modified = True

def get_wishlist_books(request):
    """Return a list of Book objects in wishlist, for user or guest."""

    from myshop.books.models import Book
    if request.user.is_authenticated:
        items = WishlistItem.objects.filter(user=request.user).select_related("book")
        return [item.book for item in items if item.book and item.book.slug]
    else:
        wishlist_ids = get_wishlist_session(request)
        books = Book.objects.filter(slug__in=wishlist_ids)
        return list(books)
