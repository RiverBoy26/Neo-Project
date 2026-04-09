from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('specialists/', views.specialists_list_view, name='specialists_list'),
    path('specialists/<int:pk>/', views.specialist_detail_view, name='specialist_detail'),
    path('specialists/<int:pk>/edit/', views.specialist_edit_view, name='specialist_edit'),
    path('projects/', views.projects_list_view, name='projects_list'),
    path('projects/create/', views.project_edit_view, name='project_create'),
    path('projects/<int:pk>/', views.project_detail_view, name='project_detail'),
    path('projects/<int:pk>/edit/', views.project_edit_view, name='project_edit'),
    path('projects/<int:pk>/roles/', views.project_roles_view, name='project_roles'),
    path('roles/<int:role_id>/recommendations/', views.recommendations_view, name='recommendations'),
    path('assignments/', views.assignments_view, name='assignments'),
    path('workload/', views.workload_view, name='workload'),
    path('feedback/', views.feedback_view, name='feedback'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('profile/', views.profile_view, name='profile'),
]
