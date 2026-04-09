from django.db import transaction
from rest_framework import serializers

from db.models import (
    AssignmentStatus,
    Feedback,
    Profession,
    Project,
    ProjectAssignment,
    ProjectRequirement,
    ProjectRequirementDesiredSkill,
    ProjectRequirementRequiredSkill,
    ProjectStatus,
    Report,
    Role,
    Skill,
    SpecialistProfile,
    User,
    UserSkill,
)


class SessionLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "last_name",
            "first_name",
            "middle_name",
            "full_name",
            "email",
            "phone",
            "role",
        ]

    def get_full_name(self, obj):
        parts = [obj.last_name, obj.first_name, obj.middle_name]
        return " ".join([part for part in parts if part])


class UserSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSkill
        fields = ["id", "user", "skill"]


class SpecialistProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=Role.SPECIALIST),
        source="user",
        write_only=True,
        required=False,
    )
    skills = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = SpecialistProfile
        fields = [
            "user",
            "user_id",
            "experience_years",
            "profession",
            "level",
            "is_busy",
            "busy_until",
            "skills",
        ]

    def get_skills(self, obj):
        return list(obj.user.user_skills.values_list("skill", flat=True))


class SpecialistDetailSerializer(SpecialistProfileSerializer):
    assignments = serializers.SerializerMethodField(read_only=True)

    class Meta(SpecialistProfileSerializer.Meta):
        fields = SpecialistProfileSerializer.Meta.fields + ["assignments"]

    def get_assignments(self, obj):
        assignments = obj.user.project_assignments.select_related("project")
        return [
            {
                "id": assignment.id,
                "project_id": assignment.project_id,
                "project_name": assignment.project.name,
                "status": assignment.status,
                "start_date": assignment.start_date,
                "end_date": assignment.end_date,
                "skill_match_percent": assignment.skill_match_percent,
            }
            for assignment in assignments
        ]


class SpecialistCreateUpdateSerializer(serializers.Serializer):
    user = UserSerializer()
    experience_years = serializers.IntegerField(min_value=0)
    profession = serializers.ChoiceField(choices=Profession.choices)
    level = serializers.ChoiceField(choices=SpecialistProfile._meta.get_field("level").choices)
    is_busy = serializers.BooleanField(default=False)
    busy_until = serializers.DateField(required=False, allow_null=True)
    skills = serializers.ListField(
        child=serializers.ChoiceField(choices=Skill.choices),
        allow_empty=True,
    )

    def create(self, validated_data):
        user_data = validated_data.pop("user")
        skills = validated_data.pop("skills", [])
        with transaction.atomic():
            user = User.objects.create(role=Role.SPECIALIST, **user_data)
            profile = SpecialistProfile.objects.create(user=user, **validated_data)
            UserSkill.objects.bulk_create([UserSkill(user=user, skill=skill) for skill in set(skills)])
        return profile

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", None)
        skills = validated_data.pop("skills", None)
        with transaction.atomic():
            if user_data:
                for field, value in user_data.items():
                    setattr(instance.user, field, value)
                instance.user.role = Role.SPECIALIST
                instance.user.save()
            for field, value in validated_data.items():
                setattr(instance, field, value)
            instance.save()
            if skills is not None:
                instance.user.user_skills.all().delete()
                UserSkill.objects.bulk_create([UserSkill(user=instance.user, skill=skill) for skill in set(skills)])
        return instance


class ProjectRequirementRequiredSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectRequirementRequiredSkill
        fields = ["id", "project_requirement", "skill"]


class ProjectRequirementDesiredSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectRequirementDesiredSkill
        fields = ["id", "project_requirement", "skill"]


class ProjectRequirementSerializer(serializers.ModelSerializer):
    required_skills = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="skill",
    )
    desired_skills = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="skill",
    )

    class Meta:
        model = ProjectRequirement
        fields = [
            "id",
            "project",
            "profession",
            "required_level",
            "desired_level",
            "specialists_count",
            "required_skills",
            "desired_skills",
        ]


class ProjectRequirementWriteSerializer(serializers.Serializer):
    profession = serializers.ChoiceField(choices=Profession.choices)
    required_level = serializers.ChoiceField(choices=SpecialistProfile._meta.get_field("level").choices)
    desired_level = serializers.ChoiceField(
        choices=SpecialistProfile._meta.get_field("level").choices,
        required=False,
        allow_null=True,
    )
    specialists_count = serializers.IntegerField(min_value=1)
    required_skills = serializers.ListField(
        child=serializers.ChoiceField(choices=Skill.choices),
        allow_empty=True,
        required=False,
    )
    desired_skills = serializers.ListField(
        child=serializers.ChoiceField(choices=Skill.choices),
        allow_empty=True,
        required=False,
    )

    def create(self, validated_data):
        project = self.context["project"]
        required_skills = validated_data.pop("required_skills", [])
        desired_skills = validated_data.pop("desired_skills", [])
        with transaction.atomic():
            requirement = ProjectRequirement.objects.create(project=project, **validated_data)
            ProjectRequirementRequiredSkill.objects.bulk_create([
                ProjectRequirementRequiredSkill(project_requirement=requirement, skill=skill)
                for skill in set(required_skills)
            ])
            ProjectRequirementDesiredSkill.objects.bulk_create([
                ProjectRequirementDesiredSkill(project_requirement=requirement, skill=skill)
                for skill in set(desired_skills)
            ])
        return requirement

    def update(self, instance, validated_data):
        required_skills = validated_data.pop("required_skills", None)
        desired_skills = validated_data.pop("desired_skills", None)
        with transaction.atomic():
            for field, value in validated_data.items():
                setattr(instance, field, value)
            instance.save()
            if required_skills is not None:
                instance.required_skills.all().delete()
                ProjectRequirementRequiredSkill.objects.bulk_create([
                    ProjectRequirementRequiredSkill(project_requirement=instance, skill=skill)
                    for skill in set(required_skills)
                ])
            if desired_skills is not None:
                instance.desired_skills.all().delete()
                ProjectRequirementDesiredSkill.objects.bulk_create([
                    ProjectRequirementDesiredSkill(project_requirement=instance, skill=skill)
                    for skill in set(desired_skills)
                ])
        return instance


class ProjectSerializer(serializers.ModelSerializer):
    manager = UserSerializer(read_only=True)
    manager_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=Role.PROJECT_MANAGER),
        source="manager",
        write_only=True,
    )
    requirements = ProjectRequirementSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "name",
            "description",
            "start_date",
            "end_date",
            "budget",
            "expected_result",
            "manager",
            "manager_id",
            "status",
            "requirements",
        ]


class ProjectAssignmentSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source="project.name", read_only=True)
    user_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProjectAssignment
        fields = [
            "id",
            "project",
            "project_name",
            "user",
            "user_name",
            "role",
            "status",
            "start_date",
            "end_date",
            "assigned_by",
            "skill_match_percent",
        ]

    def get_user_name(self, obj):
        return f"{obj.user.last_name} {obj.user.first_name}".strip()


class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ["id", "text", "user", "project", "role", "created_at"]
        read_only_fields = ["created_at"]


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = [
            "id",
            "project",
            "admin",
            "total_hours",
            "quality",
            "recommendations",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class RecommendationSerializer(serializers.Serializer):
    specialist_id = serializers.IntegerField()
    full_name = serializers.CharField()
    profession = serializers.CharField()
    level = serializers.CharField()
    skill_match_percent = serializers.FloatField()
    required_skills_matched = serializers.ListField(child=serializers.CharField())
    desired_skills_matched = serializers.ListField(child=serializers.CharField())
    busy_until = serializers.DateField(allow_null=True)
    recommendation_reason = serializers.CharField()


class AnalyticsDashboardSerializer(serializers.Serializer):
    active_projects = serializers.IntegerField()
    specialists_total = serializers.IntegerField()
    specialists_busy = serializers.IntegerField()
    open_requirements = serializers.IntegerField()
    assignments_active = serializers.IntegerField()
    feedback_total = serializers.IntegerField()


class WorkloadItemSerializer(serializers.Serializer):
    specialist_id = serializers.IntegerField()
    full_name = serializers.CharField()
    profession = serializers.CharField()
    level = serializers.CharField()
    is_busy = serializers.BooleanField()
    busy_until = serializers.DateField(allow_null=True)
    active_assignments = serializers.IntegerField()
    current_load_percent = serializers.FloatField()
