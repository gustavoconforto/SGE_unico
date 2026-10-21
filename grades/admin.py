from django.contrib import admin

from grades.models import ExamType, Grade, GradeLevelSubject, Subject

# Temporary: lets grades be entered until the grade entry screens exist.
admin.site.register(Subject)
admin.site.register(ExamType)
admin.site.register(GradeLevelSubject)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "subject", "bimester", "exam_type", "score"]
    list_filter = ["bimester", "subject", "exam_type"]
    raw_id_fields = ["enrollment"]
