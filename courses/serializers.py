from typing import cast

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from courses.models import Attachment, Choice, Course, CourseCategory, Enrollment, Lesson, Question, Test
from users.models import User


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

    @extend_schema_field(ChoiceSerializer(many=True))
    def get_choices(self, obj):
        """
        Для администратора или преподавателя-владельца возвращает полные данные о вариантах ответа
        (включая флаг правильности). Для студента - только id и текст варианта.
        """
        request = self.context.get("request")

        if (
            request is not None
            and request.user.is_authenticated  # type: ignore[union-attr]
            and request.user.role in ["admin", "teacher"]  # type: ignore[union-attr]
        ):
            return ChoiceSerializer(obj.choices.all(), many=True).data

        return [
            {
                "id": c.id,
                "text": c.text,
            }
            for c in obj.choices.all()
        ]


class TestSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для теста (все поля)."""

    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = "__all__"


class LessonDetailSerializer(serializers.ModelSerializer):
    """Полный сериализатор урока со списком вложений."""

    attachments = AttachmentSerializer(many=True, read_only=True)
    test = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = "__all__"

    @extend_schema_field(TestSerializer(allow_null=True))
    def get_test(self, obj):
        """Возвращает данные теста, связанного с уроком, если он существует."""

        if hasattr(obj, "test"):
            return TestSerializer(obj.test, context=self.context).data

        return None


class CourseCategorySerializer(serializers.ModelSerializer):
    """Сериализатор категории курса (только чтение)."""

    class Meta:
        model = CourseCategory
        fields = ["id", "title", "slug", "space_type", "description"]


class CourseListSerializer(serializers.ModelSerializer):
    """Краткая информация о курсе для публичного списка."""

    owner = serializers.CharField(source="owner.username", read_only=True)
    category = CourseCategorySerializer(read_only=True)
    required_course_ids = serializers.SerializerMethodField()
    is_accessible = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ["id", "title", "description", "price", "owner", "category", "required_course_ids", "is_accessible"]

    @staticmethod
    def get_required_course_ids(obj):
        """Возвращает список идентификаторов курсов-пререквизитов для данного курса."""
        return list(obj.required_courses.values_list("id", flat=True))

    def get_is_accessible(self, obj):
        """
        Определяет, доступен ли курс для текущего пользователя:
        - пользователь аутентифицирован
        - все обязательные курсы (пререквизиты) завершены (is_completed=True)
        - или обязательных курсов нет
        """
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:  # type: ignore[union-attr]
            return False

        user = request.user  # type: ignore[union-attr]

        if not obj.required_courses.exists():
            return True

        required_ids = obj.required_courses.values_list("id", flat=True)
        completed_ids = Enrollment.objects.filter(
            user=user, course_id__in=required_ids, is_completed=True
        ).values_list("course_id", flat=True)

        return set(required_ids) == set(completed_ids)


class CourseDetailSerializer(serializers.ModelSerializer):
    """Полная информация о курсе со списком уроков (кратко)."""

    lessons = LessonListSerializer(many=True, read_only=True)
    category = CourseCategorySerializer(read_only=True)
    required_course_ids = serializers.SerializerMethodField()
    is_accessible = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = "__all__"
        extra_kwargs = {"owner": {"read_only": True}}

    @staticmethod
    def get_required_course_ids(obj):
        """Возвращает список идентификаторов курсов-пререквизитов для данного курса."""
        return list(obj.required_courses.values_list("id", flat=True))

    def get_is_accessible(self, obj):
        """
        Определяет, доступен ли курс для текущего пользователя:
        - пользователь аутентифицирован
        - все обязательные курсы (пререквизиты) завершены (is_completed=True)
        - или обязательных курсов нет
        """
        request = self.context.get("request")

        if not request or not request.user.is_authenticated:  # type: ignore[union-attr]
            return False

        user = request.user  # type: ignore[union-attr]

        if not obj.required_courses.exists():
            return True

        required_ids = obj.required_courses.values_list("id", flat=True)
        completed_ids = Enrollment.objects.filter(
            user=user, course_id__in=required_ids, is_completed=True
        ).values_list("course_id", flat=True)

        return set(required_ids) == set(completed_ids)


class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления курса (только основные поля)."""

    class Meta:
        model = Course
        fields = ["title", "description", "price", "is_published", "category", "required_courses"]


