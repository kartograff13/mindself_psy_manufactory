from phonenumber_field.serializerfields import PhoneNumberField as PhoneNumberSerializerField
from rest_framework import serializers

from consultations.models import (
    ConsultationRequest,
    ConsultationService,
    Supervision,
    SupervisionBooking,
    SupervisionRequest,
    TherapyBooking,
    TherapyRequest,
    TherapySession,
)


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


class SupervisionSerializer(serializers.ModelSerializer):
    """
    Сериализатор супервизии (полная информация).
    Добавляет:
    - psychologist_name - имя ведущего (только чтение)
    - booked_count - количество подтвержденных записей
    """

    psychologist = serializers.HiddenField(default=serializers.CurrentUserDefault())
    psychologist_name = serializers.CharField(source="psychologist.username", read_only=True)
    booked_count = serializers.SerializerMethodField()

    class Meta:
        model = Supervision
        fields = "__all__"

    @staticmethod
    def get_booked_count(obj):
        """Возвращает количество подтверждённых записей на супервизию."""
        return obj.bookings.filter(status="confirmed").count()


class SupervisionBookingSerializer(serializers.ModelSerializer):
    """Сериализатор записи на супервизию (только чтение для студента и даты записи)."""

    student_name = serializers.CharField(source="student.username", read_only=True)
    supervision_title = serializers.CharField(source="supervision.title", read_only=True)

    class Meta:
        model = SupervisionBooking
        fields = "__all__"
        read_only_fields = ["student", "booked_at"]


class TherapySessionSerializer(serializers.ModelSerializer):
    """Сериализатор терапевтической сессии с именем психолога (только чтение)."""

    psychologist = serializers.HiddenField(default=serializers.CurrentUserDefault())
    psychologist_name = serializers.CharField(source="psychologist.username", read_only=True)

    class Meta:
        model = TherapySession
        fields = "__all__"


class TherapyBookingSerializer(serializers.ModelSerializer):
    """Сериализатор записи на терапевтическую сессию (только чтение для студента и даты записи)."""

    psychologist_name = serializers.CharField(source="psychologist.username", read_only=True)
    session_title = serializers.CharField(source="session.title", read_only=True)

    class Meta:
        model = TherapyBooking
        fields = "__all__"
        read_only_fields = ["student", "booked_at"]


class SupervisionRequestCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания заявки на супервизию.
    Автоматически подставляет данные авторизованного пользователя (ФИО, телефон, email),
    если они не указаны явно.
    """

    name = serializers.CharField(required=False)
    phone = PhoneNumberSerializerField(required=False)
    email = serializers.EmailField(required=False)

    class Meta:
        model = SupervisionRequest
        fields = ["supervision", "name", "phone", "email", "comment"]

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


class SupervisionRequestListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка заявок на супервизию (только чтение).
    Добавляет названия супервизии и имя пользователя (если авторизован).
    """

    supervision_title = serializers.CharField(source="supervision.title", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True, allow_null=True)

    class Meta:
        model = SupervisionRequest
        fields = "__all__"


class TherapyRequestCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания заявки на терапевтическую сессию.
    Автоматически подставляет данные авторизованного пользователя (ФИО, телефон, email),
    если они не указаны явно.
    """

    name = serializers.CharField(required=False)
    phone = PhoneNumberSerializerField(required=False)
    email = serializers.EmailField(required=False)

    class Meta:
        model = TherapyRequest
        fields = ["session", "name", "phone", "email", "comment"]

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


class TherapyRequestListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка заявок на терапию (только чтение).
    Добавляет название сессии и имя пользователя (если авторизован).
    """

    session_title = serializers.CharField(source="session.title", read_only=True)
    user_name = serializers.CharField(source="user.username", read_only=True, allow_null=True)

    class Meta:
        model = TherapyRequest
        fields = "__all__"
