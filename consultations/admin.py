from django.contrib import admin

from consultations.models import ConsultationRequest, ConsultationService

admin.site.register(ConsultationService)
admin.site.register(ConsultationRequest)
