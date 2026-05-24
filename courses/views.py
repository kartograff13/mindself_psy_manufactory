from typing import cast

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from courses.models import Attachment, Course, Enrollment, Lesson, StudentTestAttempt, Test
from courses.permissions import IsEnrolledOrAdmin, IsOwnerOrAdmin
from courses.serializers import (
    AttachmentCreateUpdateSerializer,
    AttachmentSerializer,
    CourseCreateUpdateSerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    EnrollmentSerializer,
    LessonCreateUpdateSerializer,
    LessonDetailSerializer,
    LessonListSerializer,
    TestCreateUpdateSerializer,
    TestSerializer,
    TestSubmitSerializer,
)
from users.models import User


@extend_schema_view(
    list=extend_schema(
        summary="Список курсов",
        description="Возвращает курсы в зависимости от роли: администратор видит все курсы, "
        "преподаватель - свои, студент = опубликованные",
        responses={200: CourseListSerializer(many=True)},
    ),
    create=extend_schema(
        summary="Создать курс",
        description="Создаёт новый курс (только преподаватель или администратор). Владелец назначается автоматически",
        request=CourseCreateUpdateSerializer,
        responses={201: CourseDetailSerializer},
    ),
    retrieve=extend_schema(
        summary="Детали курса",
        responses={200: CourseDetailSerializer},
    ),
    update=extend_schema(
        summary="Обновить курс полностью",
        request=CourseCreateUpdateSerializer,
        responses={200: CourseDetailSerializer},
    ),
    partial_update=extend_schema(
        summary="Обновить курс частично",
        request=CourseCreateUpdateSerializer,
        responses={200: CourseDetailSerializer},
    ),
    destroy=extend_schema(
        summary="Удалить курс",
        responses={204: None},
    ),
)
class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления курсами.
    Поддерживает все действия (list, create, update, delete).
    Доступ зависит от роли:
    - администратор видит всё
    - преподаватель - свои курсы
    - студент/клиент - только опубликованные
    """

    queryset = Course.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор в зависимости от действия."""

        if self.action == "list":
            return CourseListSerializer
        elif self.action in ["create", "update", "partial_update"]:
            return CourseCreateUpdateSerializer

        return CourseDetailSerializer

    def perform_create(self, serializer):
        """При создании курса автоматически назначает текущего пользователя владельцем."""
        serializer.save(owner=self.request.user)

    def get_queryset(self):
        """
        Фильтрует курсы в зависимости от роли пользователя:
        - admin: все курсы
        - teacher: только свои курсы
        - остальные: только опубликованные курсы
        """
        user = cast(User, self.request.user)

        if self.action in ["list", "create"]:

            if user.role == "admin":
                return Course.objects.all()
            elif user.role == "teacher":
                return Course.objects.filter(owner=user)

            return Course.objects.filter(is_published=True)

        return Course.objects.all()


@extend_schema_view(
    list=extend_schema(summary="Список уроков"),
    retrieve=extend_schema(
        summary="Детали урока",
        parameters=[
            OpenApiParameter("id", type=OpenApiTypes.INT, location=OpenApiParameter.PATH),  # type: ignore[arg-type]
        ],
    ),
)
class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet только для чтения (GET list/retrieve) уроков.
    Доступ имеют администраторы, преподаватели-владельцы и студенты, записанные на соответствующий курс.
    """

    queryset = Lesson.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsEnrolledOrAdmin]

    def get_serializer_class(self):
        """Для списка используется краткий сериализатор, для деталей - полный."""

        if self.action == "list":
            return LessonListSerializer

        return LessonDetailSerializer

    def get_queryset(self):
        """
        Фильтрует уроки в зависимости от роли пользователя:
        - admin: все уроки
        - teacher: уроки своих курсов
        - student: уроки из курсов, на которые записаны (опубликованные)
        """
        user = cast(User, self.request.user)

        if user.role == "admin":
            return Lesson.objects.all()

        if user.role == "teacher":
            return Lesson.objects.filter(course__owner=user)

        enrolled_courses = Course.objects.filter(enrollments__user=user, is_published=True)
        return Lesson.objects.filter(course__in=enrolled_courses)


@extend_schema_view(
    retrieve=extend_schema(
        parameters=[
            OpenApiParameter("id", type=OpenApiTypes.INT, location=OpenApiParameter.PATH),  # type: ignore[arg-type]
        ]
    ),
)
class AttachmentViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet только для чтения вложенных уроков с фильтрацией по доступным курсам."""

    serializer_class = AttachmentSerializer
    permission_classes = [permissions.IsAuthenticated, IsEnrolledOrAdmin]

    def get_queryset(self):
        """
        Фильтрует вложения в зависимости от роли пользователя:
        - admin: все вложения
        - teacher: вложения уроков своих курсов
        - student: вложения уроков из записанных (опубликованных) курсов
        """
        user = cast(User, self.request.user)

        if user.role == "admin":
            return Attachment.objects.all()

        if user.role == "teacher":
            return Attachment.objects.filter(lesson__course__owner=user)

        enrolled_courses = Course.objects.filter(enrollments__user=user, is_published=True)
        return Attachment.objects.filter(lesson__course__in=enrolled_courses)


