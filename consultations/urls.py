from django.urls import include, path
from rest_framework.routers import DefaultRouter

from consultations.views import ConsultationRequestViewSet, ConsultationServiceViewSet

router = DefaultRouter()
router.register(r"services", ConsultationServiceViewSet, basename="service")
router.register(r"requests", ConsultationRequestViewSet, basename="request")

urlpatterns = [
    path("", include(router.urls)),
]
