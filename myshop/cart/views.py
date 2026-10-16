from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from decimal import Decimal, ROUND_HALF_UP
from django.views.decorators.http import require_http_methods
import json

from myshop.books.models import Book
from .models import CartItem, WishlistItem
from .session import (
    SESSION_WISHLIST_KEY,
    get_cart_session, add_to_cart_session, remove_from_cart_session, update_cart_session, clear_cart_session,
    get_wishlist_session, add_to_wishlist_session, remove_from_wishlist_session, clear_wishlist_session, get_wishlist_books
)

# ---- 1. CART VIEW ----
def cart_view(request):
    if request.user.is_authenticated:
        items = CartItem.objects.filter(user=request.user).select_related("book")
        cart_items = [
            (item.book, item.quantity, item.book.slug, (item.book.price or 0) * item.quantity)
            for item in items
        ]
    else:
        cart = get_cart_session(request)
        books = Book.objects.in_bulk(list(cart.keys()), field_name='slug')
        cart_items = [
            (books[slug], qty, slug, (books[slug].price or 0) * qty)
            for slug, qty in cart.items() if slug in books
        ]

    subtotal = sum(total_price for _, _, _, total_price in cart_items)
    shipping_cost = Decimal("0") if subtotal >= Decimal("30.00") else Decimal("3.95")
    tax_rate = Decimal("0.19")
    tax = ((subtotal + shipping_cost) * tax_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = subtotal + shipping_cost + tax

    if request.user.is_authenticated:
        wishlist_count = request.user.wishlistitem_set.count()
    else:
        wishlist_count = len(request.session.get(SESSION_WISHLIST_KEY, []))

    return render(request, "cart/cart.html", {
        "cart_items": cart_items,
        "subtotal": subtotal,
        "shipping_cost": shipping_cost,
        "tax": tax,
        "total": total,
        "wishlist_count": wishlist_count,
    })

# ---- 2. ADD TO CART ----
@require_http_methods(["GET", "POST"])
@require_POST
def add_to_cart(request, slug):
    book = get_object_or_404(Book, slug=slug)
    if book.stock_status == "Out of Stock":
        msg = f"'{book.title}' is currently out of stock."
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"success": False, "message": msg})
        messages.error(request, msg)
        return redirect("books:book_detail", slug=book.slug)

    try:
        if request.method == "GET":
            quantity = 1
        elif request.headers.get("X-Requested-With") == "XMLHttpRequest":
            data = json.loads(request.body)
            quantity = int(data.get("quantity", 1))
        else:
            quantity = int(request.POST.get("quantity", 1))

        if quantity < 1 or quantity > 999:
            return JsonResponse({"success": False, "message": "Quantity must be at least 1"})

        if request.user.is_authenticated:
            cart_item, created = CartItem.objects.get_or_create(user=request.user, book=book)
            if not created:
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            cart_item.save()
            cart_count = CartItem.objects.filter(user=request.user).count()
        else:
            add_to_cart_session(request, slug, quantity)
            cart_count = len(get_cart_session(request))

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({
                "status": "success",
                "message": f"{book.title} added to cart",
                "cart_count": cart_count,
            })

        messages.success(request, f"{book.title} added to cart")
        return redirect("cart:cart_view")

    except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return JsonResponse({"success": False, "message": "Invalid quantity"})

# ---- 3. UPDATE CART ----
@require_http_methods(["POST"])
def update_cart(request, slug):
    try:
        if request.content_type == "application/json":
            data = json.loads(request.body)
            quantity = int(data.get("quantity", 1))
        else:
            quantity = int(request.POST.get("quantity", 1))
        if quantity < 1:
            return JsonResponse({"status": "error", "message": "Quantity must be at least 1"})

        if request.user.is_authenticated:
            cart_item = get_object_or_404(CartItem, user=request.user, book__slug=slug)
            cart_item.quantity = quantity
            cart_item.save()
            book = cart_item.book
            item_total = (book.price or 0) * quantity
            items = CartItem.objects.filter(user=request.user).select_related("book")
            all_items = [(item.book, item.quantity, item.book.slug,) for item in items]
        else:
            update_cart_session(request, slug, quantity)
            cart = get_cart_session(request)
            books = Book.objects.in_bulk(list(cart.keys()), field_name='slug')
            book = books.get(slug)
            item_total = (book.price or 0) * quantity if book else 0
            all_items = [(books[s], qty, s) for s, qty in cart.items() if s in books]

        subtotal = sum((book.price or 0) * qty for book, qty, _ in all_items)
        shipping_cost = Decimal("0") if subtotal >= 30 else Decimal("3.95")
        tax = ((subtotal + shipping_cost) * Decimal("0.19")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total = subtotal + shipping_cost + tax

        return JsonResponse({
            "status": "success",
            "item_total": float(item_total),
            "subtotal": float(subtotal),
            "shipping_cost": float(shipping_cost),
            "tax": float(tax),
            "total": float(total),
        })

    except (ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return JsonResponse({"status": "error", "message": "Invalid data"})

# ---- 4. REMOVE FROM CART ----
@require_http_methods(["POST"])
def remove_from_cart(request, slug):
    if request.user.is_authenticated:
        cart_item = get_object_or_404(CartItem, user=request.user, book__slug=slug)
        cart_item.delete()
    else:
        remove_from_cart_session(request, slug)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "success"})
    messages.success(request, "Item removed from cart")
    return redirect("cart:cart_view")

