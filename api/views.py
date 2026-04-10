from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.db.models import Count
import json

from db.models import (
    AssignmentStatus,
    Feedback,
    Level,
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
    QualityLevel
)

from django.http import FileResponse, Http404
from db.services.docx_reports import (
    build_project_report_docx,
    build_specialist_report_docx,
    build_quality_feedback_report_docx,
)

from db.services.recommendations import recommend_specialists_for_requirement

ROLE_LABELS = {
    Role.ADMIN: "Администратор",
    Role.PROJECT_MANAGER: "Менеджер проекта",
    Role.SPECIALIST: "Специалист",
    Role.CUSTOMER: "Заказчик",
}

QUALITY_LEVEL = {
    QualityLevel.AWFUL: 1,
    QualityLevel.BAD: 2,
    QualityLevel.NORMAL: 3,
    QualityLevel.GOOD: 4,
    QualityLevel.EXCELLENT: 5
}

STATUS_FORM_TO_MODEL = {
    "draft": ProjectStatus.NOT_STARTED,
    "not_started": ProjectStatus.NOT_STARTED,
    "in_progress": ProjectStatus.IN_PROGRESS,
    "completed": ProjectStatus.COMPLETED,
    ProjectStatus.NOT_STARTED: ProjectStatus.NOT_STARTED,
    ProjectStatus.IN_PROGRESS: ProjectStatus.IN_PROGRESS,
    ProjectStatus.COMPLETED: ProjectStatus.COMPLETED,
}


PROFESSION_LABELS = dict(Profession.choices)
LEVEL_LABELS = dict(Level.choices)
SKILL_VALUES = [choice[0] for choice in Skill.choices]


def _full_name(user: User) -> str:
    return " ".join(part for part in [user.last_name, user.first_name, user.middle_name] if part)


def _current_user(request):
    user_id = request.session.get("api_user_id")
    if not user_id:
        return None
    return User.objects.filter(pk=user_id).first()


def _page(request, template_name, page_title, page_description, **context):
    context.update({
        'page_title': page_title,
        'page_description': page_description,
        'current_user': _current_user(request),
    })
    return render(request, template_name, context)


def login_view(request):
    if _current_user(request):
        return redirect("app:dashboard")

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        role = request.POST.get("role") or ""
        user = User.objects.filter(email=email).first()
        if not user:
            messages.error(request, "Пользователь с таким email не найден.")
        elif role and user.role != role:
            messages.error(request, "Роль не совпадает с профилем пользователя.")
        else:
            request.session["api_user_id"] = user.id
            request.session["api_user_name"] = _full_name(user)
            messages.success(request, f"Вы вошли как {_full_name(user)}.")
            return redirect("app:dashboard")

    return _page(
        request,
        "pages/login.html",
        "Вход в систему",
        "Авторизация пользователей по ролям.",
        roles=Role.choices,
    )


def logout_view(request):
    if request.method == "POST":
        request.session.pop("api_user_id", None)
        request.session.pop("api_user_name", None)
        messages.success(request, "Вы вышли из системы.")
    return redirect("app:login")


def register_view(request):
    if request.method == "POST":
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()
        middle_name = (request.POST.get("middle_name") or "").strip() or None
        email = (request.POST.get("email") or "").strip().lower()
        phone = (request.POST.get("phone") or "").strip()
        role = request.POST.get("role") or Role.SPECIALIST
        profession = request.POST.get("profession") or Profession.BACKEND
        level = request.POST.get("level") or Level.JUNIOR
        experience_years = int(request.POST.get("experience_years") or 0)

        if not first_name or not last_name or not email or not phone:
            messages.error(request, "Заполните обязательные поля регистрации.")
        elif User.objects.filter(email=email).exists():
            messages.error(request, "Пользователь с таким email уже существует.")
        else:
            user = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                email=email,
                phone=phone,
                role=role,
            )
            if role == Role.SPECIALIST:
                SpecialistProfile.objects.create(
                    user=user,
                    experience_years=max(0, experience_years),
                    profession=profession,
                    level=level,
                    is_busy=False,
                )
            request.session["api_user_id"] = user.id
            request.session["api_user_name"] = _full_name(user)
            messages.success(request, "Регистрация прошла успешно.")
            return redirect("app:dashboard")

    return _page(
        request,
        "pages/register.html",
        "Регистрация",
        "Создание нового пользователя в системе.",
        roles=Role.choices,
        professions=Profession.choices,
        levels=Level.choices,
    )


