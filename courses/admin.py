from django.contrib import admin

from courses.models import Attachment, Choice, Course, Enrollment, Lesson, Question, StudentTestAttempt, Test

admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(Attachment)
admin.site.register(Test)
admin.site.register(Question)
admin.site.register(Choice)
admin.site.register(StudentTestAttempt)
admin.site.register(Enrollment)