@extend_schema_view(
    list=extend_schema(summary="Список тестов"),
    retrieve=extend_schema(
        summary="Детали теста",
        parameters=[
            OpenApiParameter("id", type=OpenApiTypes.INT, location=OpenApiParameter.PATH),  # type: ignore[arg-type]
        ],
    ),
)
class TestViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра тестов и отправки ответов (@action submit)."""

    serializer_class = TestSerializer
    permission_classes = [permissions.IsAuthenticated, IsEnrolledOrAdmin]

    def get_queryset(self):
        """
        Фильтрует тесты в зависимости от роли пользователя:
        - admin: все тесты
        - teacher: тесты своих курсов
        - student: тесты из доступных курсов (записан на курс + опубликован)
        """
        user = cast(User, self.request.user)

        if self.action == "list":

            if user.role == "admin":
                return Test.objects.all()

            if user.role == "teacher":
                return Test.objects.filter(lesson__course__owner=user)

            enrolled_courses = Course.objects.filter(enrollments__user=user, is_published=True)
            return Test.objects.filter(lesson__course__in=enrolled_courses)

        return Test.objects.all()

    @extend_schema(
        summary="Отправить ответы на тест",
        description="Принимает словарь answers (id вопросов -> список id выбранных ответов). "
        "Возвращает результат в процентах и количество правильных ответов.",
        request=TestSubmitSerializer,
        responses={200: OpenApiTypes.OBJECT},
        parameters=[
            OpenApiParameter("id", type=OpenApiTypes.INT, location=OpenApiParameter.PATH)  # type: ignore[arg-type]
        ],
        examples=[
            OpenApiExample(
                "Пример запроса",
                value={"answers": {"1": [2, 3], "2": [5]}},
            ),
        ],
    )
    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, pk=None):
        """
        Принимает ответы студентов на тест, вычисляет процент правильных ответов
        и сохраняет результат в модель StudentTestAttempt.
        """
        test = self.get_object()
        serializer = TestSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answers = serializer.validated_data["answers"]
        total_questions = test.questions.count()
        correct_count = 0

        for question in test.questions.all():
            correct_choice = set(question.choices.filter(is_correct=True).values_list("id", flat=True))
            selected = set(answers.get(str(question.id), []))

            if correct_choice == selected:
                correct_count += 1

        score = int(correct_count / total_questions * 100) if total_questions else 0
        StudentTestAttempt.objects.create(user=request.user, test=test, score=score)

        return Response(
            {"score": score, "correct": correct_count, "total": total_questions}, status=status.HTTP_200_OK
        )


@extend_schema_view(
    create=extend_schema(
        summary="Создать тест с вопросами ответами",
        description="Создаёт тест, вложенные вопросы и варианты ответов. "
        "Доступно преподавателю в своём уроке или администратору",
        request=TestCreateUpdateSerializer,
        responses={201: TestCreateUpdateSerializer},
    ),
    update=extend_schema(
        summary="Обновить тест его вопросы/ответы",
        request=TestCreateUpdateSerializer,
    ),
    partial_update=extend_schema(
        summary="Частично обновить тест",
        request=TestCreateUpdateSerializer,
    ),
    destroy=extend_schema(
        summary="Удалить тест",
    ),
)
class TeacherTestViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления тестами (создание, обновление, удаление) преподавателями-владельцами и администраторами.
    Поддерживает вложенное создание/обновление вопросов и ответов.
    """

    queryset = Test.objects.all()
    serializer_class = TestCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Фильтрует queryset тестов в зависимости от роли пользователя:
        - admin: все тесты
        - teacher: только тесты, принадлежащие его курсам (через lesson - course)
        """
        user = cast(User, self.request.user)

        if user.role == "admin":
            return Test.objects.all()

        return Test.objects.filter(lesson__course__owner=user)

    def perform_create(self, serializer):
        """
        Проверяет, что преподаватель создаёт тест в уроке своего собственного курса.
        Администратор может создавать тесты в любых уроках без дополнительной проверки.
        """
        user = cast(User, self.request.user)
        lesson = serializer.validated_data["lesson"]

        if user.role != "admin" and lesson.course.owner != self.request.user:
            raise PermissionDenied("Вы можете создавать тесты только в своих уроках.")

        serializer.save()


@extend_schema_view(
    create=extend_schema(
        summary="Создать урок",
        description="Создаёт урок в курсе. Доступно преподавателю для своего курса или администратору. ",
        request=LessonCreateUpdateSerializer,
        responses={201: LessonDetailSerializer},
    ),
    update=extend_schema(
        summary="Обновить урок",
        request=LessonCreateUpdateSerializer,
    ),
    partial_update=extend_schema(
        summary="Частично обновить урок",
        request=LessonCreateUpdateSerializer,
    ),
    destroy=extend_schema(
        summary="Удалить урок",
    ),
)
class TeacherLessonViewSet(viewsets.ModelViewSet):
    """ViewSet для управления уроками преподавателями-владельцами и администраторами."""

    queryset = Lesson.objects.all()
    serializer_class = LessonCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Фильтрует queryset уроков в зависимости от роли пользователя:
        - admin: все уроки
        - teacher: только уроки, принадлежащие его курсам
        """
        user = cast(User, self.request.user)

        if user.role == "admin":
            return Lesson.objects.all()

        return Lesson.objects.filter(course__owner=user)

    def perform_create(self, serializer):
        """Проверяет, что преподаватель создаёт урок в своём курсе."""

        user = cast(User, self.request.user)
        course = serializer.validated_data["course"]

        if user.role != "admin" and course.owner != user:
            raise PermissionDenied("Вы можете создавать уроки только в своих курсах.")

        serializer.save()


