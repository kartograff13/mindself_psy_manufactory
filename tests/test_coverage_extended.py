from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from consultations.models import (
    ConsultationRequest,
    ConsultationService,
    Supervision,
    SupervisionRequest,
    TherapyRequest,
    TherapySession,
)
from courses.models import Attachment, Course, CourseCategory, Enrollment, Lesson, Test
from users.models import User


@pytest.mark.django_db
def test_filter_courses_by_category(api_client):
    """Курсы фильтруются по параметру category (slug)."""
    cat1 = CourseCategory.objects.create(title="Family", slug="family", space_type="family")
    cat2 = CourseCategory.objects.create(title="Academy", slug="academy", space_type="academy")
    teacher = User.objects.create_user(
        username="teacher_cat", email="teacher_cat@example.com", password="pass", role="teacher"
    )
    Course.objects.create(owner=teacher, title="Family Course", price=10, is_published=True, category=cat1)
    Course.objects.create(owner=teacher, title="Academy Course", price=20, is_published=True, category=cat2)

    response = api_client.get("/api/courses/?category=family")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["title"] == "Family Course"


@pytest.mark.django_db
def test_course_list_serializer_is_accessible_field(api_client, client_user):
    """Поле is_accessible правильно вычисляется для студента с выполненными пререквизитами."""
    teacher = User.objects.create_user(
        username="teacher_acc", email="teacher_acc@example.com", password="pass", role="teacher"
    )

    required = Course.objects.create(owner=teacher, title="Required", price=0, is_published=True)
    course = Course.objects.create(owner=teacher, title="Advanced", price=10, is_published=True)
    course.required_courses.add(required)

    Enrollment.objects.create(user=client_user, course=required, is_completed=True)
    api_client.force_authenticate(user=client_user)

    response_detail = api_client.get(f"/api/courses/{course.id}/")

    assert response_detail.status_code == 200
    assert response_detail.data["is_accessible"] is True

    required.refresh_from_db()
    Enrollment.objects.filter(user=client_user, course=required).update(is_completed=False)
    response_detail2 = api_client.get(f"/api/courses/{course.id}/")

    assert response_detail2.status_code == 200
    assert response_detail2.data["is_accessible"] is False


@pytest.mark.django_db
def test_create_course_with_required_courses(api_client, teacher_user):
    """Преподаватель может создать курс с указанием обязательных курсов."""
    api_client.force_authenticate(user=teacher_user)
    required = Course.objects.create(owner=teacher_user, title="Req", price=0, is_published=True)
    response = api_client.post(
        "/api/courses/",
        {
            "title": "New Course with req",
            "description": "Desc",
            "price": "50.00",
            "is_published": False,
            "category": None,
            "required_courses": [required.id],
        },
        format="json",
    )

    assert response.status_code == 201

    course = Course.objects.get(title="New Course with req")

    assert list(course.required_courses.values_list("id", flat=True)) == [required.id]


@pytest.mark.django_db
def test_supervision_list_public(api_client):
    """Список супервизий доступен без авторизации."""
    psychologist = User.objects.create_user(
        username="psych_super", email="psych_super@example.com", password="pass", role="teacher"
    )
    Supervision.objects.create(
        psychologist=psychologist,
        title="Supervision 1",
        supervision_type="individual",
        start_datetime=timezone.now() + timedelta(days=1),
        end_datetime=timezone.now() + timedelta(days=1, hours=1),
        price=500.00,
        max_participants=1,
    )
    response = api_client.get("/api/supervisions/")

    assert response.status_code == 200
    assert len(response.data) == 1


