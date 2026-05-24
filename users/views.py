from django.contrib.auth import get_user_model
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, permissions
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from users.serializers import RegisterSerializer

User = get_user_model()


@extend_schema(
    summary="Регистрация нового пользователя",
    description="Создаёт пользователя с ролью 'client'. Возвращает данные созданного пользователя",
    request=RegisterSerializer,
    responses={201: RegisterSerializer},
    examples=[
        OpenApiExample(
            "Пример запроса",
            value={
                "username": "new_user",
                "email": "user@example.com",
                "password": "Str0ngPass1",
                "password2": "Str0ngPass1",
            },
        ),
    ],
)
class RegisterView(generics.CreateAPIView):
    """Представление для регистрации новых пользователей."""

    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer


@extend_schema(
    summary="Получить JWT токен",
    description="Возвращает access и refresh токены для аутентификации",
)
class TokenObtainPairView(BaseTokenObtainPairView):
    pass


@extend_schema(
    summary="Обновить JWT токены",
    description="Обновляет access токен по refresh токену",
)
class TokenRefreshView(BaseTokenRefreshView):
    pass