def dashboard_view(request):
    stats = [
        {"label": "Активные проекты", "value": Project.objects.filter(status=ProjectStatus.IN_PROGRESS).count()},
        {"label": "Свободные специалисты", "value": SpecialistProfile.objects.filter(is_busy=False).count()},
        {"label": "Ожидают назначения", "value": ProjectAssignment.objects.filter(status=AssignmentStatus.OFFERED).count()},
        {
            "label": "Средняя загрузка",
            "value": f"{min(100, SpecialistProfile.objects.filter(is_busy=True).count() * 100 // max(SpecialistProfile.objects.count(), 1))}%",
        },
    ]
    return _page(request, "pages/dashboard.html", "Дашборд", "Общий обзор системы.", stats=stats)


def specialists_list_view(request):
    query = (request.GET.get("q") or "").strip().lower()
    profession_filter = request.GET.get("profession") or ""
    load_filter = request.GET.get("load") or ""

    profiles = SpecialistProfile.objects.select_related("user").prefetch_related("user__user_skills").all()
    if profession_filter:
        profiles = profiles.filter(profession=profession_filter)
    if load_filter == "free":
        profiles = profiles.filter(is_busy=False)
    elif load_filter == "busy":
        profiles = profiles.filter(is_busy=True)

    specialists = []
    for profile in profiles:
        skills = list(profile.user.user_skills.values_list("skill", flat=True))
        name = _full_name(profile.user)
        if query and query not in name.lower() and not any(query in skill.lower() for skill in skills):
            continue
        specialists.append(
            {
                "id": profile.user_id,
                "name": name,
                "role": profile.profession,
                "stack": ", ".join(skills) or "—",
                "load": f"Занят до {profile.busy_until}" if profile.is_busy else "Свободен",
            }
        )

    return _page(
        request,
        "pages/specialists_list.html",
        "Специалисты",
        "Список всех специалистов и фильтры.",
        specialists=specialists,
        profession_choices=Profession.choices,
        selected_profession=profession_filter,
        selected_load=load_filter,
        query=query,
    )


def specialist_detail_view(request, pk):
    profile = get_object_or_404(SpecialistProfile.objects.select_related("user"), pk=pk)
    assignments = profile.user.project_assignments.select_related("project").all()
    specialist = {
        "id": profile.user_id,
        "name": _full_name(profile.user),
        "role": profile.profession,
        "seniority": profile.level,
        "experience": f"{profile.experience_years} лет",
        "load": "100%" if profile.is_busy else "0%",
        "skills": list(profile.user.user_skills.values_list("skill", flat=True)),
        "projects": [assignment.project.name for assignment in assignments],
    }
    return _page(request, "pages/specialist_detail.html", "Карточка специалиста", "Детальная информация о специалисте.", specialist=specialist)


def specialist_edit_view(request, pk):
    profile = get_object_or_404(SpecialistProfile.objects.select_related("user"), pk=pk)
    user = profile.user

    if request.method == "POST":
        user.first_name = (request.POST.get("first_name") or user.first_name).strip()
        user.last_name = (request.POST.get("last_name") or user.last_name).strip()
        user.middle_name = (request.POST.get("middle_name") or "").strip() or None
        user.email = (request.POST.get("email") or user.email).strip().lower()
        user.phone = (request.POST.get("phone") or user.phone).strip()
        user.save()

        profile.profession = request.POST.get("profession") or profile.profession
        profile.level = request.POST.get("level") or profile.level
        profile.experience_years = int(request.POST.get("experience_years") or profile.experience_years)
        busy_until = request.POST.get("busy_until") or None
        profile.busy_until = busy_until
        profile.is_busy = bool(busy_until)
        profile.save()

        skills_input = request.POST.get("skills") or ""
        skills = [skill.strip() for skill in skills_input.split(",") if skill.strip()]
        valid_skills = [skill for skill in dict.fromkeys(skills) if skill in SKILL_VALUES]
        user.user_skills.all().delete()
        UserSkill.objects.bulk_create([UserSkill(user=user, skill=skill) for skill in valid_skills])

        messages.success(request, "Профиль специалиста обновлён.")
        return redirect("app:specialist_detail", pk=pk)

    specialist = {
        "id": profile.user_id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "middle_name": user.middle_name or "",
        "email": user.email,
        "phone": user.phone,
        "role": profile.profession,
        "seniority": profile.level,
        "experience": profile.experience_years,
        "skills": ", ".join(user.user_skills.values_list("skill", flat=True)),
        "busy_until": profile.busy_until.isoformat() if profile.busy_until else "",
    }
    return _page(
        request,
        "pages/specialist_edit.html",
        "Редактирование специалиста",
        "Изменение профиля, навыков и доступности.",
        specialist=specialist,
        profession_choices=Profession.choices,
        level_choices=Level.choices,
        skill_choices=Skill.choices,
    )


