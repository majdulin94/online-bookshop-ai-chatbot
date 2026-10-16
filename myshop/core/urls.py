from django.urls import path
from . import views
from myshop.books import views as book_views

urlpatterns = [
    path('', views.home, name='home'),
    path('books/', book_views.book_list, name='book_list'),
]
