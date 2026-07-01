from datetime import timedelta

import pytest
from django.utils import timezone

from consultations.models import (
    ConsultationRequest,
    ConsultationService,
    Supervision,
    SupervisionRequest,
    TherapyRequest,
    TherapySession,
)
from users.models import User


@pytest.fixture
def service():
    """Фикстура: создаёт услугу консультации для использования в тестах."""
    return ConsultationService.objects.create(name="Личная консультация", description="Индивидуальная работа")


@pytest.mark.django_db
def test_anonymous_can_create_request(api_client, service):
    """Проверяет, что анонимный пользователь может оставить заявку на консультацию."""
    response = api_client.post(
        "/api/requests/",
        {
            "service": service.id,
            "name": "Иван Петров",
            "phone": "+79991234567",
        },
    )
    assert response.status_code == 201
    assert ConsultationRequest.objects.count() == 1

    req = ConsultationRequest.objects.first()
    assert req.name == "Иван Петров"
    assert req.phone == "+79991234567"
    assert req.user is None


@pytest.mark.django_db
def test_auth_user_auto_fill(api_client, client_user, service):
    """
    Проверяет, что для авторизованного пользователя поля name, phone, email автоматически подставляются из профиля.
    """
    client_user.phone = "+79991112233"
    client_user.save()
    api_client.force_authenticate(user=client_user)
    response = api_client.post("/api/requests/", {"service": service.id})
    assert response.status_code == 201

    req = ConsultationRequest.objects.first()
    assert req.user == client_user
    assert req.name == client_user.get_full_name() or client_user.username
    assert req.phone == client_user.phone


@pytest.mark.django_db
def test_teacher_can_view_requests(api_client, teacher_user, service):
    """Проверяет, что психолог (teacher) видит все заявки."""
    ConsultationRequest.objects.create(service=service, name="Клиент", phone="+79990000000")
    api_client.force_authenticate(user=teacher_user)
    response = api_client.get("/api/requests/")

    assert response.status_code == 200
    assert len(response.data) == 1


@pytest.mark.django_db
def test_client_sees_only_own_requests(api_client, client_user, service):
    """Проверяет, что обычный клиент (client) видит только свои заявки."""
    ConsultationRequest.objects.create(service=service, name="Другой", phone="+79991111111")
    api_client.force_authenticate(user=client_user)
    response = api_client.get("/api/requests/")

    assert response.status_code == 200
    assert len(response.data) == 0


@pytest.mark.django_db
def test_admin_can_update_status(api_client, admin_user, service):
    """Проверяет, что администратор может изменять статус заявки."""
    req = ConsultationRequest.objects.create(service=service, name="Клиент", phone="+79991234567")
    api_client.force_authenticate(user=admin_user)
    response = api_client.patch(f"/api/requests/{req.id}/", {"status": "processed"})
    assert response.status_code == 200

    req.refresh_from_db()
    assert req.status == "processed"


@pytest.mark.django_db
def test_auth_user_must_provide_phone(api_client, client_user, service):
    """Проверяет, что если у авторизованного пользователя не указан телефон, поле phone становится обязательным."""
    client_user.phone = ""
    client_user.save()
    api_client.force_authenticate(user=client_user)
    response = api_client.post("/api/requests/", {"service": service.id})

    assert response.status_code == 400
    assert "phone" in response.data


@pytest.mark.django_db
def test_supervision_request_anonymous(api_client):
    """Анонимный пользователь может создать запрос на супервизию."""
    psychologist = User.objects.create_user(username="psychologist", password="pass", role="teacher")
    supervision = Supervision.objects.create(
        psychologist=psychologist,
        title="Test Supervision",
        supervision_type="individual",
        start_datetime=timezone.now() + timedelta(days=1),
        end_datetime=timezone.now() + timedelta(days=1, hours=1),
        price=500.00,
        max_participants=1,
    )
    response = api_client.post(
        "/api/supervision-requests/",
        {
            "supervision": supervision.id,
            "name": "Иван Петров",
            "phone": "+79991234567",
            "email": "ivan@example.com",
            "comment": "Хочу участвовать",
        },
    )
    assert response.status_code == 201
    assert SupervisionRequest.objects.count() == 1


@pytest.mark.django_db
def test_therapy_request_anonymous(api_client):
    """Анонимный пользователь может создать запрос на терапевтическую сессию."""
    psychologist = User.objects.create_user(username="psychologist2", password="pass", role="teacher")
    session = TherapySession.objects.create(
        psychologist=psychologist,
        title="Therapy Session",
        start_datetime=timezone.now() + timedelta(days=2),
        end_datetime=timezone.now() + timedelta(days=2, hours=1),
        price=1000.00,
    )
    response = api_client.post(
        "/api/therapy-requests/",
        {"session": session.id, "name": "Мария Иванова", "phone": "+79991112233", "comment": "Нужна консультация"},
    )
    assert response.status_code == 201
    assert TherapyRequest.objects.count() == 1