def projects_list_view(request):
    projects = []
    for project in Project.objects.select_related("manager").all().order_by("-id"):
        projects.append(
            {
                "id": project.id,
                "name": project.name,
                "status": project.status,
                "manager": _full_name(project.manager),
                "dates": f"{project.start_date:%d.%m.%Y} — {project.end_date:%d.%m.%Y}" if project.end_date else f"{project.start_date:%d.%m.%Y} — ?",
            }
        )
    return _page(request, "pages/projects_list.html", "Проекты", "Список проектов компании.", projects=projects)


def _get_manager_choices():
    return User.objects.filter(role=Role.PROJECT_MANAGER).order_by("last_name", "first_name")


def _project_form_context(project=None):
    return {
        "managers": _get_manager_choices(),
        "status_choices": [
            (ProjectStatus.NOT_STARTED, "Не начат"),
            (ProjectStatus.IN_PROGRESS, "В работе"),
            (ProjectStatus.COMPLETED, "Завершён"),
        ],
        "project": project,
    }


def project_detail_view(request, pk):
    project_obj = get_object_or_404(Project.objects.select_related("manager"), pk=pk)
    project = {
        "id": project_obj.id,
        "name": project_obj.name,
        "status": project_obj.status,
        "manager": _full_name(project_obj.manager),
        "budget": project_obj.budget,
        "period": f"{project_obj.start_date:%d.%m.%Y} — {project_obj.end_date:%d.%m.%Y}" if project_obj.end_date else f"{project_obj.start_date:%d.%m.%Y} — ?",
        "team": [_full_name(item.user) for item in project_obj.assignments.select_related("user").all()],
    }
    return _page(request, "pages/project_detail.html", "Карточка проекта", "Подробная информация о проекте.", project=project)


def project_create_view(request):
    if request.method == "POST":
        return _save_project(request)
    context = _project_form_context()
    return _page(request, "pages/create_project.html", "Создание проекта", "Форма создания нового проекта.", **context)


def project_edit_view(request, pk=None):
    project = get_object_or_404(Project.objects.select_related("manager"), pk=pk)
    if request.method == "POST":
        return _save_project(request, project)
    context = _project_form_context(project)
    return _page(request, "pages/project_edit.html", "Редактирование проекта", "Форма редактирования проекта.", **context)


def _save_project(request, project=None):
    managers = _get_manager_choices()
    name = (request.POST.get("name") or "").strip()
    manager_id = request.POST.get("manager_id") or None
    start_date = request.POST.get("start_date") or None
    end_date = request.POST.get("end_date") or None
    budget_raw = (request.POST.get("budget") or "").strip()
    status = STATUS_FORM_TO_MODEL.get(request.POST.get("status") or ProjectStatus.NOT_STARTED, ProjectStatus.NOT_STARTED)
    description = (request.POST.get("description") or "").strip()
    expected_result = (request.POST.get("expected_result") or "").strip()

    if not all([name, manager_id, start_date, budget_raw, description, expected_result]):
        messages.error(request, "Заполните обязательные поля проекта.")
        template = "pages/project_edit.html" if project else "pages/create_project.html"
        return render(request, template, {**_project_form_context(project), "page_title": "Редактирование проекта" if project else "Создание проекта", "page_description": "Форма проекта."})

    manager = User.objects.filter(id=manager_id, role=Role.PROJECT_MANAGER).first()
    if not manager:
        messages.error(request, "Выберите корректного менеджера проекта.")
        template = "pages/project_edit.html" if project else "pages/create_project.html"
        return render(request, template, {**_project_form_context(project), "page_title": "Редактирование проекта" if project else "Создание проекта", "page_description": "Форма проекта."})

    try:
        budget = Decimal(str(budget_raw).replace(" ", "").replace(",", "."))
    except InvalidOperation:
        messages.error(request, "Некорректный бюджет.")
        template = "pages/project_edit.html" if project else "pages/create_project.html"
        return render(request, template, {**_project_form_context(project), "page_title": "Редактирование проекта" if project else "Создание проекта", "page_description": "Форма проекта."})

    if project is None:
        project = Project()
    project.name = name
    project.manager = manager
    project.start_date = start_date
    project.end_date = end_date or None
    project.budget = budget
    project.status = status
    project.description = description
    project.expected_result = expected_result
    project.save()
    messages.success(request, f'Проект "{project.name}" успешно сохранён.')
    return redirect("app:project_detail", pk=project.id)


