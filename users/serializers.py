import re

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from rest_framework import serializers

from .models import User


class RegisterSerializer(serializers.ModelSerializer):
    """
    Сериализатор для регистрации пользователя с подтверждением пароля,
    расширенной валидацией надёжности пароля, уникальностью email и проверкой username на запрещенные слова.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        help_text="Пароль длиной не менее 8 символов, содержащий хотя бы одну цифру и одну букву.",
    )
    password2 = serializers.CharField(
        write_only=True, required=True, help_text="Подтверждение пароля (должно совпадать с password)."
    )
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password", "password2")

    def validate_username(self, value):
        """Проверяет username на список запрещённых слов."""

        reserved = getattr(settings, "FORBIDDEN_USERNAMES", [])

        if value.lower() in [name.lower() for name in reserved]:
            raise serializers.ValidationError("Это имя пользователя недоступно.")

        return value

    def validate_email(self, value):
        """Проверяет уникальность email."""

        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Пользователь с таким email уже существует.")

        return value

    def validate_password(self, value):
        """
        Проверяет сложность пароля:

        - хотя бы одна буква (латиница или кириллица)
        - хотя бы одна цифра
        """

        if not re.search(r"[A-Za-zА-Яа-я]", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну букву.")

        if not re.search(r"\d", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну цифру.")

        return value

    def validate(self, attrs):
        """Проверяет совпадение password и password2."""

        if attrs.get("password") != attrs.get("password2"):
            raise serializers.ValidationError("Пароли не совпадают.")

        return attrs

    def create(self, validated_data):
        """Создаёт пользователя, отбрасывая поле password2."""

        validated_data.pop("password2")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )

        return user


class UserProfileSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра и редактирования собственного профиля."""

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "phone", "avatar", "bio", "role")
        read_only_fields = ("id", "username", "email", "role")

    def validate_avatar(self, value):
        """
        Проверяет загружаемый аватар:
        - размер не более 2 МБ
        - разрешенные форматы: JPEG, PNG
        """
        if isinstance(value, UploadedFile):
            if value.size > 2 * 1024 * 1024:
                raise serializers.ValidationError("Размер файла не должен превышать 2 МБ.")

            allowed_mime_types = ["image/jpeg", "image/jpg", "image/png"]
            if value.content_type not in allowed_mime_types:
                raise serializers.ValidationError("Разрешены только файлы JPEG и PNG.")

        return value

    def update(self, instance, validated_data):
        """Обновляет профиль пользователя. При замене аватара удаляет старый файл из хранилища."""
        if "avatar" in validated_data:
            old_avatar = instance.avatar  # type: ignore[arg-type]
            new_avatar = validated_data.get("avatar")
            if old_avatar and old_avatar != new_avatar:
                old_avatar.delete(save=False)

        return super().update(instance, validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля: принимает старый и новый пароль, валидирует новый."""

    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, min_length=8)
    new_password2 = serializers.CharField(required=True, write_only=True, help_text="Подтверждение нового пароля")

    def validate_new_password(self, value):
        """Проверяет сложность нового пароля (буква + цифра)."""
        if not re.search(r"[A-Za-zА-Яа-я]", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну букву.")
        if not re.search(r"\d", value):
            raise serializers.ValidationError("Пароль должен содержать хотя бы одну цифру.")

        return value

    def validate(self, attrs):
        """Проверяет совпадение нового пароля и его подтверждения."""
        if attrs.get("new_password") != attrs.get("new_password2"):
            raise serializers.ValidationError(
                {"new_password2": "Новый пароль и подтверждение нового пароля не совпадают."}
            )

        return attrs