# ---- 5. EMPTY CART ----
@require_http_methods(["POST"])
def empty_cart(request):
    if request.user.is_authenticated:
        CartItem.objects.filter(user=request.user).delete()
    else:
        clear_cart_session(request)
    messages.success(request, "Cart has been emptied")
    return redirect("cart:cart_view")

# ---- 6. MOVE TO WISHLIST ----
@require_http_methods(["POST"])
def move_to_wishlist(request, slug):
    book = get_object_or_404(Book, slug=slug)

    # 1. Remove from cart
    if request.user.is_authenticated:
        CartItem.objects.filter(user=request.user, book=book).delete()
    else:
        remove_from_cart_session(request, slug)

    # 2. Add to wishlist
    if request.user.is_authenticated:
        WishlistItem.objects.get_or_create(user=request.user, book=book)
    else:
        add_to_wishlist_session(request, slug)

    messages.success(request, f"{book.title} moved to wishlist")
    return redirect("cart:wishlist_view")

# ---- 7. WISHLIST VIEWS ----
def wishlist_view(request):
    wishlist_books = get_wishlist_books(request)
    total_value = sum(book.price or 0 for book in wishlist_books)
    # Check if there is at least one available book
    has_available_books = any(book.stock_status != "Out of Stock" for book in wishlist_books)
    return render(request, "cart/wishlist.html", {
        "wishlist_items": wishlist_books,
        "total_value": total_value,
        "has_available_books": has_available_books,  #
    })

@require_http_methods(["GET", "POST"])
@require_POST
def add_to_wishlist(request, slug):
    book = get_object_or_404(Book, slug=slug)
    if request.user.is_authenticated:
        WishlistItem.objects.get_or_create(user=request.user, book=book)
        wishlist_count = WishlistItem.objects.filter(user=request.user).count()
    else:
        add_to_wishlist_session(request, slug)
        wishlist_count = len(get_wishlist_session(request))
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({
            "status": "success",
            "message": f"{book.title} added to wishlist",
            "wishlist_count": wishlist_count,
        })
    messages.success(request, f"{book.title} added to wishlist")
    return redirect("cart:wishlist_view")

@require_http_methods(["POST"])
def remove_from_wishlist(request, slug):
    if request.user.is_authenticated:
        WishlistItem.objects.filter(user=request.user, book__slug=slug).delete()
    else:
        remove_from_wishlist_session(request, slug)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"status": "success"})
    messages.success(request, "Item removed from wishlist")
    return redirect("cart:wishlist_view")

@require_http_methods(["POST"])
def clear_wishlist(request):
    if request.user.is_authenticated:
        WishlistItem.objects.filter(user=request.user).delete()
    else:
        clear_wishlist_session(request)
    messages.success(request, "Wishlist has been cleared")
    return redirect("cart:wishlist_view")

@require_http_methods(["POST"])
def move_to_cart_from_wishlist(request, slug):
    book = get_object_or_404(Book, slug=slug)
    if book.stock_status == "Out of Stock":
        messages.error(request, f"'{book.title}' is currently out of stock and cannot be added to the cart.")
        return redirect("cart:wishlist_view")
    # Add to cart first
    if request.user.is_authenticated:
        cart_item, created = CartItem.objects.get_or_create(user=request.user, book=book)
        if not created:
            cart_item.quantity += 1
            cart_item.save()
        WishlistItem.objects.filter(user=request.user, book=book).delete()
    else:
        add_to_cart_session(request, slug, 1)
        remove_from_wishlist_session(request, slug)
    messages.success(request, f"{book.title} moved to cart")
    return redirect("cart:cart_view")

@require_http_methods(["POST"])
def add_all_to_cart_from_wishlist(request):
    not_added = 0
    added = 0
    if request.user.is_authenticated:
        wishlist_items = WishlistItem.objects.filter(user=request.user).select_related('book')
        for item in wishlist_items:
            if item.book.stock_status == "Out of Stock":
                not_added += 1
                continue
            cart_item, created = CartItem.objects.get_or_create(user=request.user, book=item.book)
            if not created:
                cart_item.quantity += 1
                cart_item.save()
            # Only delete books that were successfully added
            item.delete()
            added += 1
    else:
        from myshop.books.models import Book
        wishlist_slugs = get_wishlist_session(request)
        books = Book.objects.filter(slug__in=wishlist_slugs)
        # List to delete books that were added to cart from wishlist
        added_slugs = []
        for book in books:
            if book.stock_status == "Out of Stock":
                not_added += 1
                continue
            add_to_cart_session(request, book.slug, 1)
            added_slugs.append(book.slug)
            added += 1
        # Only remove books that were added to the cart from the wishlist
        wishlist_set = set(wishlist_slugs)
        for slug in added_slugs:
            remove_from_wishlist_session(request, slug)
        # Do not use clear_wishlist_session here!
    if not_added > 0:
        messages.warning(request, f"{not_added} book(s) were not added to cart because they are out of stock.")
    if added > 0:
        messages.success(request, "All available wishlist items moved to cart.")
    if not_added == 0 and added == 0:
        messages.info(request, "No books were added to cart.")
    return redirect("cart:cart_view")
