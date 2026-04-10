from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .api_views import (
    DashboardAnalyticsView,
    FeedbackViewSet,
    ProjectAnalyticsView,
    ProjectAssignmentViewSet,
    ProjectRequirementViewSet,
    ProjectViewSet,
    ReportViewSet,
    SessionLoginView,
    SessionLogoutView,
    SessionMeView,
    SkillCatalogView,
    SpecialistViewSet,
    UserViewSet,
    WorkloadAnalyticsView,
    availability_overview,
)

app_name = 'app'

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'specialists', SpecialistViewSet, basename='specialists')
router.register(r'projects', ProjectViewSet, basename='projects')
router.register(r'project-roles', ProjectRequirementViewSet, basename='project-roles')
router.register(r'assignments', ProjectAssignmentViewSet, basename='assignments')
router.register(r'feedback-items', FeedbackViewSet, basename='feedback-items')
router.register(r'reports', ReportViewSet, basename='reports')

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('specialists/', views.specialists_list_view, name='specialists_list'),
    path('specialists/<int:pk>/', views.specialist_detail_view, name='specialist_detail'),
    path('specialists/<int:pk>/edit/', views.specialist_edit_view, name='specialist_edit'),
    path('projects/', views.projects_list_view, name='projects_list'),
    path('projects/create/', views.project_create_view, name='project_create'),
    path('projects/<int:pk>/', views.project_detail_view, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_edit_view, name='project_edit'),
    path('projects/<int:pk>/roles/', views.project_roles_view, name='project_roles'),
    path('roles/<int:role_id>/recommendations/', views.recommendations_view, name='recommendations'),
    path('assignments/', views.assignments_view, name='assignments'),
    path('workload/', views.workload_view, name='workload'),
    path('feedback/', views.feedback_view, name='feedback'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('profile/', views.profile_view, name='profile'),

    path('api/auth/login', SessionLoginView.as_view(), name='api-login'),
    path('api/auth/logout', SessionLogoutView.as_view(), name='api-logout'),
    path('api/auth/me', SessionMeView.as_view(), name='api-me'),
    path('api/skills', SkillCatalogView.as_view(), name='api-skills'),
    path('api/availability', availability_overview, name='api-availability'),
    path('api/workload', WorkloadAnalyticsView.as_view(), name='api-workload'),
    path('api/analytics/dashboard', DashboardAnalyticsView.as_view(), name='api-analytics-dashboard'),
    path('api/analytics/projects/<int:pk>', ProjectAnalyticsView.as_view(), name='api-analytics-project-detail'),
    path('api/', include(router.urls)),

    path("reports/download/<str:report_type>/<int:object_id>/", views.download_report_view, name="download_report")
]
