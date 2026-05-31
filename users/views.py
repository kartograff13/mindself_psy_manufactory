from django.contrib.auth import get_user_model, update_session_auth_hash
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView as BaseTokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView as BaseTokenRefreshView

from users.serializers import ChangePasswordSerializer, RegisterSerializer, UserProfileSerializer

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


class ProfileView(generics.RetrieveUpdateAPIView):
    """Получение и обновление профиля текущего пользователя."""

    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Получить профиль",
        description="Возвращает данные текущего пользователя: username, email, роль, телефон, аватар, био.",
    )
    def get(self, request, *args, **kwargs):
        """Возвращает профиль текущего пользователя."""
        return super().get(request, *args, **kwargs)

    @extend_schema(summary="Обновить профиль", description="Изменяет first_name, last_name, phone, avatar, bio.")
    def put(self, request, *args, **kwargs):
        """Полностью обновляет профиль пользователя."""
        return super().put(request, *args, **kwargs)

    @extend_schema(summary="Частично обновить профиль", description="Частично изменяет поля профиля.")
    def patch(self, request, *args, **kwargs):
        """Частично обновляет профиль пользователя."""
        return super().patch(request, *args, **kwargs)

    def get_object(self):
        """Возвращает текущего аутентифицированного пользователя."""
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    """Смена пароля текущего пользователя."""

    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Сменить пароль",
        description="Принимает old_password, new_password и new_password2. "
        "Обновляет пароль, если старый указан верно.",
    )
    def post(self, request):
        """Проверяет старый пароль, валидирует новый и сохраняет его."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"old_password": ["Неверный старый пароль."]}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data["new_password"])
        user.save()
        update_session_auth_hash(request, user)

        return Response({"detail": "Пароль успешно изменён."}, status=status.HTTP_200_OK)
