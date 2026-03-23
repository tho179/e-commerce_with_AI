from django.urls import path

from .views import HealthCheck, LoginView, RefreshView, RegisterView, UpdateRoleView, VerifyView

urlpatterns = [
    path('health/', HealthCheck.as_view()),
    path('auth/register/', RegisterView.as_view()),
    path('auth/login/', LoginView.as_view()),
    path('auth/refresh/', RefreshView.as_view()),
    path('auth/verify/', VerifyView.as_view()),
    path('auth/users/role/', UpdateRoleView.as_view()),
]