@extend_schema_view(
    create=extend_schema(
        summary="Добавить вложение к уроку",
        description="Загружает файл и прикрепляет к указанному уроку, "
        "Доступно преподавателю для своего урока или администратору. ",
        request=AttachmentCreateUpdateSerializer,
        responses={201: AttachmentCreateUpdateSerializer},
    ),
    update=extend_schema(
        summary="Обновить тест его вопросы/ответы",
        request=AttachmentCreateUpdateSerializer,
    ),
    partial_update=extend_schema(
        summary="Частично обновить тест",
        request=AttachmentCreateUpdateSerializer,
    ),
    destroy=extend_schema(
        summary="Удалить тест",
    ),
)
class TeacherAttachmentViewSet(viewsets.ModelViewSet):
    """ViewSet для управления прикреплёнными файлами преподавателей-владельцев или администраторами."""

    queryset = Attachment.objects.all()
    serializer_class = AttachmentCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        """
        Фильтруем queryset вложений в зависимости от роли пользователя:
        - admin: все вложения
        - teacher: только вложения, принадлежащие его курсам
        """
        user = cast(User, self.request.user)

        if user.role == "admin":
            return Attachment.objects.all()

        return Attachment.objects.filter(lesson__course__owner=user)

    def perform_create(self, serializer):
        """Проверяет, что преподаватель прикрепляет файл к уроку из своего курса."""

        user = cast(User, self.request.user)
        lesson = serializer.validated_data["lesson"]

        if user.role != "admin" and lesson.course.owner != user:
            raise PermissionDenied("Вы можете добавлять файлы только к урокам из своего курса.")

        serializer.save()


@extend_schema_view(
    list=extend_schema(
        summary="Список записей на курсы",
        description="Возвращает записи: администратор видит всё, преподаватели - записи на свои курсы, "
        "студент - свои. ",
    ),
    create=extend_schema(
        summary="Записаться на курс",
        description="Текущий пользователь записывается на опубликованный курс. "
        "Нельзя записаться повторно или на скрытый курс. ",
        request=EnrollmentSerializer,
        responses={201: EnrollmentSerializer},
    ),
    destroy=extend_schema(
        summary="Отчислить с курса",
    ),
)
class EnrollmentViewSet(viewsets.ModelViewSet):
    """ViewSet для управления записями на курс (покупка/отписка)."""

    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Фильтрует записи на курс в зависимости от роли:
        - admin: все записи
        - teacher: записи на свои курсы
        - student: только свои записи
        """
        user = cast(User, self.request.user)

        if user.role == "admin":
            return Enrollment.objects.all()

        if user.role == "teacher":
            return Enrollment.objects.filter(course__owner=user)

        return Enrollment.objects.filter(user=user)

    def perform_create(self, serializer):
        """При создании записи на курс автоматически назначает текущего пользователя."""
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        """
        Разрешает удаление записи на курс в зависимости от роли:
        - admin: удалить все записи
        - teacher: удалить запись только на свой курс
        - student: удалить только свою запись
        """
        user = cast(User, self.request.user)

        if (
            user.role == "admin"
            or instance.user == user  # type: ignore[union-attr]
            or (user.role == "teacher" and instance.course.owner == user)  # type: ignore[union-attr]
        ):
            instance.delete()
        else:
            raise PermissionDenied("У Вас нет прав для удаления этой записи.")
