from django.urls import path

from .views import ChangePasswordView, ProfileView, RegisterView, TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", ProfileView.as_view(), name="user_profile"),
    path("profile/change-password/", ChangePasswordView.as_view(), name="change_password"),
]
