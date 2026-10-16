from django.contrib import admin
from .models import CartItem, WishlistItem

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ["user", "get_book_name", "quantity", "added_at", "updated_at"]
    list_filter = ["added_at", "updated_at"]
    search_fields = ["user__username", "book__name"]

    def get_book_name(self, obj):
        return obj.book.name
    get_book_name.short_description = 'Book'

@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ["user", "get_book_name", "added_at"]
    list_filter = ["added_at"]
    search_fields = ["user__username", "book__name"]

    def get_book_name(self, obj):
        return obj.book.name
    get_book_name.short_description = 'Book'
