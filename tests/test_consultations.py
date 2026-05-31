import pytest

from consultations.models import ConsultationRequest, ConsultationService


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
