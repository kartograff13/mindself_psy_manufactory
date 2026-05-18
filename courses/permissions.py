from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminOrReadOnly(BasePermission):
    """
    Администратор - полный доступ, остальные - только чтение (GET, HEAD, OPTIONS).
    Используется для моделей, где изменение разрешено только администратору.
    """

    def has_permission(self, request, view):
        """
        Проверяет доступ на уровне запроса (не объекта).
        Безопасные методы разрешены всем, остальные - только администратору.
        """
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == "admin"


class IsOwnerOrAdmin(BasePermission):
    """
    Доступ на изменение объекта только владельцу (преподавателю) курса или администратору.
    Для чтения - доступ аутентифицированным пользователям, но контент будет отфильтрован.
    """

    def has_permission(self, request, view):
        """
        На уровне запроса разрешает безопасные методы (GET, HEAD, OPTIONS) всем.
        Для небезопасных методов (POST, PUT, PATCH, DELETE) доступ открыт только администратору или
        преподавателю-владельцу.
        """

        if request.method in SAFE_METHODS:
            return True

        return request.user.is_authenticated and request.user.role in ["admin", "teacher"]

    def has_object_permission(self, request, view, obj):
        """
        Проверяет доступ к конкретному объекту.
        Безопасные методы разрешены всем. Для изменения:
        - сам объект имеет атрибут 'owner' - сравниваем с пользователем
        - у объекта есть 'course' - проверяем владельца курса
        - у объекта есть 'lesson' - проверяем владельца урока - курса - владельца
        """
        if request.method in SAFE_METHODS:
            return True

        if hasattr(obj, "owner"):
            return request.user.role == "admin" or obj.owner == request.user

        if hasattr(obj, "course"):
            return request.user.role == "admin" or obj.course.owner == request.user

        if hasattr(obj, "lesson"):
            return request.user.role == "admin" or obj.lesson.course.owner == request.user

        return False


class IsEnrolledOrAdmin(BasePermission):
    """
    Доступ к содержимому курса (уроки, тесты) имеют студенты, записанные на этот курс,
    преподаватель-владелец курса или администратор.
    """

    def has_permission(self, request, view):
        """На уровне запроса требуется только аутентификация."""
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """
        Разрешает доступ, если пользователь:
        - администратор
        - преподаватель-владелец курса
        - студент, записанный на курс (через relation enrollments)/
        Автоматически определяет объект курса (по атрибутам course, lesson, owner).
        """
        user = request.user

        if user.is_authenticated and user.role == "admin":
            return True

        course = None

        if hasattr(obj, "course"):
            course = obj.course
        elif hasattr(obj, "lesson"):
            course = obj.lesson.course
        elif hasattr(obj, "owner"):
            course = obj

        if course is None:
            return False

        if user.is_authenticated and user.role == "teacher" and course.owner == user:
            return True

        return course.enrollments.filter(user=user).exists()
