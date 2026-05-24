import pytest

from courses.models import Course, Enrollment, Lesson, Test
from users.models import User


@pytest.mark.django_db
def test_register_success(api_client):
    """Проверяет успешную регистрацию нового пользователя с корректными данными."""
    response = api_client.post(
        "/api/auth/register/",
        {"username": "new_user", "email": "new@example.com", "password": "Str0ngPass1", "password2": "Str0ngPass1"},
    )

    assert response.status_code == 201
    assert User.objects.filter(username="new_user").exists()

    user = User.objects.get(username="new_user")

    assert user.role == "client"
    assert user.check_password("Str0ngPass1")


@pytest.mark.django_db
def test_register_weak_password(api_client):
    """Проверяет, что регистрация отклоняется при слабом пароле (короткий или простой)."""
    response = api_client.post(
        "/api/auth/register/", {"username": "weak", "email": "weak@example.com", "password": "123", "password2": "123"}
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_register_duplicate_email(api_client, client_user):
    """Проверяет, что нельзя зарегистрироваться с уже существующим email."""
    response = api_client.post(
        "/api/auth/register/",
        {
            "username": "duplicate",
            "email": "client@example.com",
            "password": "Str0ngPass1",
            "password2": "Str0ngPass1",
        },
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_obtain_token(api_client, client_user):
    """Проверяет получения токена JWT (access и refresh) при правильных учётных данных."""
    response = api_client.post("/api/auth/token/", {"username": "client", "password": "clientpass"})

    assert response.status_code == 200
    assert "access" in response.data
    assert "refresh" in response.data


@pytest.mark.django_db
def test_teacher_create_course(api_client, teacher_user):
    """Проверяет, что преподаватель может создать новый курс."""
    api_client.force_authenticate(user=teacher_user)
    response = api_client.post(
        "/api/courses/", {"title": "New Course", "description": "Desc", "price": "50.00", "is_published": False}
    )

    assert response.status_code == 201
    assert Course.objects.filter(owner=teacher_user, title="New Course").exists()


@pytest.mark.django_db
def test_client_cannot_create_course(api_client, client_user):
    """Проверяет, что обычный клиент (студент) не может создать курс."""
    api_client.force_authenticate(user=client_user)
    response = api_client.post("/api/courses/", {"title": "Hack", "price": "1.00"})

    assert response.status_code == 403


@pytest.mark.django_db
def test_teacher_can_update_own_course(api_client, teacher_user, course):
    """Проверяет, что преподаватель может редактировать свой собственный курс."""
    api_client.force_authenticate(user=teacher_user)
    response = api_client.patch(f"/api/courses/{course.id}/", {"title": "Updated"})

    assert response.status_code == 200

    course.refresh_from_db()

    assert course.title == "Updated"


@pytest.mark.django_db
def test_teacher_cannot_update_other_course(api_client, teacher_user, another_teacher):
    """Проверяет, что преподаватель не может редактировать курс другого преподавателя."""
    other_course = Course.objects.create(owner=another_teacher, title="Other Course", price=10.00, is_published=True)
    api_client.force_authenticate(user=teacher_user)
    response = api_client.patch(f"/api/courses/{other_course.id}/", {"title": "Hacked"})

    assert response.status_code == 403


@pytest.mark.django_db
def test_student_sees_only_published_courses(api_client, client_user, course, hidden_course):
    """Проверяет, что студент видит только опубликованные курсы."""
    api_client.force_authenticate(user=client_user)
    response = api_client.get("/api/courses/")

    assert response.status_code == 200

    titles = [c["title"] for c in response.data]

    assert "Test Course" in titles
    assert "Hidden Course" not in titles


@pytest.mark.django_db
def test_student_can_see_lesson_after_enrollment(api_client, client_user, course, lesson, enrollment):
    """Проверяет, что студент видит урок только после записи на курс."""
    api_client.force_authenticate(user=client_user)
    response = api_client.get("/api/lessons/")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["title"] == "Test Lesson"


@pytest.mark.django_db
def test_student_cannot_see_lesson_without_enrollment(api_client, client_user, course, lesson):
    """Проверяет, что студент не видит урок, если не записан на курс."""
    api_client.force_authenticate(user=client_user)
    response = api_client.get("/api/lessons/")

    assert response.status_code == 200
    assert len(response.data) == 0


@pytest.mark.django_db
def test_teacher_can_create_lesson(api_client, teacher_user, course):
    """Проверяет, что преподаватель может создать урок в своём курсе."""
    api_client.force_authenticate(user=teacher_user)
    response = api_client.post(
        "/api/teacher/lessons/", {"course": course.id, "title": "New Lesson", "content": "Content", "order": 2}
    )

    assert response.status_code == 201
    assert Lesson.objects.filter(course=course, title="New Lesson").exists()


@pytest.mark.django_db
def test_teacher_cannot_create_lesson_in_other_course(api_client, teacher_user, another_teacher):
    """Проверяет, что преподаватель не может создать урок в чужом курсе."""
    other_course = Course.objects.create(owner=another_teacher, title="Other", price=0, is_published=True)
    api_client.force_authenticate(user=teacher_user)
    response = api_client.post(
        "/api/teacher/lessons/", {"course": other_course.id, "title": "Hack Lesson", "order": 1}
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_student_submit_test(api_client, client_user, enrollment, test_obj):
    """Проверяет, что студент может отправить ответы на тест и получить корректный балл."""
    api_client.force_authenticate(user=client_user)
    question = test_obj.questions.first()
    correct_choice = question.choices.get(is_correct=True)
    response = api_client.post(
        f"/api/tests/{test_obj.id}/submit/", {"answers": {str(question.id): [correct_choice.id]}}, format="json"
    )

    assert response.status_code == 200
    assert response.data["score"] == 100
    assert response.data["correct"] == 1
    assert response.data["total"] == 1


@pytest.mark.django_db
def test_student_cannot_submit_without_enrollment(api_client, client_user, test_obj):
    """Проверяет, что студент не может отправить тест, если не записан на соответствующий курс."""
    api_client.force_authenticate(user=client_user)
    response = api_client.post(f"/api/tests/{test_obj.id}/submit/", {"answers": {}}, format="json")
    assert response.status_code == 403


@pytest.mark.django_db
def test_teacher_create_test(api_client, teacher_user, lesson):
    """Проверяет, что преподаватель может создать тест в своём уроке."""
    api_client.force_authenticate(user=teacher_user)
    response = api_client.post(
        "/api/teacher/tests/",
        {
            "lesson": lesson.id,
            "title": "Teacher Test",
            "questions": [
                {
                    "text": "Q1",
                    "order": 1,
                    "choices": [{"text": "Correct", "is_correct": True}, {"text": "Wrong", "is_correct": False}],
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 201
    assert Test.objects.filter(lesson=lesson).count() == 1


@pytest.mark.django_db
def test_teacher_cannot_create_test_in_other_lesson(api_client, teacher_user, another_teacher):
    """Проверяет, что преподаватель не может создать тест в уроке чужого курса."""
    other_course = Course.objects.create(owner=another_teacher, title="Other", price=0, is_published=True)
    other_lesson = Lesson.objects.create(course=other_course, title="Other Lesson", order=1)
    api_client.force_authenticate(user=teacher_user)
    response = api_client.post(
        "/api/teacher/tests/", {"lesson": other_lesson.id, "title": "Hack Test", "questions": []}, format="json"
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_enroll_in_course(api_client, client_user, course):
    """Проверяет, что студент может записаться на опубликованный курс."""
    api_client.force_authenticate(user=client_user)
    response = api_client.post("/api/enrollments/", {"course": course.id})

    assert response.status_code == 201
    assert Enrollment.objects.filter(user=client_user, course=course).exists()


@pytest.mark.django_db
def test_cannot_enroll_twice(api_client, client_user, course, enrollment):
    """Проверяет, что повторная запись на тот же курс запрещена."""
    api_client.force_authenticate(user=client_user)
    response = api_client.post("/api/enrollments/", {"course": course.id})

    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_enroll_in_hidden_course(api_client, client_user, hidden_course):
    """Проверяет, что студент не может записаться на неопубликованный курс."""
    api_client.force_authenticate(user=client_user)
    response = api_client.post("/api/enrollments/", {"course": hidden_course.id})

    assert response.status_code == 400


@pytest.mark.django_db
def test_teacher_can_view_enrollments_for_own_course(api_client, teacher_user, course, enrollment):
    """Проверяет, что преподаватель видит список записей на свой курс."""
    api_client.force_authenticate(user=teacher_user)
    response = api_client.get("/api/enrollments/")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["course"] == course.id


@pytest.mark.django_db
def test_student_can_delete_own_enrollment(api_client, client_user, enrollment):
    """Проверяет, что студент может удалить (отписаться) свою запись на курс."""
    api_client.force_authenticate(user=client_user)
    response = api_client.delete(f"/api/enrollments/{enrollment.id}/")

    assert response.status_code == 204
    assert not Enrollment.objects.filter(id=enrollment.id).exists()


@pytest.mark.django_db
def test_anonymous_user_cannot_access_api(api_client):
    """Проверяет, что неаутентифицированный пользователь не имеет доступа к API."""
    response = api_client.get("/api/courses/")

    assert response.status_code == 401

    response = api_client.post("/api/teacher/lessons/", {})

    assert response.status_code == 401


@pytest.mark.django_db
def test_teacher_can_delete_own_course(api_client, teacher_user, course):
    """Проверяет, что преподаватель может удалить свой курс."""
    api_client.force_authenticate(user=teacher_user)
    response = api_client.delete(f"/api/courses/{course.id}/")

    assert response.status_code == 204
    assert not Course.objects.filter(id=course.id).exists()


@pytest.mark.django_db
def test_teacher_cannot_delete_other_course(api_client, teacher_user, another_teacher):
    """Проверяет, что преподаватель не может удалить курс другого преподавателя."""
    other_course = Course.objects.create(owner=another_teacher, title="Other", price=0, is_published=True)
    api_client.force_authenticate(user=teacher_user)
    response = api_client.delete(f"/api/courses/{other_course.id}/")

    assert response.status_code == 403
    assert Course.objects.filter(id=other_course.id).exists()
