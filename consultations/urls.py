from django.urls import include, path
from rest_framework.routers import DefaultRouter

from consultations.views import (
    ConsultationRequestViewSet,
    ConsultationServiceViewSet,
    SupervisionBookingViewSet,
    SupervisionRequestViewSet,
    SupervisionViewSet,
    TherapyBookingViewSet,
    TherapyRequestViewSet,
    TherapySessionViewSet,
)

router = DefaultRouter()
router.register(r"services", ConsultationServiceViewSet, basename="service")
router.register(r"requests", ConsultationRequestViewSet, basename="request")
router.register(r"supervisions", SupervisionViewSet, basename="supervision")
router.register(r"supervision-bookings", SupervisionBookingViewSet, basename="supervision-booking")
router.register(r"therapy-sessions", TherapySessionViewSet, basename="therapy-session")
router.register(r"therapy-bookings", TherapyBookingViewSet, basename="therapy-booking")
router.register(r"supervision-requests", SupervisionRequestViewSet, basename="supervision-request")
router.register(r"therapy-requests", TherapyRequestViewSet, basename="therapy-request")

urlpatterns = [
    path("", include(router.urls)),
]
