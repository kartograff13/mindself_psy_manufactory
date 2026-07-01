import pytest
from rest_framework.test import APIRequestFactory

from courses.models import Course, Enrollment, Lesson
from courses.permissions import IsEnrolledOrAdmin, IsOwnerOrAdmin
from users.models import User

factory = APIRequestFactory()


def make_request(method="get", user=None):
    request = factory.generic(method, "/fake-url/")
    request.user = user

    return request


@pytest.mark.django_db
def test_is_owner_or_admin_anonymous():
    """Анонимный пользователь не имеет разрешения на небезопасный метод."""
    perm = IsOwnerOrAdmin()
    request = make_request("post", None)

    assert not perm.has_permission(request, None)


@pytest.mark.django_db
def test_is_owner_or_admin_safe_methods():
    """Безопасные методы разрешены даже для анонимов."""
    perm = IsOwnerOrAdmin()
    request = make_request("get", None)

    assert perm.has_permission(request, None)


@pytest.mark.django_db
def test_is_owner_or_admin_admin():
    """Администратор имеет полный доступ."""
    admin = User.objects.create_superuser(username="admin", email="admin@example.com", password="pass", role="admin")
    request = make_request("post", admin)
    perm = IsOwnerOrAdmin()

    assert perm.has_permission(request, None)


@pytest.mark.django_db
def test_is_owner_or_admin_teacher_owner():
    """Преподаватель-владелец курса имеет доступ к объекту."""
    teacher = User.objects.create_user(
        username="teacher_owner", email="teacher_owner@example.com", password="pass", role="teacher"
    )
    course = Course.objects.create(owner=teacher, title="C", price=10, is_published=True)
    request = make_request("patch", teacher)
    perm = IsOwnerOrAdmin()

    assert perm.has_object_permission(request, None, course)


@pytest.mark.django_db
def test_is_owner_or_admin_teacher_not_owner():
    """Преподаватель не может редактировать чужой курс."""
    teacher1 = User.objects.create_user(
        username="teacher1", email="teacher1@example.com", password="pass", role="teacher"
    )
    teacher2 = User.objects.create_user(
        username="teacher2", email="teacher2@example.com", password="pass", role="teacher"
    )
    course = Course.objects.create(owner=teacher2, title="C", price=10, is_published=True)
    request = make_request("patch", teacher1)
    perm = IsOwnerOrAdmin()

    assert not perm.has_object_permission(request, None, course)


@pytest.mark.django_db
def test_is_enrolled_or_admin_authenticated():
    """Аутентифицированный пользователь имеет доступ на уровне has_permission."""
    user = User.objects.create_user(username="student", email="student@example.com", password="pass", role="client")
    request = make_request("get", user)
    perm = IsEnrolledOrAdmin()

    assert perm.has_permission(request, None)


@pytest.mark.django_db
def test_is_enrolled_or_admin_enrolled_student():
    """Зачисленный студент имеет доступ к уроку."""
    student = User.objects.create_user(
        username="enrolled_student", email="enrolled@example.com", password="pass", role="client"
    )
    teacher = User.objects.create_user(
        username="teacher_enroll", email="teacher_enroll@example.com", password="pass", role="teacher"
    )
    course = Course.objects.create(owner=teacher, title="C", price=10, is_published=True)
    lesson = Lesson.objects.create(course=course, title="L", order=1)
    Enrollment.objects.create(user=student, course=course)
    request = make_request("get", student)
    perm = IsEnrolledOrAdmin()

    assert perm.has_object_permission(request, None, lesson)


@pytest.mark.django_db
def test_is_enrolled_or_admin_not_enrolled_student():
    """Незачисленный студент не имеет доступа к уроку."""
    student = User.objects.create_user(
        username="not_enrolled", email="not_enrolled@example.com", password="pass", role="client"
    )
    teacher = User.objects.create_user(
        username="teacher_not_enrolled", email="teacher_not@example.com", password="pass", role="teacher"
    )
    course = Course.objects.create(owner=teacher, title="C", price=10, is_published=True)
    lesson = Lesson.objects.create(course=course, title="L", order=1)
    request = make_request("get", student)
    perm = IsEnrolledOrAdmin()

    assert not perm.has_object_permission(request, None, lesson)


@pytest.mark.django_db
def test_is_enrolled_or_admin_teacher_owner():
    """Преподаватель-владелец курса имеет доступ к уроку."""
    teacher = User.objects.create_user(
        username="teacher_owner2", email="teacher_owner2@example.com", password="pass", role="teacher"
    )
    course = Course.objects.create(owner=teacher, title="C", price=10, is_published=True)
    lesson = Lesson.objects.create(course=course, title="L", order=1)
    request = make_request("get", teacher)
    perm = IsEnrolledOrAdmin()

    assert perm.has_object_permission(request, None, lesson)
