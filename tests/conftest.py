import pytest
from rest_framework.test import APIClient

from courses.models import Choice, Course, Enrollment, Lesson, Question, Test
from users.models import User


@pytest.fixture
def api_client():
    """Не аутентифицированный клиент."""
    return APIClient()


@pytest.fixture
def admin_user() -> User:
    """Администратор."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass",
        role="admin",
    )


@pytest.fixture
def teacher_user() -> User:
    """Преподаватель."""
    return User.objects.create_user(
        username="teacher",
        email="teacher@example.com",
        password="teacherpass",
        role="teacher",
    )


@pytest.fixture
def another_teacher() -> User:
    """Другой преподаватель для проверки изоляции."""
    return User.objects.create_user(
        username="teacher2",
        email="teacher2@example.com",
        password="teacherpass2",
        role="teacher",
    )


@pytest.fixture
def client_user() -> User:
    """Обычный клиент."""
    return User.objects.create_user(
        username="client",
        email="client@example.com",
        password="clientpass",
        role="client",
    )


@pytest.fixture
def course(teacher_user: User) -> Course:
    """Опубликованный курс первого преподавателя."""
    return Course.objects.create(
        owner=teacher_user,
        title="Test Course",
        description="A test course",
        price=100.00,
        is_published=True,
    )


@pytest.fixture
def hidden_course(teacher_user: User) -> Course:
    """Неопубликованный курс."""
    return Course.objects.create(
        owner=teacher_user,
        title="Hidden Course",
        price=50.00,
        is_published=False,
    )


@pytest.fixture
def lesson(course: Course) -> Lesson:
    """Урок в опубликованном курсе."""
    return Lesson.objects.create(
        course=course,
        title="Test Lesson",
        content="Lesson content",
        order=1,
    )


@pytest.fixture
def test_obj(lesson: Lesson) -> Test:
    """Тест с одним вопросом и двумя вариантами ответа."""
    test = Test.objects.create(lesson=lesson, title="Sample Test")
    question = Question.objects.create(test=test, text="2+2?", order=1)
    Choice.objects.create(question=question, text="4", is_correct=True)
    Choice.objects.create(question=question, text="5", is_correct=False)

    return test


@pytest.fixture
def enrollment(client_user: User, course: Course) -> Enrollment:
    """Запись клиента на курс."""
    return Enrollment.objects.create(user=client_user, course=course)