class TestSubmitSerializer(serializers.Serializer):
    """Сериализатор для отправки ответов студента на тест."""

    answers = serializers.DictField(
        child=serializers.ListField(child=serializers.IntegerField()),
        help_text="Словарь: ключ - id вопроса, значение - список выбранных id ответов.",
    )


class ChoiceCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/обновления варианта ответа (используется внутри QuestionCreateUpdateSerializer)."""

    class Meta:
        model = Choice
        fields = ["id", "text", "is_correct"]
        extra_kwargs = {"id": {"read_only": False, "required": False}}


class QuestionCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/обновления вопроса с вложенными вариантами ответов."""

    choices = ChoiceCreateUpdateSerializer(many=True)

    class Meta:
        model = Question
        fields = ["id", "text", "order", "choices"]
        extra_kwargs = {"id": {"read_only": False, "required": False}}

    def create(self, validated_data):
        """
        Создаёт вопрос и все связанные с ним варианты ответов.
        Принимает данные: text, order, choices (список словарей с полями Choice).
        """
        choices_data = validated_data.pop("choices")
        question = Question.objects.create(**validated_data)

        for choice_data in choices_data:
            Choice.objects.create(question=question, **choice_data)

        return question

    def update(self, instance, validated_data):
        """
        Обновляет вопрос и управляет вариантами ответов:
        - удаляет варианты, отсутствующие в запросе
        - обновляет существующие варианты (по id)
        - создаёт новые варианты (без id)
        """
        choices_data = validated_data.pop("choices", None)
        instance.text = validated_data.get("text", instance.text)
        instance.order = validated_data.get("order", instance.order)
        instance.save()

        if choices_data is not None:
            existing_ids = [c.get("id") for c in choices_data if c.get("id")]
            instance.choices.exclude(id__in=existing_ids).delete()  # type: ignore[union-attr]

            for choice_data in choices_data:
                choice_id = choice_data.get("id")

                if choice_id:
                    choice = Choice.objects.get(id=choice_id, question=instance)
                    choice.text = choice_data.get("text", choice.text)
                    choice.is_correct = choice_data.get("is_correct", choice.is_correct)
                else:
                    Choice.objects.create(question=instance, **choice_data)

        return instance


class TestCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/обновления теста с вложенными вопросами и вариантами ответов."""

    questions = QuestionCreateUpdateSerializer(many=True)

    class Meta:
        model = Test
        fields = ["id", "lesson", "title", "description", "questions"]

    def create(self, validated_data):
        """
        Создаёт тест, все вопросы и варианты ответов.
        Принимает данные: lesson, title, description, questions (список словарей с вложенными choices).
        """
        questions_data = validated_data.pop("questions")
        test = Test.objects.create(**validated_data)

        for question_data in questions_data:
            choices_data = question_data.pop("choices")
            question = Question.objects.create(test=test, **question_data)

            for choice_data in choices_data:
                Choice.objects.create(question=question, **choice_data)

        return test

    def update(self, instance, validated_data):
        """
        Обновляет тест и полностью синхронизирует структуру вопросов/ответов:
        - удаляет вопросы, отсутствующие в запросе
        - обновляет существующие вопросы и их варианты (по id)
        - создаёт новые вопросы/варианты
        - удаляет варианты, отсутствующие в обновлённом вопросе
        """
        questions_data = validated_data.pop("questions", None)
        instance.title = validated_data.get("title", instance.title)
        instance.description = validated_data.get("description", instance.description)
        instance.save()

        if questions_data is not None:
            existing_question_ids = [q.get("id") for q in questions_data if q.get("id")]
            instance.questions.exclude(id__in=existing_question_ids).delete()  # type: ignore[union-attr]

            for question_data in questions_data:
                question_id = question_data.get("id")
                choices_data = question_data.pop("choices", [])

                if question_id:
                    question = Question.objects.get(id=question_id, test=instance)
                    question.text = question_data.get("text", question.text)
                    question.order = question_data.get("order", question.order)
                    question.save()
                else:
                    question = Question.objects.create(test=instance, **question_data)

                existing_choices_ids = [c.get("id") for c in choices_data if c.get("id")]
                question.choices.exclude(id__in=existing_choices_ids).delete()  # type: ignore[union-attr]

                for choice_data in choices_data:
                    choice_id = choice_data.get("id")

                    if choice_id:
                        choice = Choice.objects.get(id=choice_id, question=question)
                        choice.text = choice_data.get("text", choice.text)
                        choice.is_correct = choice_data.get("is_correct", choice.is_correct)
                        choice.save()
                    else:
                        Choice.objects.create(question=question, **choice_data)

        return instance


class LessonCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания/обновления урока преподавателем."""

    class Meta:
        model = Lesson
        fields = ["id", "course", "title", "content", "video_url", "video_file", "order"]
        extra_kwargs = {
            "id": {"read_only": True},
            "course": {"required": True},
        }

    def update(self, instance, validated_data):
        """Обновляет урок. Проверяет, что преподаватель не может перенести урок в чужой курс."""

        request = self.context.get("request")

        if request is not None and request.user.is_authenticated:  # type: ignore[union-attr]
            user = cast(User, request.user)  # type: ignore[union-attr]
            new_course = validated_data.get("course", instance.course)

            if user.role != "admin" and new_course.owner != user:
                raise serializers.ValidationError({"course": "Вы можете назначать урок только своему курсу."})

        instance.course = validated_data.get("course", instance.course)
        instance.title = validated_data.get("title", instance.title)
        instance.content = validated_data.get("content", instance.content)
        instance.video_url = validated_data.get("video_url", instance.video_url)
        instance.video_file = validated_data.get("video_file", instance.video_file)
        instance.order = validated_data.get("order", instance.order)
        instance.save()

        return instance


class AttachmentCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для загрузки и обновления прикреплённых файлов."""

    class Meta:
        model = Attachment
        fields = ["id", "lesson", "title", "file", "order"]
        extra_kwargs = {
            "id": {"read_only": True},
            "lesson": {"required": True},
            "file": {"required": True},
        }

    def update(self, instance, validated_data):
        """
        Обновляет прикреплённый файл. Проверяет, что преподаватель не может перенести вложения в урок чужого курса.
        """
        request = self.context.get("request")

        if request is not None and request.user.is_authenticated:  # type: ignore[union-attr]
            user = cast(User, request.user)  # type: ignore[union-attr]
            new_lesson = validated_data.get("lesson", instance.lesson)

            if user.role != "admin" and new_lesson.course.owner != user:
                raise serializers.ValidationError(
                    {"lesson": "Вы можете прикреплять файлы только к уроку из своего курса."}
                )

        instance.lesson = validated_data.get("lesson", instance.lesson)
        instance.title = validated_data.get("title", instance.title)
        instance.file = validated_data.get("file", instance.file)
        instance.order = validated_data.get("order", instance.order)
        instance.save()

        return instance


class EnrollmentSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения и создания записи на курс."""

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Enrollment
        fields = ["id", "user", "course", "enrolled_at", "is_completed"]
        read_only_fields = ["id", "enrolled_at", "is_completed"]

    def validate_course(self, value):
        """
        Проверяет, что курс опубликован (если пользователь не администратор).
        Администратор может записываться на любые курсы, включая неопубликованные.
        """
        user = self.context["request"].user

        if not value.is_published and user.role != "admin":
            raise serializers.ValidationError("Нельзя записаться на неопубликованный курс.")

        return value
