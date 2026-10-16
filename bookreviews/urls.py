from django.urls import path
from . import views

app_name = 'bookreviews'

urlpatterns = [
    path('add/<slug:slug>/', views.add_review, name='add_review'),
    path('delete/<slug:slug>/', views.delete_review, name='delete_review'),
    path('like/<int:review_id>/', views.like_review, name='like_review'),       # NEU
    path('dislike/<int:review_id>/', views.dislike_review, name='dislike_review'), # NEU
]
