from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    PendingView,
    RegisterView,
    account_delete,
    friend_remove,
    friend_request_accept,
    friend_request_reject,
    friend_request_send,
    friends_list,
    logout_confirm,
    profile_detail,
    profile_edit,
    user_search,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('pending/', PendingView.as_view(), name='pending'),
    path('profile/', profile_detail, name='my-profile'),
    path('profile/edit/', profile_edit, name='profile-edit'),
    path('profile/delete/', account_delete, name='account-delete'),
    path('profile/<str:username>/', profile_detail, name='profile-detail'),
    path('friends/', friends_list, name='friends'),
    path('users/', user_search, name='user-search'),
    path('friends/request/<str:username>/', friend_request_send, name='friend-request-send'),
    path('friends/accept/<int:pk>/', friend_request_accept, name='friend-request-accept'),
    path('friends/reject/<int:pk>/', friend_request_reject, name='friend-request-reject'),
    path('friends/remove/<str:username>/', friend_remove, name='friend-remove'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='account/login.html'),#djangonun hazır giriş viewı parola kontrolü oturum açma hata mesajları
        name='login',
    ),
    path('logout/confirm/', logout_confirm, name='logout-confirm'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
