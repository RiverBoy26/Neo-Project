from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from db.models import (
    AssignmentStatus,
    Level,
    Profession,
    Project,
    ProjectAssignment,
    ProjectRequirement,
    ProjectRequirementDesiredSkill,
    ProjectRequirementRequiredSkill,
    ProjectStatus,
    Role,
    Skill,
    SpecialistProfile,
    User,
    UserSkill,
)


class Command(BaseCommand):
    help = "Заполняет БД демонстрационными пользователями, проектами и назначениями."

    @transaction.atomic
    def handle(self, *args, **options):
        admin, _ = User.objects.get_or_create(
            email="admin@neo.local",
            defaults={
                "first_name": "Анна",
                "last_name": "Соколова",
                "middle_name": "Игоревна",
                "phone": "+79990000001",
                "role": Role.ADMIN,
            },
        )

        manager1, _ = User.objects.get_or_create(
            email="manager1@neo.local",
            defaults={
                "first_name": "Егор",
                "last_name": "Ковалёв",
                "middle_name": "Андреевич",
                "phone": "+79990000002",
                "role": Role.PROJECT_MANAGER,
            },
        )
        manager2, _ = User.objects.get_or_create(
            email="manager2@neo.local",
            defaults={
                "first_name": "Мария",
                "last_name": "Лебедева",
                "middle_name": "Сергеевна",
                "phone": "+79990000003",
                "role": Role.PROJECT_MANAGER,
            },
        )

        specs = [
            {
                "email": "ivan@neo.local",
                "first_name": "Иван", "last_name": "Петров", "middle_name": "Олегович",
                "phone": "+79990000011", "profession": Profession.BACKEND, "level": Level.SENIOR, "exp": 6,
                "skills": [Skill.PYTHON, Skill.DJANGO, Skill.DOCKER], "is_busy": False,
            },
            {
                "email": "olga@neo.local",
                "first_name": "Ольга", "last_name": "Ильина", "middle_name": "Викторовна",
                "phone": "+79990000012", "profession": Profession.FRONTEND, "level": Level.MIDDLE, "exp": 4,
                "skills": [Skill.DOCKER], "is_busy": False,
            },
            {
                "email": "nikita@neo.local",
                "first_name": "Никита", "last_name": "Орлов", "middle_name": "Дмитриевич",
                "phone": "+79990000013", "profession": Profession.QA, "level": Level.MIDDLE, "exp": 3,
                "skills": [Skill.DOCKER], "is_busy": True,
            },
        ]

        created_specs = []
        for spec in specs:
            user, _ = User.objects.get_or_create(
                email=spec["email"],
                defaults={
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                    "middle_name": spec["middle_name"],
                    "phone": spec["phone"],
                    "role": Role.SPECIALIST,
                },
            )
            SpecialistProfile.objects.update_or_create(
                user=user,
                defaults={
                    "experience_years": spec["exp"],
                    "profession": spec["profession"],
                    "level": spec["level"],
                    "is_busy": spec["is_busy"],
                },
            )
            UserSkill.objects.filter(user=user).delete()
            UserSkill.objects.bulk_create([UserSkill(user=user, skill=s) for s in spec["skills"]])
            created_specs.append(user)

        project1, _ = Project.objects.get_or_create(
            name="Neo Staffing Platform",
            defaults={
                "description": "Платформа для управления распределением специалистов по проектам.",
                "start_date": "2026-04-19",
                "end_date": "2026-05-20",
                "budget": Decimal("4500000.00"),
                "expected_result": "Рабочая система с модулем рекомендаций и аналитикой.",
                "manager": manager1,
                "status": ProjectStatus.IN_PROGRESS,
            },
        )
        req1, _ = ProjectRequirement.objects.get_or_create(
            project=project1,
            profession=Profession.BACKEND,
            required_level=Level.MIDDLE,
            defaults={
                "desired_level": Level.SENIOR,
                "specialists_count": 2,
            },
        )
        ProjectRequirementRequiredSkill.objects.get_or_create(project_requirement=req1, skill=Skill.PYTHON)
        ProjectRequirementRequiredSkill.objects.get_or_create(project_requirement=req1, skill=Skill.DJANGO)
        ProjectRequirementDesiredSkill.objects.get_or_create(project_requirement=req1, skill=Skill.DOCKER)

        project2, _ = Project.objects.get_or_create(
            name="QA Automation Pilot",
            defaults={
                "description": "Пилот по автоматизации тестирования.",
                "start_date": "2026-04-25",
                "end_date": "2026-06-01",
                "budget": Decimal("1800000.00"),
                "expected_result": "Набор smoke/regression сценариев и отчёт по качеству.",
                "manager": manager2,
                "status": ProjectStatus.NOT_STARTED,
            },
        )
        req2, _ = ProjectRequirement.objects.get_or_create(
            project=project2,
            profession=Profession.QA,
            required_level=Level.MIDDLE,
            defaults={
                "desired_level": Level.SENIOR,
                "specialists_count": 1,
            },
        )
        ProjectRequirementRequiredSkill.objects.get_or_create(project_requirement=req2, skill=Skill.DOCKER)

        ProjectAssignment.objects.get_or_create(
            project=project1,
            user=created_specs[0],
            defaults={
                "role": Role.SPECIALIST,
                "status": AssignmentStatus.WORKING,
                "start_date": "2026-04-19",
                "end_date": "2026-05-20",
                "assigned_by": manager1,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            "Готово. Созданы демо-пользователи: admin@neo.local, manager1@neo.local, manager2@neo.local, ivan@neo.local, olga@neo.local, nikita@neo.local"
        ))
