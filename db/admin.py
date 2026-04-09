from django.contrib import admin

from .models import (
    Feedback,
    Project,
    ProjectAssignment,
    ProjectRequirement,
    ProjectRequirementDesiredSkill,
    ProjectRequirementRequiredSkill,
    Report,
    SpecialistProfile,
    User,
    UserSkill,
)


class SpecialistProfileInline(admin.StackedInline):
    model = SpecialistProfile
    extra = 0
    can_delete = False
    fk_name = "user"


class UserSkillInline(admin.TabularInline):
    model = UserSkill
    extra = 0


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "last_name",
        "first_name",
        "middle_name",
        "email",
        "phone",
        "role",
    )
    list_display_links = ("id", "last_name", "first_name")
    search_fields = (
        "last_name",
        "first_name",
        "middle_name",
        "email",
        "phone",
    )
    list_filter = ("role",)
    ordering = ("last_name", "first_name", "id")
    inlines = [SpecialistProfileInline, UserSkillInline]


@admin.register(SpecialistProfile)
class SpecialistProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "profession",
        "level",
        "experience_years",
        "is_busy",
        "busy_until",
    )
    search_fields = (
        "user__last_name",
        "user__first_name",
        "user__email",
    )
    list_filter = ("profession", "level", "is_busy")
    autocomplete_fields = ("user",)


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "skill")
    search_fields = (
        "user__last_name",
        "user__first_name",
        "user__email",
    )
    list_filter = ("skill",)
    autocomplete_fields = ("user",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "manager",
        "status",
        "start_date",
        "end_date",
        "budget",
    )
    list_display_links = ("id", "name")
    search_fields = (
        "name",
        "description",
        "expected_result",
        "manager__last_name",
        "manager__first_name",
        "manager__email",
    )
    list_filter = ("status", "start_date", "end_date")
    autocomplete_fields = ("manager",)
    ordering = ("-id",)


@admin.register(ProjectRequirement)
class ProjectRequirementAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "project",
        "profession",
        "required_level",
        "desired_level",
        "specialists_count",
    )
    list_display_links = ("id", "project")
    search_fields = ("project__name",)
    list_filter = ("profession", "required_level", "desired_level")
    autocomplete_fields = ("project",)


@admin.register(ProjectRequirementRequiredSkill)
class ProjectRequirementRequiredSkillAdmin(admin.ModelAdmin):
    list_display = ("id", "project_requirement", "skill")
    list_display_links = ("id", "project_requirement")
    search_fields = ("project_requirement__project__name",)
    list_filter = ("skill",)
    autocomplete_fields = ("project_requirement",)


@admin.register(ProjectRequirementDesiredSkill)
class ProjectRequirementDesiredSkillAdmin(admin.ModelAdmin):
    list_display = ("id", "project_requirement", "skill")
    list_display_links = ("id", "project_requirement")
    search_fields = ("project_requirement__project__name",)
    list_filter = ("skill",)
    autocomplete_fields = ("project_requirement",)


@admin.register(ProjectAssignment)
class ProjectAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "project",
        "user",
        "role",
        "status",
        "start_date",
        "end_date",
        "assigned_by",
        "skill_match_percent",
    )
    list_display_links = ("id", "project")
    search_fields = (
        "project__name",
        "user__last_name",
        "user__first_name",
        "user__email",
        "assigned_by__last_name",
        "assigned_by__first_name",
        "assigned_by__email",
    )
    list_filter = ("role", "status", "start_date", "end_date")
    autocomplete_fields = ("project", "user", "assigned_by")
    ordering = ("-id",)


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "project",
        "role",
        "created_at",
    )
    list_display_links = ("id", "user")
    search_fields = (
        "text",
        "user__last_name",
        "user__first_name",
        "user__email",
        "project__name",
    )
    list_filter = ("role", "created_at")
    autocomplete_fields = ("user", "project")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "project",
        "admin",
        "total_hours",
        "quality",
        "created_at",
    )
    list_display_links = ("id", "project")
    search_fields = (
        "project__name",
        "admin__last_name",
        "admin__first_name",
        "admin__email",
        "recommendations",
    )
    list_filter = ("quality", "created_at")
    autocomplete_fields = ("project", "admin")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)