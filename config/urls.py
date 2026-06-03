from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("users.urls")),
    path("api/", include("courses.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/", include("consultations.urls")),
    path("", TemplateView.as_view(template_name="index.html"), name="index"),
    path("login/", TemplateView.as_view(template_name="login.html"), name="login"),
    path("courses/", TemplateView.as_view(template_name="courses_list.html"), name="courses_list"),
    path("consultations/", TemplateView.as_view(template_name="consultations_list.html"), name="consultations_list"),
    path("register/", TemplateView.as_view(template_name="register.html"), name="register"),
    path("profile/", TemplateView.as_view(template_name="profile.html"), name="profile"),
    path("courses/<int:course_id>/", TemplateView.as_view(template_name="course_detail.html"), name="course_detail"),
    path("lessons/<int:lesson_id>/", TemplateView.as_view(template_name="lesson_detail.html"), name="lesson_detail"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
