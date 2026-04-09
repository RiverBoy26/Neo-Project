from django.db import models
from django.db.models import F, Q
from django.utils import timezone


# =========================
# Enums вместо reference tables
# =========================

class Role(models.TextChoices):
    ADMIN = "admin", "admin"
    SPECIALIST = "specialist", "specialist"
    PROJECT_MANAGER = "project_manager", "project_manager"
    CUSTOMER = "customer", "customer"


class Profession(models.TextChoices):
    PRODUCT_MANAGER = "product_manager", "Product Manager"
    FRONTEND_DEVELOPER = "frontend_developer", "Frontend Developer"
    BACKEND_DEVELOPER = "backend_developer", "Backend Developer"
    FULLSTACK_DEVELOPER = "fullstack_developer", "Full-stack Developer"
    MOBILE_DEVELOPER = "mobile_developer", "Mobile Developer"
    CRM_ERP_DEVELOPER = "crm_erp_developer", "CRM / ERP Developer"
    QA_ENGINEER = "qa_engineer", "QA Engineer"
    TEST_AUTOMATION_ENGINEER = "test_automation_engineer", "Test Automation Engineer"
    DEVOPS_ENGINEER = "devops_engineer", "DevOps Engineer"
    AI_ENGINEER = "ai_engineer", "AI Engineer"
    DATA_ANALYST = "data_analyst", "Data Analyst"
    BI_DEVELOPER = "bi_developer", "BI Developer"
    DATA_ENGINEER = "data_engineer", "Data Engineer"
    DATA_SCIENTIST = "data_scientist", "Data Scientist"
    SECURITY_ENGINEER = "security_engineer", "Security Engineer"
    CLOUD_ENGINEER = "cloud_engineer", "Cloud Engineer"
    RELEASE_MANAGER = "release_manager", "Release Manager"


class Level(models.TextChoices):
    JUNIOR = "junior", "junior"
    MIDDLE = "middle", "middle"
    SENIOR = "senior", "senior"


class Skill(models.TextChoices):
    TYPESCRIPT = "typescript", "TypeScript"
    JAVASCRIPT = "javascript", "JavaScript"
    PYTHON = "python", "Python"
    SQL = "sql", "SQL"
    GO = "go", "Go"
    JAVA = "java", "Java"
    CSHARP = "csharp", "C#"
    RUST = "rust", "Rust"
    BASH_SHELL = "bash_shell", "Bash / Shell"
    HTML_CSS = "html_css", "HTML / CSS"
    PHP = "php", "PHP"
    KOTLIN = "kotlin", "Kotlin"
    SWIFT = "swift", "Swift"
    CPP = "cpp", "C++"
    NODE_JS = "node_js", "Node.js"
    REACT = "react", "React"
    VUE_JS = "vue_js", "Vue.js"
    VITE = "vite", "Vite"
    FLUTTER = "flutter", "Flutter"
    GRPC = "grpc", "gRPC"
    SQLALCHEMY = "sqlalchemy", "SQLAlchemy"
    MONGODB = "mongodb", "MongoDB"
    CLICKHOUSE = "clickhouse", "ClickHouse"
    KAFKA = "kafka", "Kafka"
    POSTGRESQL = "postgresql", "PostgreSQL"
    MYSQL = "mysql", "MySQL"
    DOCKER = "docker", "Docker"


class ProjectStatus(models.TextChoices):
    NOT_STARTED = "не начат", "не начат"
    IN_PROGRESS = "в процессе", "в процессе"
    COMPLETED = "завершен", "завершен"


class AssignmentStatus(models.TextChoices):
    RECOMMENDED = "рекомендован", "рекомендован"
    OFFERED = "предложен", "предложен"
    ACCEPTED = "согласился", "согласился"
    WORKING = "работает", "работает"
    FINISHED = "завершил", "завершил"


class QualityLevel(models.TextChoices):
    AWFUL = "ужасно", "ужасно"
    BAD = "плохо", "плохо"
    NORMAL = "нормально", "нормально"
    GOOD = "хорошо", "хорошо"
    EXCELLENT = "отлично", "отлично"


# =========================
# Main tables
# =========================

class User(models.Model):
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(max_length=255, unique=True)
    phone = models.CharField(max_length=30)
    role = models.CharField(max_length=50, choices=Role.choices, db_index=True)

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.last_name} {self.first_name}"


class SpecialistProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="specialist_profile",
        limit_choices_to={"role": Role.SPECIALIST},
    )
    experience_years = models.PositiveIntegerField()
    profession = models.CharField(max_length=50, choices=Profession.choices, db_index=True)
    level = models.CharField(max_length=50, choices=Level.choices, db_index=True)
    is_busy = models.BooleanField(default=False)
    busy_until = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "specialist_profile"
        constraints = [
            models.CheckConstraint(
                check=Q(experience_years__gte=0),
                name="chk_specialist_profile_experience_years",
            ),
        ]

    def __str__(self):
        return f"Профиль специалиста: {self.user}"


class UserSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_skills")
    skill = models.CharField(max_length=100, choices=Skill.choices, db_index=True)

    class Meta:
        db_table = "user_skills"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "skill"],
                name="uq_user_skills_user_skill",
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.skill}"


class Project(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    expected_result = models.TextField()
    manager = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="managed_projects",
        limit_choices_to={"role": Role.PROJECT_MANAGER},
    )
    status = models.CharField(max_length=50, choices=ProjectStatus.choices, db_index=True)

    class Meta:
        db_table = "projects"
        constraints = [
            models.CheckConstraint(
                check=Q(budget__gte=0),
                name="chk_projects_budget",
            ),
            models.CheckConstraint(
                check=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="chk_projects_dates",
            ),
        ]

    def __str__(self):
        return self.name


class ProjectRequirement(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="requirements",
    )
    profession = models.CharField(max_length=50, choices=Profession.choices, db_index=True)
    required_level = models.CharField(max_length=50, choices=Level.choices, db_index=True)
    desired_level = models.CharField(
        max_length=50,
        choices=Level.choices,
        null=True,
        blank=True,
        db_index=True,
    )
    specialists_count = models.PositiveIntegerField()

    class Meta:
        db_table = "project_requirements"
        constraints = [
            models.CheckConstraint(
                check=Q(specialists_count__gt=0),
                name="chk_project_requirements_specialists_count",
            ),
        ]

    def __str__(self):
        return f"{self.project.name} / {self.profession}"


class ProjectRequirementRequiredSkill(models.Model):
    project_requirement = models.ForeignKey(
        ProjectRequirement,
        on_delete=models.CASCADE,
        related_name="required_skills",
    )
    skill = models.CharField(max_length=100, choices=Skill.choices, db_index=True)

    class Meta:
        db_table = "project_requirement_required_skills"
        constraints = [
            models.UniqueConstraint(
                fields=["project_requirement", "skill"],
                name="uq_req_required_skills",
            ),
        ]

    def __str__(self):
        return f"Required: {self.project_requirement} — {self.skill}"


class ProjectRequirementDesiredSkill(models.Model):
    project_requirement = models.ForeignKey(
        ProjectRequirement,
        on_delete=models.CASCADE,
        related_name="desired_skills",
    )
    skill = models.CharField(max_length=100, choices=Skill.choices, db_index=True)

    class Meta:
        db_table = "project_requirement_desired_skills"
        constraints = [
            models.UniqueConstraint(
                fields=["project_requirement", "skill"],
                name="uq_req_desired_skills",
            ),
        ]

    def __str__(self):
        return f"Desired: {self.project_requirement} — {self.skill}"


class ProjectAssignment(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_assignments",
    )
    role = models.CharField(max_length=50, choices=Role.choices, db_index=True)
    status = models.CharField(max_length=50, choices=AssignmentStatus.choices, db_index=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="created_assignments",
    )
    skill_match_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "project_assignments"
        constraints = [
            models.CheckConstraint(
                check=Q(end_date__isnull=True) | Q(end_date__gte=F("start_date")),
                name="chk_project_assignments_dates",
            ),
            models.CheckConstraint(
                check=Q(skill_match_percent__isnull=True)
                | (Q(skill_match_percent__gte=0) & Q(skill_match_percent__lte=100)),
                name="chk_project_assignments_skill_match_percent",
            ),
        ]

    def __str__(self):
        return f"{self.user} -> {self.project}"


class Feedback(models.Model):
    text = models.TextField()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    role = models.CharField(max_length=50, choices=Role.choices, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "feedback"

    def __str__(self):
        return f"Feedback #{self.pk}"


class Report(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="reports",
    )
    admin = models.ForeignKey(
        User,
        on_delete=models.RESTRICT,
        related_name="reports_created",
        limit_choices_to={"role": Role.ADMIN},
    )
    total_hours = models.PositiveIntegerField()
    quality = models.CharField(max_length=50, choices=QualityLevel.choices, db_index=True)
    recommendations = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "reports"
        constraints = [
            models.CheckConstraint(
                check=Q(total_hours__gte=0),
                name="chk_reports_total_hours",
            ),
        ]

    def __str__(self):
        return f"Report #{self.pk} / {self.project.name}"