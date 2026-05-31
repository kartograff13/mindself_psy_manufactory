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
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW, verbose_name="Статус")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Заявка на консультацию"
        verbose_name_plural = "Заявки на консультацию"
        ordering = ["-created_at"]

    def __str__(self):
        """Возвращает строковое представление заявки: ФИО и название услуги"""
        return f"{self.name} - {self.service.name}"
