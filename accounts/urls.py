from django.contrib.auth import views as auth_views
from django.urls import path

from .views import PendingView, RegisterView, profile_detail, profile_edit

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('pending/', PendingView.as_view(), name='pending'),
    path('profile/', profile_detail, name='my-profile'),
    path('profile/edit/', profile_edit, name='profile-edit'),
    path('profile/<str:username>/', profile_detail, name='profile-detail'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='account/login.html'),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
