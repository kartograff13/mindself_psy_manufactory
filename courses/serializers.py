from rest_framework import serializers

from courses.models import Attachment, Choice, Course, Lesson, Question, Test


class AttachmentSerializer(serializers.ModelSerializer):
    """Сериализатор для вложений (файлов, ссылок) урока."""

    class Meta:
        model = Attachment
        fields = "__all__"


class LessonListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка уроков (краткая версия без полного контента)."""

    class Meta:
        model = Lesson
        fields = ["id", "title", "order", "video_url", "video_file"]


class LessonDetailSerializer(serializers.ModelSerializer):
    """Полный сериализатор урока со списком вложений."""

    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Lesson
        fields = "__all__"


class TestSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для теста (все поля)."""

    class Meta:
        model = Test
        fields = "__all__"


class ChoiceSerializer(serializers.ModelSerializer):
    """Сериализатор варианта ответа для вопроса."""

    class Meta:
        model = Choice
        fields = "__all__"


class QuestionSerializer(serializers.ModelSerializer):
    """Сериализатор вопроса с динамическим отображением вариантов ответов в зависимости от роли пользователя."""

    choices = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = ["id", "text", "order", "choices"]

    def get_choices(self, obj):
        """
        Для администратора или преподавателя-владельца возвращает полные данные о вариантах ответа
        (включая флаг правильности). Для студента - только id и текст варианта.
        """
        request = self.context.get("request")

        if request and request.user.role in ["admin", "teacher"]:
            return ChoiceSerializer(obj.choices.all(), many=True).data

        return [
            {
                "id": c.id,
                "text": c.text,
            }
            for c in obj.choices.all()
        ]


class CourseListSerializer(serializers.ModelSerializer):
    """Краткая информация о курсе для публичного списка."""

    class Meta:
        model = Course
        fields = ["id", "title", "description", "price", "owner"]
        extra_kwargs = {"owner": {"source": "owner.username", "read_only": True}}


class CourseDetailSerializer(serializers.ModelSerializer):
    """Полная информация о курсе со списком уроков (кратко)."""

    lessons = LessonListSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = "__all__"
        extra_kwargs = {"owner": {"read_only": True}}


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления курса (только основные поля)."""

    class Meta:
        model = Course
        fields = ["title", "description", "price", "is_published"]


class TestSubmitSerializer(serializers.Serializer):
    """Сериализатор для отправки ответов студента на тест."""

    answers = serializers.DictField(
        child=serializers.ListField(child=serializers.IntegerField()),
        help_text="Словарь: ключ - id вопроса, значение - список выбранных id ответов.",
    )
