from django.contrib import admin

from lessons.models import Lecture, TimetableSlot


@admin.register(TimetableSlot)
class TimetableSlotAdmin(admin.ModelAdmin):
    list_display = ["school_class", "weekday", "period", "subject", "teacher"]
    list_filter = ["school_class__year", "weekday"]


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ["school_class", "date", "period", "subject", "teacher", "topic"]
    list_filter = ["school_class__year", "date"]
    search_fields = ["topic"]
