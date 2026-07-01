from django.conf import settings
from django.db import models
from phonenumber_field.modelfields import PhoneNumberField


class ConsultationService(models.Model):
    """
    Модель услуги консультации. Определяет название, описание, цену и активность услуги
    """

    name = models.CharField(max_length=100, verbose_name="Название услуги")
    description = models.TextField(verbose_name="Описание")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Цена (справочно)"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")

    class Meta:
        verbose_name = "Услуга консультации"
        verbose_name_plural = "Услуги консультаций"

    def __str__(self):
        """Возвращает строковое представление названия услуги."""
        return self.name


class ConsultationRequest(models.Model):
    """
    Модель заявки на консультацию, оставленной пользователем (авторизованным или анонимным).
    Содержит контактные данные, выбранную услугу, статус обработки.
    """

    class Status(models.TextChoices):
        """Статус обработки заявки."""

        NEW = "new", "Новая"
        PROCESSED = "processed", "Обработана"
        CANCELLED = "cancelled", "Отменена"

    service = models.ForeignKey(
        ConsultationService, on_delete=models.CASCADE, related_name="requests", verbose_name="Услуга"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="consultation_requests",
        verbose_name="Пользователь",
    )
    name = models.CharField(max_length=255, verbose_name="ФИО")
    phone = PhoneNumberField(verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, verbose_name="Статус"  # type: ignore[arg-type]
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Заявка на консультацию"
        verbose_name_plural = "Заявки на консультацию"
        ordering = ["-created_at"]

    def __str__(self):
        """Возвращает строковое представление заявки: ФИО и название услуги."""
        return f"{self.name} - {self.service.name}"


class Supervision(models.Model):
    """
    Модель супервизии (индивидуальной и групповой) для психологов.
    Содержит информацию о времени, цене, статусе, типе и количестве участников.
    """

    class SupervisionType(models.TextChoices):
        """Тип супервизии: индивидуальная или групповая."""

        INDIVIDUAL = "individual", "Индивидуальная"
        GROUP = "group", "Групповая"

    class Status(models.TextChoices):
        """Статус супервизии."""

        OPEN = "open", "Открыта"
        CANCELLED = "cancelled", "Отменена"
        COMPLETED = "completed", "Завершена"

    psychologist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="supervisions",
        limit_choices_to={"role": "teacher"},
        verbose_name="Ведущий",
    )
    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    supervision_type = models.CharField(
        max_length=20, choices=SupervisionType.choices, verbose_name="Тип супервизии"  # type: ignore[arg-type]
    )
    max_participants = models.PositiveIntegerField(
        default=1, verbose_name="Максимальное количество участников", help_text="Для групповой супервизии укажите >1"
    )
    start_datetime = models.DateTimeField(verbose_name="Дата и время начала")
    end_datetime = models.DateTimeField(verbose_name="Дата и время окончания")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, verbose_name="Статус"  # type: ignore[arg-type]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Супервизия"
        verbose_name_plural = "Супервизии"
        ordering = ["-start_datetime"]

    def __str__(self):
        """Возвращает строковое представление названия супервизии, дату и время начала."""
        return f"{self.title} ({self.start_datetime:%d.%m.%Y %H:%M})"


class SupervisionBooking(models.Model):
    """Модель записи студента на супервизию. Обеспечивает уникальность пары (студент, супервизия)."""

    class Status(models.TextChoices):
        """Статус записи."""

        CONFIRMED = "confirmed", "Подтверждена"
        CANCELLED = "cancelled", "Отменена"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="supervision_bookings", verbose_name="Студент"
    )
    supervision = models.ForeignKey(
        Supervision, on_delete=models.CASCADE, related_name="bookings", verbose_name="Супервизия"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,  # type: ignore[arg-type]
        default=Status.CONFIRMED,
        verbose_name="Статус",
    )
    booked_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата записи")

    class Meta:
        verbose_name = "Запись на супервизию"
        verbose_name_plural = "Записи на супервизию"
        unique_together = ["student", "supervision"]
        ordering = ["-booked_at"]

    def __str__(self):
        """Возвращает строковое представление имени студента и название супервизии."""
        return f"{self.student.username} - {self.supervision.title}"


