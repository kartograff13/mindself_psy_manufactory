from typing import cast

from django.conf import settings
from django.core.mail import send_mail
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from consultations.models import ConsultationRequest, ConsultationService
from consultations.serializers import (
    ConsultationRequestCreateSerializer,
    ConsultationRequestListSerializer,
    ConsultationServiceSerializer,
)
from users.models import User


@extend_schema_view(
    list=extend_schema(summary="Список услуг консультаций"),
    retrieve=extend_schema(summary="Детали услуги"),
    create=extend_schema(summary="Создать услуги (только администратор)"),
    update=extend_schema(summary="Обновить услугу (только администратор)"),
    partial_update=extend_schema(summary="Частично обновить услугу (только администратор)"),
    destroy=extend_schema(summary="Удалить услугу (только администратор)"),
)
class ConsultationServiceViewSet(viewsets.ModelViewSet):
    """ViewSet для управления услугами консультаций (администратор) и просмотра (все пользователи)."""

    queryset = ConsultationService.objects.filter(is_active=True)
    serializer_class = ConsultationServiceSerializer

    def get_permissions(self):
        """Права: список и детали - всем пользователям, остальное - только администратору."""
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]


@extend_schema_view(
    list=extend_schema(summary="Список заявок (психолог/администратор)"),
    retrieve=extend_schema(summary="Детали заявки (психолог/администратор)"),
    create=extend_schema(
        summary="Оставить заявку на консультацию",
        description="Доступно всем. Для авторизованных данные подтягиваются из профиля.",
    ),
    update=extend_schema(summary="Обновить статус заявки (психолог/администратор)"),
    partial_update=extend_schema(summary="Частично обновить заявку (психолог/администратор)"),
    destroy=extend_schema(summary="Удалить заявку"),
)
class ConsultationRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с заявками на консультацию:
    - создание доступно всем (в т.ч. анонимам)
    - просмотр/изменение - только авторизованным, с фильтрацией по роли
    """

    queryset = ConsultationRequest.objects.all()

    def get_serializer_class(self):
        """Для создания используется специальный сериализатор, для остального - список/детали."""
        if self.action == "create":
            return ConsultationRequestCreateSerializer
        return ConsultationRequestListSerializer

    def get_permissions(self):
        """Только создание без аутентификации, остальные действия требуют авторизации."""
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """
        Фильтрация заявок по роли?
        - администратор/психолог (teacher): все заявки
        - обычный пользователь: только свои
        - аноним - пустой queryset (никогда не используется, т.к. требуется авторизация)
        """
        user = cast(User, self.request.user)
        if not user.is_authenticated:
            return ConsultationRequest.objects.none()
        if user.role in ["admin", "teacher"]:
            return ConsultationRequest.objects.all()

        return ConsultationRequest.objects.filter(user=user)

    def perform_create(self, serializer):
        """
        Сохраняет заявку: для авторизованного пользователя привязывает user, для анонима - простое сохранение.
        После сохранения отправляет email-уведомление администратору/психологу.
        """
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()

        instance = serializer.instance
        subject = f"Новая заявка на консультацию: {instance.service.name}"  # type: ignore[arg-type]
        message = (
            f"Имя: {instance.name}\n"  # type: ignore[arg-type]
            f"Телефон: {instance.phone}\n"  # type: ignore[arg-type]
            f"Email: {instance.email or 'не указан'}\n"  # type: ignore[arg-type]
            f"Комментарий: {instance.comment or 'нет'}\n"  # type: ignore[arg-type]
            f"Дата: {instance.created_at: %d.%m.%Y %H:%M}"  # type: ignore[arg-type]
        )
        recipient = getattr(settings, "CONSULTATION_EMAIL", settings.DEFAULT_FROM_EMAIL)
        send_mail(subject, message, None, [recipient], fail_silently=True)  # type: ignore[arg-type]

    def perform_update(self, serializer):
        """Проверяет права на обновление заявки (только администратор или психолог)."""
        if self.request.user.role not in ["admin", "teacher"]:  # type: ignore[arg-type]
            raise PermissionDenied("Недостаточно прав для изменения заявки.")

        serializer.save()
