from django.contrib.auth import views as auth_views
from django.urls import path

from .views import PendingView, RegisterView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('pending/', PendingView.as_view(), name='pending'),
    path(
        'login/',
        auth_views.LoginView.as_view(template_name='account/login.html'),
        name='login',
    ),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