def project_roles_view(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if request.method == "POST":
        profession = request.POST.get("profession") or Profession.BACKEND
        required_level = request.POST.get("required_level") or Level.JUNIOR
        desired_level = request.POST.get("desired_level") or None
        specialists_count = int(request.POST.get("specialists_count") or 1)
        required_skills = [skill.strip() for skill in (request.POST.get("required_skills") or "").split(",") if skill.strip()]
        desired_skills = [skill.strip() for skill in (request.POST.get("desired_skills") or "").split(",") if skill.strip()]

        requirement = ProjectRequirement.objects.create(
            project=project,
            profession=profession,
            required_level=required_level,
            desired_level=desired_level or None,
            specialists_count=max(1, specialists_count),
        )
        ProjectRequirementRequiredSkill.objects.bulk_create([
            ProjectRequirementRequiredSkill(project_requirement=requirement, skill=skill)
            for skill in dict.fromkeys(required_skills)
            if skill in SKILL_VALUES
        ])
        ProjectRequirementDesiredSkill.objects.bulk_create([
            ProjectRequirementDesiredSkill(project_requirement=requirement, skill=skill)
            for skill in dict.fromkeys(desired_skills)
            if skill in SKILL_VALUES
        ])
        messages.success(request, "Роль проекта добавлена.")
        return redirect("app:project_roles", pk=pk)

    roles = []
    for role in project.requirements.prefetch_related("required_skills").all():
        roles.append(
            {
                "id": role.id,
                "title": role.profession,
                "count": role.specialists_count,
                "must_have": ", ".join(role.required_skills.values_list("skill", flat=True)) or "—",
                "status": "Открыта",
            }
        )
    return _page(
        request,
        "pages/project_roles.html",
        "Роли и требования проекта",
        "Настройка ролей, количества специалистов и навыков.",
        project=project,
        project_id=pk,
        roles=roles,
        profession_choices=Profession.choices,
        level_choices=Level.choices,
        skill_choices=Skill.choices,
    )


def recommendations_view(request, role_id):
    requirement = get_object_or_404(
        ProjectRequirement.objects.select_related("project").prefetch_related(
            "required_skills",
            "desired_skills",
        ),
        pk=role_id,
    )
    project = requirement.project

    if request.method == "POST":
        specialist_id = request.POST.get("specialist_id")

        # В recommendations.py используется user_id, а не pk профиля
        profile = get_object_or_404(
            SpecialistProfile.objects.select_related("user"),
            user_id=specialist_id,
        )

        # Получаем актуальные рекомендации, чтобы взять метрики выбранного кандидата
        raw_recommendations = recommend_specialists_for_requirement(requirement, limit=1000)
        recommendation_map = {
            item["user_id"]: item
            for item in raw_recommendations
            if isinstance(item, dict)
        }
        rec = recommendation_map.get(profile.user_id)

        # skill_match_percent лучше хранить как процент покрытия required skills,
        # потому что total_score из recommendations.py не является процентом
        skill_match_percent = 0
        if rec:
            skill_match_percent = round(rec.get("required_skill_coverage", 0) * 100, 2)

        actor = (
            _current_user(request)
            or User.objects.filter(role=Role.ADMIN).first()
            or User.objects.filter(role=Role.PROJECT_MANAGER).first()
            or profile.user
        )

        ProjectAssignment.objects.create(
            project=project,
            user=profile.user,
            role=Role.SPECIALIST,
            status=AssignmentStatus.OFFERED,
            start_date=project.start_date,
            end_date=project.end_date,
            assigned_by=actor,
            skill_match_percent=skill_match_percent,
        )

        profile.is_busy = True
        profile.busy_until = project.end_date or project.start_date
        profile.save(update_fields=["is_busy", "busy_until"])

        messages.success(
            request,
            f"Специалист {_full_name(profile.user)} назначен на проект.",
        )
        return redirect("app:assignments")

    raw_recommendations = recommend_specialists_for_requirement(requirement, limit=10)

    recommendations = []
    for item in raw_recommendations:
        # защита на случай, если fallback-ветка в recommendations.py
        # все еще возвращает числа, а не словари
        if not isinstance(item, dict):
            continue

        required_matches = item.get("required_skill_matches", 0)
        required_total = item.get("required_skill_total", 0)
        desired_matches = item.get("desired_skill_matches", 0)
        desired_total = item.get("desired_skill_total", 0)

        mode_label = "Идеальный кандидат" if item.get("mode") == "ideal" else "Резервный кандидат"

        reason_parts = [
            mode_label,
            f"Профессия: {item.get('profession', '—')}",
            f"Уровень: {item.get('level', '—')}",
            f"Опыт: {item.get('experience_years', 0)} лет",
            f"Обязательные навыки: {required_matches}/{required_total}",
        ]

        if desired_total:
            reason_parts.append(f"Желательные навыки: {desired_matches}/{desired_total}")

        if item.get("is_exact_profession"):
            reason_parts.append("Точное совпадение по профессии")

        recommendations.append(
            {
                "id": item["user_id"],  # в POST теперь тоже передаем user_id
                "name": item["full_name"],
                "score": f"{round(item.get('required_skill_coverage', 0) * 100)}%",
                "reason": ", ".join(reason_parts),
                "end_date": "сейчас свободен",
                "total_score": round(item.get("total_score", 0), 2),
            }
        )

    return _page(
        request,
        "pages/recommendations.html",
        "Рекомендации кандидатов",
        "Подбор специалистов под конкретную роль.",
        role_id=role_id,
        project=project,
        recommendations=recommendations,
    )


def assignments_view(request):
    if request.method == "POST":
        assignment = get_object_or_404(ProjectAssignment, pk=request.POST.get("assignment_id"))
        action = request.POST.get("action")
        if action == "accept":
            assignment.status = AssignmentStatus.ACCEPTED
        elif action == "start":
            assignment.status = AssignmentStatus.WORKING
        elif action == "finish":
            assignment.status = AssignmentStatus.FINISHED
            profile = SpecialistProfile.objects.filter(pk=assignment.user_id).first()
            if profile:
                profile.is_busy = False
                profile.busy_until = None
                profile.save(update_fields=["is_busy", "busy_until"])
        assignment.save(update_fields=["status"])
        messages.success(request, "Статус назначения обновлён.")
        return redirect("app:assignments")

    assignments = []
    for assignment in ProjectAssignment.objects.select_related("user", "project").all().order_by("-id"):
        assignments.append(
            {
                "id": assignment.id,
                "specialist": _full_name(assignment.user),
                "project": assignment.project.name,
                "role": assignment.role,
                "status": assignment.status,
                "load": f"{assignment.skill_match_percent or 0}%",
            }
        )
    return _page(request, "pages/assignments.html", "Назначения", "Управление назначениями специалистов на проекты.", assignments=assignments)


def workload_view(request):
    workload = []
    for profile in SpecialistProfile.objects.select_related("user").all():
        workload.append(
            {
                "name": _full_name(profile.user),
                "current": "100%" if profile.is_busy else "0%",
                "free_from": profile.busy_until or "Уже доступен",
            }
        )
    return _page(request, "pages/workload.html", "Загрузка специалистов", "Календарь занятости и доступности.", workload=workload)


def feedback_view(request):
    if request.method == "POST":
        author = _current_user(request)
        project = get_object_or_404(Project, pk=request.POST.get("project_id"))
        text = (request.POST.get("text") or "").strip()
        if author and text:
            Feedback.objects.create(text=text, user=author, project=project, role=author.role)
            messages.success(request, "Отзыв сохранён.")
        else:
            messages.error(request, "Не удалось сохранить отзыв.")
        return redirect("app:feedback")

    feedback_items = []
    for item in Feedback.objects.select_related("user", "project").all().order_by("-created_at"):
        feedback_items.append(
            {
                "author": _full_name(item.user),
                "target": item.project.name,
                "rating": ROLE_LABELS.get(item.role, item.role),
                "comment": item.text,
            }
        )
    return _page(
        request,
        "pages/feedback.html",
        "Отзывы и обратная связь",
        "Сбор и просмотр отзывов по проектам и специалистам.",
        feedback_items=feedback_items,
        projects=Project.objects.all().order_by("name"),
    )


def analytics_view(request):
    total_projects = Project.objects.count()
    total_reports = Report.objects.count()
    total_specialists = SpecialistProfile.objects.count()

    free_specialists = SpecialistProfile.objects.filter(is_busy=False).count()
    busy_specialists = max(0, total_specialists - free_specialists)

    success_percent = (
        0 if total_specialists == 0
        else int(100 * free_specialists / total_specialists)
    )

    total_assignments = ProjectAssignment.objects.count()
    successful_assignments = ProjectAssignment.objects.filter(
        status__in=[
            AssignmentStatus.ACCEPTED,
            AssignmentStatus.WORKING,
            AssignmentStatus.FINISHED,
        ]
    ).count()

    assignment_success_percent = (
        0 if total_assignments == 0
        else int(100 * successful_assignments / total_assignments)
    )

    avg_quality = (
        "Нет оценок"
        if total_reports == 0
        else f"{round(sum(QUALITY_LEVEL[report.quality] for report in Report.objects.all()) / total_reports, 1)} / 5"
    )

    project_report_items = Project.objects.select_related("manager").order_by("-id")

    specialist_report_items = SpecialistProfile.objects.select_related("user").order_by(
        "user__last_name",
        "user__first_name",
    )

    quality_feedback_report_items = (
        Project.objects.select_related("manager")
        .annotate(
            reports_count=Count("reports", distinct=True),
            feedback_count=Count("feedbacks", distinct=True),
        )
        .order_by("-id")
    )

    quality_feedback_report_items = [
        project
        for project in quality_feedback_report_items
        if project.reports_count > 0 or project.feedback_count > 0
    ]

    metrics = [
        {"label": "Количество проектов", "value": f"{total_projects}"},
        {"label": "Процент успешных назначений", "value": f"{assignment_success_percent} %"},
        {"label": "Средняя оценка клиентов", "value": avg_quality},
        {"label": "Отчеты", "value": f"{total_reports} шт."},
    ]

    pie_labels = ["Свободны", "Заняты"]
    pie_values = [free_specialists, busy_specialists]

    if total_specialists == 0:
        pie_labels = ["Нет данных"]
        pie_values = [1]

    return _page(
        request,
        "pages/analytics.html",
        "Аналитика и отчёты",
        "Сводные отчёты и метрики по системе.",
        metrics=metrics,
        pie_labels=pie_labels,
        pie_values=pie_values,
        success_percent=success_percent,
        project_report_items=project_report_items,
        specialist_report_items=specialist_report_items,
        quality_feedback_report_items=quality_feedback_report_items,
    )

def download_report_view(request, report_type, object_id):
    if report_type == "project":
        file_obj, filename = build_project_report_docx(object_id)
    elif report_type == "specialist":
        file_obj, filename = build_specialist_report_docx(object_id)
    elif report_type == "quality_feedback":
        file_obj, filename = build_quality_feedback_report_docx(object_id)
    else:
        raise Http404("Неизвестный тип отчета.")

    return FileResponse(
        file_obj,
        as_attachment=True,
        filename=filename,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

def profile_view(request):
    user = _current_user(request)
    if not user:
        messages.error(request, "Нет пользователя для отображения профиля.")
        return redirect("app:register")

    if request.method == "POST":
        user.first_name = (request.POST.get("first_name") or user.first_name).strip()
        user.last_name = (request.POST.get("last_name") or user.last_name).strip()
        user.middle_name = (request.POST.get("middle_name") or "").strip() or None
        user.email = (request.POST.get("email") or user.email).strip().lower()
        user.phone = (request.POST.get("phone") or user.phone).strip()
        user.save()
        messages.success(request, "Профиль обновлён.")
        return redirect("app:profile")

    profile = {
        "name": _full_name(user),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "middle_name": user.middle_name or "",
        "role": ROLE_LABELS.get(user.role, user.role),
        "email": user.email,
        "phone": user.phone,
    }
    return _page(request, "pages/profile.html", "Профиль пользователя", "Личные данные текущего пользователя.", profile=profile)
