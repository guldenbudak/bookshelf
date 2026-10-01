from django.urls import path
from. import views
from .views import home

urlpatterns = [
    path('', home, name='home'),
    path('books/', views.book_list, name='book-list'),
    path('feed/', views.book_feed, name='book-feed'),
    path('books/create/', views.book_create, name='book-create'),
    path('favorites/', views.favorite_list, name='favorite-list'),
    path('books/<int:pk>/',views.book_detail, name='book-detail'),
    path('books/<int:pk>/favorite/', views.favorite_toggle, name='favorite-toggle'),
    path('books/<int:pk>/comment/', views.comment_create, name='comment-create'),
    path('comments/<int:pk>/edit/', views.comment_update, name='comment-update'),
    path('comments/<int:pk>/delete/', views.comment_delete, name='comment-delete'),
    path('books/<int:pk>/update/',views.book_update, name='book-update'),
    path('books/<int:pk>/delete/',views.book_delete, name='book-delete'),
]
