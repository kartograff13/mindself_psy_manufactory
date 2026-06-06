from phonenumber_field.serializerfields import PhoneNumberField as PhoneNumberSerializerField
from rest_framework import serializers

from consultations.models import ConsultationRequest, ConsultationService


class ConsultationServiceSerializer(serializers.ModelSerializer):
    """Сериализатор для услуги консультации (все поля)."""

    class Meta:
        model = ConsultationService
        fields = "__all__"


class ConsultationRequestCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания заявки на консультацию.
    Автоматически подставляет данные авторизованного пользователя (ФИО, телефон, email),
    если они не указаны явно.
    """

    name = serializers.CharField(required=False)
    phone = PhoneNumberSerializerField(required=False)
    email = serializers.EmailField(required=False)

    class Meta:
        model = ConsultationRequest
        fields = ["service", "name", "phone", "email", "comment"]

    def validate(self, attrs):
        """
        Для авторизованного пользователя:
        - если не указано имя, берёт get_full_name() или username
        - если не указан телефон, берёт из модели пользователя (поле phone)
        - если не указан email, берёт user.email
        Для анонимного пользователя:
        - имя и телефон обязательны
        """
        request = self.context.get("request")

        if request is None:
            return attrs

        user = request.user if request and request.user.is_authenticated else None  # type: ignore[arg-type]

        if user:
            attrs.setdefault("name", user.get_full_name() or user.username)  # type: ignore[arg-type]
            attrs.setdefault("phone", getattr(user, "phone", ""))
            attrs.setdefault("email", user.email)  # type: ignore[arg-type]

        if not attrs.get("name"):
            raise serializers.ValidationError({"name": "Укажите ФИО"})
        if not attrs.get("phone"):
            raise serializers.ValidationError({"phone": "Укажите телефон"})

        return attrs


class ConsultationRequestListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка заявок (только чтение) с дополнительными полями:
    - service_name (название услуги)
    - user_name (имя пользователя, если авторизован)
    """

    service_name = serializers.CharField(source="service.name", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True, allow_null=True)

    class Meta:
        model = ConsultationRequest
        fields = [
            "id",
            "service",
            "service_name",
            "user",
            "user_name",
            "name",
            "phone",
            "email",
            "comment",
            "status",
            "created_at",
        ]
        read_only_fields = ["id", "service_name", "user_name", "created_at"]
