from django.conf import settings
from django.db import models


class Course(models.Model):
    """Курс (раздел), создаваемый преподавателем."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_courses",
        limit_choices_to={"role": "teacher"},
        verbose_name="Владелец",
    )
    title = models.CharField(max_length=255, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    is_published = models.BooleanField(default=False, verbose_name="Опубликовано")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"

    def __str__(self):
        return self.title


class Lesson(models.Model):
    """Урок внутри курса."""

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name="Курс",
    )
    title = models.CharField(max_length=255, verbose_name="Название урока")
    content = models.TextField(blank=True, verbose_name="Текстовый контент (HTML)")
    video_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на видео (внешний ресурс)")
    video_file = models.FileField(upload_to="videos/", blank=True, null=True, verbose_name="Видеофайл")
    order = models.PositiveIntegerField(verbose_name="Порядковый номер")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["course", "order"]
        unique_together = ["course", "order"]
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Attachment(models.Model):
    """Прикреплённый файл к уроку (шпаргалка, PDF и т.п.)."""

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Урок",
    )
    title = models.CharField(max_length=255, verbose_name="Название файла")
    file = models.FileField(upload_to="attachments/", verbose_name="Файл")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")

    class Meta:
        ordering = ["order"]
        verbose_name = "Прикреплённый файл"
        verbose_name_plural = "Прикреплённые файлы"

    def __str__(self):
        return f"{self.title} ({self.lesson.title})"


class Test(models.Model):
    """Тест, привязанный к уроку (один тест на урок)."""

    lesson = models.OneToOneField(
        Lesson,
        on_delete=models.CASCADE,
        related_name="test",
        verbose_name="Урок",
    )
    title = models.CharField(max_length=255, blank=True, verbose_name="Название теста")
    description = models.TextField(blank=True, verbose_name="Описание")

    class Meta:
        verbose_name = "Тест"
        verbose_name_plural = "Тесты"
        ordering = ["lesson__order"]

    def __str__(self):
        return self.title or f"Тест к уроку {self.lesson.title}"


class Question(models.Model):
    """Вопрос теста."""

    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="questions",
        verbose_name="Тест",
    )
    text = models.CharField(max_length=255, verbose_name="Текст вопроса")
    order = models.PositiveIntegerField(verbose_name="Порядок")

    class Meta:
        ordering = ["order"]
        verbose_name = "Вопрос"
        verbose_name_plural = "Вопросы"

    def __str__(self):
        return self.text


class Choice(models.Model):
    """Вариант ответа на вопрос."""

    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="choices",
        verbose_name="Вопрос",
    )
    text = models.CharField(max_length=255, verbose_name="Текст ответа")
    is_correct = models.BooleanField(default=False, verbose_name="Правильный?")

    class Meta:
        verbose_name = "Вариант ответа"
        verbose_name_plural = "Варианты ответов"
        ordering = ["question", "id"]

    def __str__(self):
        return f"{self.text} {'✓' if self.is_correct else ''}"


class StudentTestAttempt(models.Model):
    """Попытка прохождения теста студентом."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="test_attempts",
        verbose_name="Студент",
    )
    test = models.ForeignKey(
        Test,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name="Тест",
    )
    score = models.PositiveSmallIntegerField(
        verbose_name="Результат (%)",
        help_text="Процент правильных ответов",
    )
    passed_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата прохождения")

    class Meta:
        verbose_name = "Попытка теста"
        verbose_name_plural = "Попытки тестов"

    def __str__(self):
        return f"{self.user.username} - {self.test.title} ({self.score}%)"


class Enrollment(models.Model):
    """Запись пользователя на курс (покупка / предоставление доступа)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Пользователь",
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Курс",
    )
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата записи")

    class Meta:
        unique_together = ["user", "course"]
        verbose_name = "Запись на курс"
        verbose_name_plural = "Запись на курсы"

    def __str__(self):
        return f"{self.user.username} → {self.course.title} ({self.enrolled_at})"
