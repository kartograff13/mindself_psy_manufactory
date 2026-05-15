from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Кастомная модель пользователя с ролями.

    Роли:
        - admin: администратор, полный доступ.
        - teacher: преподаватель, владелец курсов.
        - client: клиент, доступ к записи на консультацию и к покупке и прохождению курсов.
    """

    class Role(models.TextChoices):
        ADMIN = "admin", "Администратор"
        TEACHER = "teacher", "Преподаватель"
        CLIENT = "client", "Клиент"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CLIENT,
        verbose_name="Роль",
        help_text="Определяет права доступа пользователя в системе",
    )

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