class TherapySession(models.Model):
    """
    Модель терапевтической сессии (индивидуальной работы с психологом). Содержит информацию о времени, цене и статусе.
    """

    class Status(models.TextChoices):
        """Статус сессии."""

        OPEN = "open", "Открыта"
        CANCELLED = "cancelled", "Отменена"
        COMPLETED = "completed", "Завершена"

    psychologist = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="therapy_sessions",
        limit_choices_to={"role": "teacher"},
        verbose_name="Психолог",
    )
    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    start_datetime = models.DateTimeField(verbose_name="Дата и время начала")
    end_datetime = models.DateTimeField(verbose_name="Дата и время окончания")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN, verbose_name="Статус"  # type: ignore[arg-type]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Терапевтическая сессия"
        verbose_name_plural = "Терапевтические сессии"
        ordering = ["-start_datetime"]

    def __str__(self):
        """Возвращает строковое представление названия сессии, дату и время начала."""
        return f"{self.title} ({self.start_datetime:%d.%m.%Y %H:%M})"


class TherapyBooking(models.Model):
    """Модель записи студента на терапевтическую сессию. Обеспечивает уникальность пары (студент, сессия)."""

    class Status(models.TextChoices):
        """Статус записи."""

        CONFIRMED = "confirmed", "Подтверждена"
        CANCELLED = "cancelled", "Отменена"

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="therapy_bookings", verbose_name="Студент"
    )
    session = models.ForeignKey(
        TherapySession, on_delete=models.CASCADE, related_name="bookings", verbose_name="Сессия"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,  # type: ignore[arg-type]
        default=Status.CONFIRMED,
        verbose_name="Статус",
    )
    booked_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата записи")

    class Meta:
        verbose_name = "Запись на терапию"
        verbose_name_plural = "Записи на терапию"
        unique_together = ["student", "session"]
        ordering = ["-booked_at"]

    def __str__(self):
        """Возвращает строковое представление имени студента и название сессии."""
        return f"{self.student.username} - {self.session.title}"


class SupervisionRequest(models.Model):
    """
    Модель заявки на участие в супервизии (групповой или индивидуальной). Может быть оставлена как авторизованным,
    так и анонимным пользователям. Содержит контактные данные, выбранную супервизию и статус обработки.
    """

    class Status(models.TextChoices):
        """Статус обработки заявки на супервизию."""

        NEW = "new", "Новая"
        PROCESSED = "processed", "Обработана"
        CANCELLED = "cancelled", "Отменена"

    supervision = models.ForeignKey(
        Supervision, on_delete=models.CASCADE, related_name="requests", verbose_name="Супервизия"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="supervision_requests",
        verbose_name="Пользователь",
    )
    name = models.CharField(max_length=255, verbose_name="ФИО")
    phone = PhoneNumberField(verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, verbose_name="Статус"  # type: ignore[arg-type]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Заявка на супервизию"
        verbose_name_plural = "Заявки на супервизию"
        ordering = ["-created_at"]

    def __str__(self):
        """Возвращает строковое представление ФИО заявителя и название супервизии."""
        return f"{self.name} - {self.supervision.title}"


class TherapyRequest(models.Model):
    """
    Модель заявки на терапевтическую сессию (индивидуальную работу с психологом). Может быть оставлена как
    авторизованным, так и анонимным пользователям. Содержит контактные данные, выбранную сессию и статус обработки.
    """

    class Status(models.TextChoices):
        """Статус обработки заявки на терапевтическую сессию."""

        NEW = "new", "Новая"
        PROCESSED = "processed", "Обработана"
        CANCELLED = "cancelled", "Отменена"

    session = models.ForeignKey(
        TherapySession, on_delete=models.CASCADE, related_name="requests", verbose_name="Сессия"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="therapy_requests",
        verbose_name="Пользователь",
    )
    name = models.CharField(max_length=255, verbose_name="ФИО")
    phone = PhoneNumberField(verbose_name="Телефон")
    email = models.EmailField(blank=True, verbose_name="Email")
    comment = models.TextField(blank=True, verbose_name="Комментарий")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.NEW, verbose_name="Статус"  # type: ignore[arg-type]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Заявка на терапию"
        verbose_name_plural = "Заявки на терапию"
        ordering = ["-created_at"]

    def __str__(self):
        """Возвращает строковое представление ФИО заявителя и название сессии."""
        return f"{self.name} - {self.session.title}"
