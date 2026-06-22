from django.views.generic import TemplateView
from unfold.views import UnfoldModelAdminViewMixin

from consultations.models import ConsultationRequest
from courses.models import Course, Enrollment


class DashboardView(UnfoldModelAdminViewMixin, TemplateView):
    """
    Административная панель (дашборд) для отображения общей статистики:
    количество уроков, записей на курсы, новых и обработанных заявок на консультации.
    """

    title = "Дашборд Mindself Psy Manufactory"
    template_name = "admin/dashboard.html"

    def get_context_data(self, **kwargs):
        """
        Добавляет в контекст шаблона статистические данные:
        - total_courses: общее количество курсов
        - total_enrollments: общее количество записей на курсы
        - new_requests: количество новых заявок на консультацию
        - processed_requests: количество обработанных заявок
        """
        context = super().get_context_data(**kwargs)
        context["total_courses"] = Course.objects.count()
        context["total_enrollments"] = Enrollment.objects.count()
        context["new_requests"] = ConsultationRequest.objects.filter(status="new").count()
        context["processed_requests"] = ConsultationRequest.objects.filter(status="processed").count()

        return context