@pytest.mark.django_db
def test_supervision_request_list_teacher(api_client, teacher_user):
    """Психолог видит все заявки на супервизию."""
    psychologist = User.objects.create_user(
        username="psych_super2", email="psych_super2@example.com", password="pass", role="teacher"
    )
    supervision = Supervision.objects.create(
        psychologist=psychologist,
        title="Supervision 2",
        supervision_type="individual",
        start_datetime=timezone.now() + timedelta(days=2),
        end_datetime=timezone.now() + timedelta(days=2, hours=1),
        price=300.00,
        max_participants=1,
    )
    SupervisionRequest.objects.create(
        supervision=supervision, name="Client Name", phone="+79991112233", email="client@example.com"
    )
    api_client.force_authenticate(user=teacher_user)
    response = api_client.get("/api/supervision-requests/")

    assert response.status_code == 200
    assert len(response.data) == 1


@pytest.mark.django_db
def test_supervision_request_list_client(api_client, client_user):
    """Обычный пользователь видит только свои заявки."""
    psychologist = User.objects.create_user(
        username="psych3", email="psych3@example.com", password="pass", role="teacher"
    )
    supervision = Supervision.objects.create(
        psychologist=psychologist,
        title="Supervision 3",
        supervision_type="individual",
        start_datetime=timezone.now() + timedelta(days=3),
        end_datetime=timezone.now() + timedelta(days=3, hours=1),
        price=400.00,
        max_participants=1,
    )
    SupervisionRequest.objects.create(supervision=supervision, name="Other", phone="+79990000000")
    api_client.force_authenticate(user=client_user)
    response = api_client.get("/api/supervision-requests/")

    assert response.status_code == 200
    assert len(response.data) == 0


@pytest.mark.django_db
def test_therapy_session_list_public(api_client):
    """Список терапевтических сессий доступен без авторизации."""
    psychologist = User.objects.create_user(
        username="psych_therapy", email="psych_therapy@example.com", password="pass", role="teacher"
    )
    TherapySession.objects.create(
        psychologist=psychologist,
        title="Therapy 1",
        start_datetime=timezone.now() + timedelta(days=1),
        end_datetime=timezone.now() + timedelta(days=1, hours=1),
        price=1000.00,
    )
    response = api_client.get("/api/therapy-sessions/")

    assert response.status_code == 200
    assert len(response.data) == 1


@pytest.mark.django_db
def test_therapy_request_update_status_teacher(api_client, teacher_user):
    """Психолог может изменить статус заявки на терапию."""
    psychologist = User.objects.create_user(
        username="psych_therapy2", email="psych_therapy2@example.com", password="pass", role="teacher"
    )
    session = TherapySession.objects.create(
        psychologist=psychologist,
        title="Therapy 2",
        start_datetime=timezone.now() + timedelta(days=2),
        end_datetime=timezone.now() + timedelta(days=2, hours=1),
        price=800.00,
    )
    req = TherapyRequest.objects.create(session=session, name="Patient", phone="+79991234567", status="new")
    api_client.force_authenticate(user=teacher_user)
    response = api_client.patch(f"/api/therapy-requests/{req.id}/", {"status": "processed"})

    assert response.status_code == 200

    req.refresh_from_db()

    assert req.status == "processed"


