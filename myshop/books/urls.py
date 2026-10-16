
from django.urls import path
from .views import book_list, book_detail

app_name = "books"

urlpatterns = [
    path('home/', book_list, name='book_list'),
    path('home/<slug:slug>/', book_detail, name='book_detail'),

]
