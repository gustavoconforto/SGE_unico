from django.contrib import admin

from pathways.models import (
    ExtraGradeSettings,
    Pathway,
    PathwayAttendance,
    PathwayEnrollment,
    PathwayGrade,
    PathwayOffering,
    PathwaySession,
)

# Temporary: lets pathways be managed until their screens exist.
admin.site.register(Pathway)
admin.site.register(ExtraGradeSettings)


@admin.register(PathwayOffering)
class PathwayOfferingAdmin(admin.ModelAdmin):
    list_display = ["pathway", "school_year", "name", "capacity"]
    list_filter = ["school_year", "pathway"]
    filter_horizontal = ["teachers"]


@admin.register(PathwayEnrollment)
class PathwayEnrollmentAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "offering", "joined_at", "left_at"]
    list_filter = ["offering"]
    raw_id_fields = ["enrollment"]


@admin.register(PathwaySession)
class PathwaySessionAdmin(admin.ModelAdmin):
    list_display = ["offering", "date", "topic"]
    list_filter = ["offering"]


@admin.register(PathwayAttendance)
class PathwayAttendanceAdmin(admin.ModelAdmin):
    list_display = ["session", "pathway_enrollment", "status"]
    list_filter = ["status", "session__offering"]
    raw_id_fields = ["session", "pathway_enrollment"]


@admin.register(PathwayGrade)
class PathwayGradeAdmin(admin.ModelAdmin):
    list_display = ["pathway_enrollment", "bimester", "score"]
    list_filter = ["bimester", "pathway_enrollment__offering"]
    raw_id_fields = ["pathway_enrollment"]
