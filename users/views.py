from django.contrib.auth import get_user_model
from rest_framework import generics, permissions

from users.serializers import RegisterSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Представление для регистрации новых пользователей."""

    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer
