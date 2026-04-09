from collections import Counter
from decimal import Decimal

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from db.models import (
    AssignmentStatus,
    Feedback,
    Project,
    ProjectAssignment,
    ProjectRequirement,
    Report,
    Role,
    SpecialistProfile,
    User,
    UserSkill,
)

from .serializers import (
    AnalyticsDashboardSerializer,
    FeedbackSerializer,
    ProjectAssignmentSerializer,
    ProjectRequirementSerializer,
    ProjectRequirementWriteSerializer,
    ProjectSerializer,
    RecommendationSerializer,
    ReportSerializer,
    SessionLoginSerializer,
    SpecialistCreateUpdateSerializer,
    SpecialistDetailSerializer,
    SpecialistProfileSerializer,
    UserSerializer,
    UserSkillSerializer,
    WorkloadItemSerializer,
)


ROLE_PRIORITY = {"junior": 1, "middle": 2, "senior": 3}


def build_recommendations(requirement: ProjectRequirement):
    required = set(requirement.required_skills.values_list("skill", flat=True))
    desired = set(requirement.desired_skills.values_list("skill", flat=True))

    specialists = SpecialistProfile.objects.select_related("user").prefetch_related("user__user_skills")
    recommendations = []

    for profile in specialists:
        user_skills = set(profile.user.user_skills.values_list("skill", flat=True))
        required_matched = sorted(required & user_skills)
        desired_matched = sorted(desired & user_skills)

        total_required = len(required) or 1
        required_score = len(required_matched) / total_required * 100
        desired_score = (len(desired_matched) / max(len(desired), 1) * 20) if desired else 0
        level_bonus = 10 if ROLE_PRIORITY.get(profile.level, 0) >= ROLE_PRIORITY.get(requirement.required_level, 0) else 0
        availability_penalty = 20 if profile.is_busy else 0
        score = max(0, min(100, required_score + desired_score + level_bonus - availability_penalty))

        reason = []
        if required_matched:
            reason.append(f"обязательные навыки: {', '.join(required_matched)}")
        if desired_matched:
            reason.append(f"желательные навыки: {', '.join(desired_matched)}")
        if not profile.is_busy:
            reason.append("сейчас доступен")
        elif profile.busy_until:
            reason.append(f"занят до {profile.busy_until}")

        recommendations.append(
            {
                "specialist_id": profile.user_id,
                "full_name": f"{profile.user.last_name} {profile.user.first_name}".strip(),
                "profession": profile.profession,
                "level": profile.level,
                "skill_match_percent": round(score, 2),
                "required_skills_matched": required_matched,
                "desired_skills_matched": desired_matched,
                "busy_until": profile.busy_until,
                "recommendation_reason": "; ".join(reason) if reason else "подходит по роли",
            }
        )

    recommendations.sort(key=lambda item: item["skill_match_percent"], reverse=True)
    return recommendations


class SessionLoginView(APIView):
    def post(self, request):
        serializer = SessionLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = get_object_or_404(User, email=serializer.validated_data["email"])
        request.session["api_user_id"] = user.id
        return Response({"message": "ok", "user": UserSerializer(user).data})


class SessionLogoutView(APIView):
    def post(self, request):
        request.session.pop("api_user_id", None)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionMeView(APIView):
    def get(self, request):
        user_id = request.session.get("api_user_id")
        if not user_id:
            return Response({"detail": "Пользователь не авторизован."}, status=status.HTTP_401_UNAUTHORIZED)
        user = get_object_or_404(User, pk=user_id)
        return Response(UserSerializer(user).data)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("last_name", "first_name")
    serializer_class = UserSerializer


class SpecialistViewSet(viewsets.ModelViewSet):
    queryset = SpecialistProfile.objects.select_related("user").all().order_by("user__last_name", "user__first_name")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return SpecialistCreateUpdateSerializer
        if self.action == "retrieve":
            return SpecialistDetailSerializer
        return SpecialistProfileSerializer

    @action(detail=True, methods=["get", "put"], url_path="skills")
    def skills(self, request, pk=None):
        profile = self.get_object()
        if request.method == "GET":
            queryset = profile.user.user_skills.all()
            return Response(UserSkillSerializer(queryset, many=True).data)

        profile.user.user_skills.all().delete()
        skills = request.data.get("skills", [])
        created = [UserSkill.objects.create(user=profile.user, skill=skill) for skill in dict.fromkeys(skills)]
        return Response(UserSkillSerializer(created, many=True).data)

    @action(detail=True, methods=["get", "post"], url_path="availability")
    def availability(self, request, pk=None):
        profile = self.get_object()
        if request.method == "GET":
            data = {
                "specialist_id": profile.user_id,
                "is_busy": profile.is_busy,
                "busy_until": profile.busy_until,
            }
            return Response(data)
        profile.is_busy = request.data.get("is_busy", profile.is_busy)
        profile.busy_until = request.data.get("busy_until", profile.busy_until)
        profile.save(update_fields=["is_busy", "busy_until"])
        return Response({"specialist_id": profile.user_id, "is_busy": profile.is_busy, "busy_until": profile.busy_until})

    @action(detail=True, methods=["get"], url_path="feedback")
    def feedback(self, request, pk=None):
        profile = self.get_object()
        queryset = Feedback.objects.filter(user=profile.user).select_related("project")
        return Response(FeedbackSerializer(queryset, many=True).data)


class SkillCatalogView(APIView):
    def get(self, request):
        return Response({"skills": [choice[0] for choice in UserSkill._meta.get_field("skill").choices]})


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.select_related("manager").prefetch_related("requirements").all().order_by("-id")
    serializer_class = ProjectSerializer

    @action(detail=True, methods=["get", "post"], url_path="roles")
    def roles(self, request, pk=None):
        project = self.get_object()
        if request.method == "GET":
            queryset = project.requirements.prefetch_related("required_skills", "desired_skills")
            return Response(ProjectRequirementSerializer(queryset, many=True).data)
        serializer = ProjectRequirementWriteSerializer(data=request.data, context={"project": project})
        serializer.is_valid(raise_exception=True)
        requirement = serializer.save()
        return Response(ProjectRequirementSerializer(requirement).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="feedback")
    def feedback(self, request, pk=None):
        project = self.get_object()
        queryset = project.feedbacks.select_related("user")
        return Response(FeedbackSerializer(queryset, many=True).data)

    @feedback.mapping.post
    def create_feedback(self, request, pk=None):
        project = self.get_object()
        serializer = FeedbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(project=project)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ProjectRequirementViewSet(viewsets.ModelViewSet):
    queryset = ProjectRequirement.objects.select_related("project").prefetch_related("required_skills", "desired_skills")

    def get_serializer_class(self):
        if self.action in {"create", "update", "partial_update"}:
            return ProjectRequirementWriteSerializer
        return ProjectRequirementSerializer

    def create(self, request, *args, **kwargs):
        project_id = request.data.get("project")
        project = get_object_or_404(Project, pk=project_id)
        serializer = self.get_serializer(data=request.data, context={"project": project})
        serializer.is_valid(raise_exception=True)
        requirement = serializer.save()
        return Response(ProjectRequirementSerializer(requirement).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        requirement = serializer.save()
        return Response(ProjectRequirementSerializer(requirement).data)

    @action(detail=True, methods=["get"], url_path="skills")
    def skills(self, request, pk=None):
        requirement = self.get_object()
        return Response(ProjectRequirementSerializer(requirement).data)

    @skills.mapping.put
    def replace_skills(self, request, pk=None):
        requirement = self.get_object()
        serializer = ProjectRequirementWriteSerializer(requirement, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        requirement = serializer.save()
        return Response(ProjectRequirementSerializer(requirement).data)

    @action(detail=True, methods=["get"], url_path="recommendations")
    def recommendations(self, request, pk=None):
        requirement = self.get_object()
        payload = build_recommendations(requirement)
        return Response(RecommendationSerializer(payload, many=True).data)

    @action(detail=True, methods=["post"], url_path="recommendations/recalculate")
    def recalculate(self, request, pk=None):
        requirement = self.get_object()
        payload = build_recommendations(requirement)
        return Response(
            {
                "project_requirement_id": requirement.id,
                "recommendations": RecommendationSerializer(payload, many=True).data,
                "message": "Рекомендации пересчитаны.",
            }
        )


class ProjectAssignmentViewSet(viewsets.ModelViewSet):
    queryset = ProjectAssignment.objects.select_related("project", "user", "assigned_by").all().order_by("-id")
    serializer_class = ProjectAssignmentSerializer

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = AssignmentStatus.ACCEPTED
        assignment.save(update_fields=["status"])
        return Response(ProjectAssignmentSerializer(assignment).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = AssignmentStatus.OFFERED
        assignment.save(update_fields=["status"])
        return Response(ProjectAssignmentSerializer(assignment).data)


class FeedbackViewSet(viewsets.ModelViewSet):
    queryset = Feedback.objects.select_related("user", "project").all().order_by("-created_at")
    serializer_class = FeedbackSerializer


class ReportViewSet(viewsets.ModelViewSet):
    queryset = Report.objects.select_related("project", "admin").all().order_by("-created_at")
    serializer_class = ReportSerializer


class DashboardAnalyticsView(APIView):
    def get(self, request):
        payload = {
            "active_projects": Project.objects.filter(status="в процессе").count(),
            "specialists_total": SpecialistProfile.objects.count(),
            "specialists_busy": SpecialistProfile.objects.filter(is_busy=True).count(),
            "open_requirements": ProjectRequirement.objects.count(),
            "assignments_active": ProjectAssignment.objects.filter(
                status__in=[AssignmentStatus.ACCEPTED, AssignmentStatus.WORKING]
            ).count(),
            "feedback_total": Feedback.objects.count(),
        }
        return Response(AnalyticsDashboardSerializer(payload).data)


class WorkloadAnalyticsView(APIView):
    def get(self, request):
        items = []
        assignment_counts = Counter(
            ProjectAssignment.objects.filter(
                status__in=[AssignmentStatus.ACCEPTED, AssignmentStatus.WORKING]
            ).values_list("user_id", flat=True)
        )
        for profile in SpecialistProfile.objects.select_related("user").all():
            active_assignments = assignment_counts.get(profile.user_id, 0)
            current_load = min(100.0, active_assignments * 50.0 if active_assignments else (100.0 if profile.is_busy else 0.0))
            items.append(
                {
                    "specialist_id": profile.user_id,
                    "full_name": f"{profile.user.last_name} {profile.user.first_name}".strip(),
                    "profession": profile.profession,
                    "level": profile.level,
                    "is_busy": profile.is_busy,
                    "busy_until": profile.busy_until,
                    "active_assignments": active_assignments,
                    "current_load_percent": current_load,
                }
            )
        return Response(WorkloadItemSerializer(items, many=True).data)


class ProjectAnalyticsView(APIView):
    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        assignments = project.assignments.all()
        feedbacks = project.feedbacks.all()
        reports = project.reports.all()
        payload = {
            "project_id": project.id,
            "project_name": project.name,
            "status": project.status,
            "requirements_count": project.requirements.count(),
            "assignments_total": assignments.count(),
            "assignments_by_status": {row["status"]: row["total"] for row in assignments.values("status").annotate(total=Count("id"))},
            "feedback_total": feedbacks.count(),
            "reports_total": reports.count(),
            "avg_skill_match_percent": round(
                float(
                    sum(
                        [assignment.skill_match_percent or Decimal("0") for assignment in assignments]
                    ) / max(assignments.count(), 1)
                ),
                2,
            ),
        }
        return Response(payload)


@api_view(["GET"])
def availability_overview(request):
    items = []
    for profile in SpecialistProfile.objects.select_related("user"):
        items.append(
            {
                "specialist_id": profile.user_id,
                "full_name": f"{profile.user.last_name} {profile.user.first_name}".strip(),
                "is_busy": profile.is_busy,
                "busy_until": profile.busy_until,
            }
        )
    return Response(items)