@pytest.mark.django_db
def test_dashboard_access(admin_user, client):
    """Администратор может открыть админку."""
    client.login(username="admin", password="adminpass")
    response = client.get("/admin/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_register_forbidden_username(api_client):
    """Регистрация с запрещённым именем отклоняется."""
    response = api_client.post(
        "/api/auth/register/",
        {"username": "admin", "email": "forbidden@example.com", "password": "Str0ngPass1", "password2": "Str0ngPass1"},
    )

    assert response.status_code == 400
    assert "username" in response.data


@pytest.mark.django_db
def test_supervision_create_by_client_forbidden(api_client, client_user):
    """Клиент не может создать супервизию."""
    api_client.force_authenticate(user=client_user)
    response = api_client.post(
        "/api/supervisions/",
        {
            "title": "Test",
            "supervision_type": "individual",
            "start_datetime": timezone.now() + timedelta(days=1),
            "end_datetime": timezone.now() + timedelta(days=1, hours=1),
            "price": 100.00,
            "max_participants": 1,
            "status": "open",
        },
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_therapy_session_create_by_client_forbidden(api_client, client_user):
    """Клиент не может создать терапевтическую сессию."""
    api_client.force_authenticate(user=client_user)
    response = api_client.post(
        "/api/therapy-sessions/",
        {
            "title": "Therapy",
            "start_datetime": timezone.now() + timedelta(days=1),
            "end_datetime": timezone.now() + timedelta(days=1, hours=1),
            "price": 200.00,
        },
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_supervision_request_update_status_teacher(api_client, teacher_user):
    """Психолог может изменить статус заявки на супервизию."""
    psychologist = User.objects.create_user(
        username="psych_super3", email="psych_super3@example.com", password="pass", role="teacher"
    )
    supervision = Supervision.objects.create(
        psychologist=psychologist,
        title="Supervision X",
        supervision_type="individual",
        start_datetime=timezone.now() + timedelta(days=1),
        end_datetime=timezone.now() + timedelta(days=1, hours=1),
        price=200.00,
        max_participants=1,
    )
    req = SupervisionRequest.objects.create(supervision=supervision, name="Client", phone="+79991234567")
    api_client.force_authenticate(user=teacher_user)
    response = api_client.patch(f"/api/supervision-requests/{req.id}/", {"status": "processed"})

    assert response.status_code == 200

    req.refresh_from_db()

    assert req.status == "processed"


@pytest.mark.django_db
def test_consultation_service_create_by_admin(api_client, admin_user):
    """Администратор может создать услугу консультации."""
    api_client.force_authenticate(user=admin_user)
    response = api_client.post(
        "/api/services/", {"name": "New Service", "description": "Desc", "price": 150.00, "is_active": True}
    )

    assert response.status_code == 201
    assert ConsultationService.objects.filter(name="New Service").exists()


@pytest.mark.django_db
def test_consultation_request_list_teacher(api_client, teacher_user):
    """Психолог видит все заявки на консультации."""
    service = ConsultationService.objects.create(name="Service1", is_active=True)
    ConsultationRequest.objects.create(service=service, name="Client", phone="+79991112233")
    api_client.force_authenticate(user=teacher_user)
    response = api_client.get("/api/requests/")

    assert response.status_code == 200
    assert len(response.data) == 1


@pytest.mark.django_db
def test_consultation_request_list_client(api_client, client_user):
    """Обычный пользователь видит только свои заявки."""
    service = ConsultationService.objects.create(name="Service2", is_active=True)
    ConsultationRequest.objects.create(service=service, name="Other", phone="+79990000000")
    api_client.force_authenticate(user=client_user)
    response = api_client.get("/api/requests/")

    assert response.status_code == 200
    assert len(response.data) == 0


@pytest.mark.django_db
def test_consultation_request_update_status_teacher(api_client, teacher_user):
    """Психолог может изменить статус заявки на консультацию."""
    service = ConsultationService.objects.create(name="Service3", is_active=True)
    req = ConsultationRequest.objects.create(service=service, name="Client", phone="+79991234567")
    api_client.force_authenticate(user=teacher_user)
    response = api_client.patch(f"/api/requests/{req.id}/", {"status": "processed"})

    assert response.status_code == 200

    req.refresh_from_db()

    assert req.status == "processed"


@pytest.mark.django_db
def test_attachment_retrieve_by_enrolled(api_client, client_user, lesson, enrollment, test_obj):
    """Студент может получить вложение, если записан на курс."""
    file = SimpleUploadedFile("test.txt", b"content")
    attachment = Attachment.objects.create(lesson=lesson, title="Att", file=file, order=1)
    api_client.force_authenticate(user=client_user)
    response = api_client.get(f"/api/attachments/{attachment.id}/")

    assert response.status_code == 200
    assert response.data["title"] == "Att"


@pytest.mark.django_db
def test_lesson_detail_contains_test(api_client, client_user, enrollment, lesson, test_obj):
    """Детальный запрос урока возвращает привязанный тест."""
    api_client.force_authenticate(user=client_user)
    response = api_client.get(f"/api/lessons/{lesson.id}/")

    assert response.status_code == 200
    assert "test" in response.data
    assert response.data["test"] is not None
    assert response.data["test"]["title"] == "Sample Test"


@pytest.mark.django_db
def test_course_detail_contains_lessons(api_client, client_user, course, lesson):
    """Детальный запрос курса содержит список уроков."""
    api_client.force_authenticate(user=client_user)
    response = api_client.get(f"/api/courses/{course.id}/")

    assert response.status_code == 200
    assert len(response.data["lessons"]) == 1
    assert response.data["lessons"][0]["title"] == "Test Lesson"


@pytest.mark.django_db
def test_teacher_test_viewset_list(api_client, teacher_user, test_obj):
    """Преподаватель видит свои тесты через teacher/tests."""
    api_client.force_authenticate(user=teacher_user)
    response = api_client.get("/api/teacher/tests/")

    assert response.status_code == 200
    assert len(response.data) == 1


@pytest.mark.django_db
def test_teacher_test_viewset_update(api_client, teacher_user, test_obj):
    """Преподаватель может обновить тест."""
    api_client.force_authenticate(user=teacher_user)
    response = api_client.patch(
        f"/api/teacher/tests/{test_obj.id}/",
        {
            "title": "Updated Test",
            "questions": [
                {
                    "id": test_obj.questions.first().id,
                    "text": "Updated Q?",
                    "order": 1,
                    "choices": [
                        {"id": test_obj.questions.first().choices.first().id, "text": "Yes", "is_correct": True},
                        {"id": test_obj.questions.first().choices.last().id, "text": "No", "is_correct": False},
                    ],
                }
            ],
        },
        format="json",
    )

    assert response.status_code == 200

    test_obj.refresh_from_db()

    assert test_obj.title == "Updated Test"


@pytest.mark.django_db
def test_teacher_test_viewset_delete(api_client, teacher_user, test_obj):
    """Преподаватель может удалить тест."""
    api_client.force_authenticate(user=teacher_user)
    response = api_client.delete(f"/api/teacher/tests/{test_obj.id}/")

    assert response.status_code == 204
    assert not Test.objects.filter(id=test_obj.id).exists()


@pytest.mark.django_db
def test_teacher_lesson_viewset_update(api_client, teacher_user, lesson):
    """Преподаватель может обновить урок."""
    api_client.force_authenticate(user=teacher_user)
    response = api_client.patch(
        f"/api/teacher/lessons/{lesson.id}/", {"title": "Updated Lesson", "content": "New content"}
    )

    assert response.status_code == 200

    lesson.refresh_from_db()

    assert lesson.title == "Updated Lesson"


@pytest.mark.django_db
def test_teacher_lesson_viewset_delete(api_client, teacher_user, lesson):
    """Преподаватель может удалить урок."""
    api_client.force_authenticate(user=teacher_user)
    response = api_client.delete(f"/api/teacher/lessons/{lesson.id}/")

    assert response.status_code == 204
    assert not Lesson.objects.filter(id=lesson.id).exists()


@pytest.mark.django_db
def test_teacher_attachment_viewset_create(api_client, teacher_user, lesson):
    """Преподаватель может добавить вложение к уроку."""
    api_client.force_authenticate(user=teacher_user)
    file = SimpleUploadedFile("test.pdf", b"content")
    response = api_client.post(
        "/api/teacher/attachments/",
        {"lesson": lesson.id, "title": "Attachment 1", "file": file, "order": 1},
        format="multipart",
    )

    assert response.status_code == 201
    assert Attachment.objects.filter(lesson=lesson).count() == 1


@pytest.mark.django_db
def test_enrollment_retrieve(api_client, client_user, enrollment):
    """Студент может получить детали своей записи."""
    api_client.force_authenticate(user=client_user)
    response = api_client.get(f"/api/enrollments/{enrollment.id}/")

    assert response.status_code == 200
    assert response.data["course"] == enrollment.course.id
