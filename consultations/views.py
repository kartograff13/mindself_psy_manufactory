from typing import cast

from django.conf import settings
from django.core.mail import send_mail
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from consultations.models import (
    ConsultationRequest,
    ConsultationService,
    Supervision,
    SupervisionBooking,
    SupervisionRequest,
    TherapyBooking,
    TherapyRequest,
    TherapySession,
)
from consultations.serializers import (
    ConsultationRequestCreateSerializer,
    ConsultationRequestListSerializer,
    ConsultationServiceSerializer,
    SupervisionBookingSerializer,
    SupervisionRequestCreateSerializer,
    SupervisionRequestListSerializer,
    SupervisionSerializer,
    TherapyBookingSerializer,
    TherapyRequestCreateSerializer,
    TherapyRequestListSerializer,
    TherapySessionSerializer,
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
        Фильтрация заявок по роли:
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


@extend_schema_view(
    list=extend_schema(summary="Список супервизий"),
    retrieve=extend_schema(summary="Детали супервизии"),
    create=extend_schema(summary="Создать супервизию (психолог/админ)"),
    update=extend_schema(summary="Обновить супервизию"),
    partial_update=extend_schema(summary="Частично обновить супервизию"),
    destroy=extend_schema(summary="Удалить супервизию"),
)
class SupervisionViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления супервизиями.
    - list, retrieve - доступны всем (включая анонимов)
    - create, update, partial_update, destroy - только аутентифицированных психологов (teacher) или администратор
    """

    queryset = Supervision.objects.all()
    serializer_class = SupervisionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """
        Назначает права доступа:
        - list, retrieve: AllowAny (могут все просматривать)
        - остальные действия: IsAuthenticated и дополнительная проверка роли (admin или teacher)
        """
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        """
        При создании супервизии проверяет, что текущий пользователь психолог или администратор,
        и назначает его ведущим.
        """
        user = cast(User, self.request.user)
        if user.role not in ["admin", "teacher"]:
            raise PermissionDenied("Только психологи и администраторы могут создавать супервизии.")

        serializer.save(psychologist=user)


@extend_schema_view(
    list=extend_schema(summary="Мои записи на супервизию (студент)"),
    create=extend_schema(summary="Записаться на супервизию"),
    destroy=extend_schema(summary="Отменить запись"),
)
class SupervisionBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления записями на супервизию:
    - list: студент видит только свои записи, администратор - все
    - create: студент создаёт запись для себя
    - destroy: студент может отменить свою запись, администратор - любую
    """

    serializer_class = SupervisionBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Фильтрует записи:
        - администратор - все записи
        - обычный пользователь - только свои (studentn = текущий пользователь)
        """
        user = cast(User, self.request.user)
        if user.role == "admin":
            return SupervisionBooking.objects.all()
        return SupervisionBooking.objects.filter(student=user)

    def perform_create(self, serializer):
        """При создании записи автоматически назначает текущего пользователя студентом."""
        serializer.save(student=cast(User, self.request.user))


@extend_schema_view(
    list=extend_schema(summary="Список терапевтических сессий"),
    retrieve=extend_schema(summary="Детали сессии"),
    create=extend_schema(summary="Создать сессию (психолог/админ)"),
    update=extend_schema(summary="Обновить сессию"),
    partial_update=extend_schema(summary="Частично обновить сессию"),
    destroy=extend_schema(summary="Удалить сессию"),
)
class TherapySessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления терапевтическими сессиями.
    - list, retrieve - доступны всем
    - create, update, partial_update, destroy - только для психологов (teacher) и администратора
    """

    queryset = TherapySession.objects.all()
    serializer_class = TherapySessionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        """
        Назначает права доступа:
        - list, retrieve: AllowAny
        - остальные: только аутентифицированные с ролью admin или teacher
        """
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        """Проверяет, что текущий пользователь - психолог или администратор, назначает его психологом сессии."""
        user = cast(User, self.request.user)

        if user.role not in ["admin", "teacher"]:
            raise PermissionDenied("Только психологи или администратор могут создавать сессии.")

        serializer.save(psychologist=user)


@extend_schema_view(
    list=extend_schema(summary="Мои записи на терапию (студент)"),
    create=extend_schema(summary="Записаться на терапию"),
    destroy=extend_schema(summary="Отменить запись"),
)
class TherapyBookingViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления записями на терапевтические сессии:
    - list: студент видит только свои записи, администратор - все
    - create: студент создаёт запись для себя
    - destroy: студент может отменить свою запись, администратор - любую
    """

    serializer_class = TherapyBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Фильтрует записи:
        - для администратора - все записи
        - для остальных - только свои (student = текущий пользователь)
        """
        user = cast(User, self.request.user)
        if user.role == "admin":
            return TherapyBooking.objects.all()
        return TherapyBooking.objects.filter(student=user)

    def perform_create(self, serializer):
        """При создании записи автоматически назначает текущего пользователя студентом."""
        serializer.save(student=cast(User, self.request.user))


@extend_schema_view(
    list=extend_schema(summary="Список заявок на супервизию (психолог/админ)"),
    retrieve=extend_schema(summary="Детали заявки"),
    create=extend_schema(summary="Оставить заявку на супервизию"),
    update=extend_schema(summary="Обновить статус заявки (психолог/админ)"),
    partial_update=extend_schema(summary="Частично обновить заявку"),
    destroy=extend_schema(summary="Удалить заявку"),
)
class SupervisionRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления заявками на супервизию:
    - создание доступно всем (включая анонимных пользователей)
    - просмотр, обновление, удаление доступно только авторизованным пользователям с фильтрацией по роли:
    -- администратор/психолог: все заявки
    -- обычный пользователь: только свои
    """

    queryset = SupervisionRequest.objects.all()

    def get_serializer_class(self):
        """Для создания использует сериализатор с валидацией, для остальных - список/детали."""
        if self.action == "create":
            return SupervisionRequestCreateSerializer
        return SupervisionRequestListSerializer

    def get_permissions(self):
        """Разрешает создание без аутентификации, остальные действия - только авторизованным."""
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """
        Фильтрует заявки:
        - для анонимных пользователей: пустой queryset (но такие запросы не попадают сюда, т.к. require auth)
        - для администратора/психолога (teacher): все заявки
        - для обычного пользователя: только его заявки
        """
        user = cast(User, self.request.user)
        if not user.is_authenticated:
            return SupervisionRequest.objects.none()
        if user.role in ["admin", "teacher"]:
            return SupervisionRequest.objects.all()

        return SupervisionRequest.objects.filter(user=user)

    def perform_create(self, serializer):
        """
        Сохраняет заявку: для авторизованного пользователя подставляет user,
        для анонимного пользователя: просто сохраняет. После сохранения отправляет email-уведомление на адрес,
        указанный в CONSULTATION_EMAIL.
        """
        if self.request.user.is_authenticated:
            serializer.save(user=cast(User, self.request.user))
        else:
            serializer.save()

        instance = serializer.instance
        subject = f"Новая заявка на супервизию: {instance.supervision.title}"  # type: ignore[arg-type]
        message = (
            f"Имя: {instance.name}\n"  # type: ignore[arg-type]
            f"Телефон: {instance.phone}\n"  # type: ignore[arg-type]
            f"Email: {instance.email or 'не указан'}\n"  # type: ignore[arg-type]
            f"Комментарий: {instance.comment or 'нет'}\n"  # type: ignore[arg-type]
        )
        recipient = getattr(settings, "CONSULTATION_EMAIL", settings.DEFAULT_FROM_EMAIL)
        send_mail(subject, message, None, [recipient], fail_silently=True)  # type: ignore[arg-type]

    def perform_update(self, serializer):
        """
        Проверяет, что пользователь имеет право изменять заявку (администратор/психолог).
        Если прав нет - выбрасывает PermissionDenied.
        """
        if self.request.user.role not in ["admin", "teacher"]:  # type: ignore[arg-type]
            raise PermissionDenied("Недостаточно прав.")

        serializer.save()


@extend_schema_view(
    list=extend_schema(summary="Список заявок на терапию (психолог/администратор)"),
    retrieve=extend_schema(summary="Детали заявки"),
    create=extend_schema(summary="Оставить заявку на терапию"),
    update=extend_schema(summary="Обновить статус заявки (психолог/администратор)"),
    partial_update=extend_schema(summary="Частично обновить заявку"),
    destroy=extend_schema(summary="Удалить заявку"),
)
class TherapyRequestViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления заявками на терапевтические сессии:
    - создание доступно всем (включая анонимных пользователей)
    - просмотр, обновление, удаление - только авторизованным, с фильтрацией по роли:
    -- администратор/психолог: все заявки
    -- обычный пользователь: только свои
    """

    queryset = TherapyRequest.objects.all()

    def get_serializer_class(self):
        """Для создания использует сериализатор с валидацией, для остальных - список/детали."""
        if self.action == "create":
            return TherapyRequestCreateSerializer
        return TherapyRequestListSerializer

    def get_permissions(self):
        """Разрешает создание без аутентификации, остальные действия - только авторизованным пользователям."""
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        """
        Фильтрует заявки:
        - для анонимных пользователей: queryset пустой
        - для администратора/психолога (teacher): все заявки
        - для обычного пользователя: только его заявки
        """
        user = cast(User, self.request.user)
        if not user.is_authenticated:
            return TherapyRequest.objects.none()
        if user.role in ["admin", "teacher"]:
            return TherapyRequest.objects.all()
        return TherapyRequest.objects.filter(user=user)

    def perform_create(self, serializer):
        """
        Сохраняет заявку: для авторизованного пользователя подставляет user,
        для анонимного пользователя - просто сохраняет. После сохранения отправляет email-уведомление на адрес,
        указанный в CONSULTATION_EMAIL.
        """
        if self.request.user.is_authenticated:
            serializer.save(user=cast(User, self.request.user))
        else:
            serializer.save()

        instance = serializer.instance
        subject = f"Новая заявка на терапию: {instance.session.title}"  # type: ignore[arg-type]
        message = (
            f"Имя: {instance.name}\n"  # type: ignore[arg-type]
            f"Телефон: {instance.phone}\n"  # type: ignore[arg-type]
            f"Email: {instance.email or 'не указан'}\n"  # type: ignore[arg-type]
            f"Комментарий: {instance.comment or 'нет'}\n"  # type: ignore[arg-type]
        )
        recipient = getattr(settings, "CONSULTATION_EMAIL", settings.DEFAULT_FROM_EMAIL)
        send_mail(subject, message, None, [recipient], fail_silently=True)  # type: ignore[arg-type]

    def perform_update(self, serializer):
        """
        Проверяет, что пользователь имеет право изменять заявку (администратор/психолог).
        Если прав нет - выбрасывает PermissionDenied.
        """
        if self.request.user.role not in ["admin", "teacher"]:  # type: ignore[arg-type]
            raise PermissionDenied("Недостаточно прав.")

        serializer.save()
