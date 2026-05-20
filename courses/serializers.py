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

        if request is not None and request.user.is_authenticated and request.user.role in ["admin", "teacher"]:  # type: ignore[union-attr]
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
            instance.choices.exclude(id__in=existing_ids).delete()

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
            instance.questions.exclude(id__in=existing_question_ids).delete()

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
