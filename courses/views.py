from typing import cast

from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from courses.models import Attachment, Course, Lesson, StudentTestAttempt, Test
from courses.permissions import IsEnrolledOrAdmin, IsOwnerOrAdmin
from courses.serializers import (
    AttachmentSerializer,
    CourseCreateUpdateSerializer,
    CourseDetailSerializer,
    CourseListSerializer,
    LessonDetailSerializer,
    LessonListSerializer,
    TestCreateUpdateSerializer,
    TestSerializer,
    TestSubmitSerializer,
)
from users.models import User


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

        if user.role == "admin":
            return Course.objects.all()
        elif user.role == "teacher":
            return Course.objects.filter(owner=user)

        return Course.objects.filter(is_published=True)


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

        if user.role == "admin":
            return Test.objects.all()

        if user.role == "teacher":
            return Test.objects.filter(lesson__course__owner=user)

        enrolled_courses = Course.objects.filter(enrollments__user=user, is_published=True)
        return Test.objects.filter(lesson__course__in=enrolled_courses)

    @action(detail=True, methods=["post"], url_path="submit")
    def submit(self, request, _pk=None):
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
        Фильтруем queryset тестов в зависимости от роли пользователя:
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
