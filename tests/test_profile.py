import pytest

from users.models import User


@pytest.fixture
def client_with_phone():
    """Фикстура: создаёт обычного пользователя (client) с телефоном."""
    return User.objects.create_user(
        username="client_with_phone",
        email="client_with_phone@example.com",
        password="clientpass",
        role="client",
        phone="+79991112233",
    )


@pytest.mark.django_db
def test_get_profile(api_client, client_with_phone):
    """Проверяет, что GET /api/auth/profile/ возвращает корректные данные пользователя."""
    api_client.force_authenticate(user=client_with_phone)
    response = api_client.get("/api/auth/profile/")

    assert response.status_code == 200
    assert response.data["username"] == "client_with_phone"
    assert response.data["email"] == "client_with_phone@example.com"
    assert response.data["role"] == "client"
    assert response.data["phone"] == "+79991112233"


@pytest.mark.django_db
def test_update_profile(api_client, client_with_phone):
    """Проверяет, что PATCH /api/auth/profile/ обновляет поля first_name, last_name, bio."""
    api_client.force_authenticate(user=client_with_phone)
    response = api_client.patch("/api/auth/profile/", {"first_name": "John", "last_name": "Doe", "bio": "Hello world"})
    assert response.status_code == 200

    client_with_phone.refresh_from_db()
    assert client_with_phone.first_name == "John"
    assert client_with_phone.last_name == "Doe"
    assert client_with_phone.bio == "Hello world"


@pytest.mark.django_db
def test_change_password(api_client, client_with_phone):
    """Проверяет успешную смену пароля при корректном старом пароле и совпадающем подтверждении."""
    api_client.force_authenticate(user=client_with_phone)
    response = api_client.post(
        "/api/auth/profile/change-password/",
        {"old_password": "clientpass", "new_password": "NewStr0ngPass1", "new_password2": "NewStr0ngPass1"},
    )
    assert response.status_code == 200

    client_with_phone.refresh_from_db()
    assert client_with_phone.check_password("NewStr0ngPass1")


@pytest.mark.django_db
def test_change_password_wrong_old(api_client, client_with_phone):
    """Проверяет, что при неверном старом пароле возвращается ошибка 400."""
    api_client.force_authenticate(user=client_with_phone)
    response = api_client.post(
        "/api/auth/profile/change-password/",
        {"old_password": "wrongpass", "new_password": "NewStr0ngPass1", "new_password2": "NewStr0ngPass1"},
    )

    assert response.status_code == 400
    assert "old_password" in response.data
