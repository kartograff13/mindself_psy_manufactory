from django.urls import include, path
from rest_framework import routers

from courses.views import (
    AttachmentViewSet,
    CourseViewSet,
    EnrollmentViewSet,
    LessonViewSet,
    TeacherAttachmentViewSet,
    TeacherLessonViewSet,
    TeacherTestViewSet,
    TestViewSet,
)

router = routers.DefaultRouter()
router.register(r"courses", CourseViewSet, basename="course")
router.register(r"lessons", LessonViewSet, basename="lesson")
router.register(r"attachments", AttachmentViewSet, basename="attachment")
router.register(r"tests", TestViewSet, basename="test")
router.register(r"enrollments", EnrollmentViewSet, basename="enrollment")

teacher_router = routers.DefaultRouter()
teacher_router.register(r"tests", TeacherTestViewSet, basename="teacher-test")
teacher_router.register(r"lessons", TeacherLessonViewSet, basename="teacher-lesson")
teacher_router.register(r"attachments", TeacherAttachmentViewSet, basename="teacher-attachment")

urlpatterns = [
    path("", include(router.urls)),
    path("teacher/", include(teacher_router.urls)),
]
