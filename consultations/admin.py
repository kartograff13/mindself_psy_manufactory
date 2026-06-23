from django.contrib import admin

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

admin.site.register(ConsultationService)
admin.site.register(ConsultationRequest)
admin.site.register(Supervision)
admin.site.register(SupervisionBooking)
admin.site.register(TherapySession)
admin.site.register(TherapyBooking)
admin.site.register(SupervisionRequest)
admin.site.register(TherapyRequest)
