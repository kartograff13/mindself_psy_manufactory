from django.urls import include, path
from rest_framework import routers

from courses.views import AttachmentViewSet, CourseViewSet, LessonViewSet, TestViewSet

router = routers.DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"lessons", LessonViewSet, basename="lesson")
router.register(r"attachments", AttachmentViewSet, basename="attachment")
router.register(r"tests", TestViewSet, basename="test")

urlpatterns = [
    path("", include(router.urls)),
]
