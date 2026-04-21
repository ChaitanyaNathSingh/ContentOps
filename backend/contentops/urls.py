from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from tracker import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='tracker/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    path('', views.dashboard, name='dashboard'),
    path('plan/new/', views.entry_create, {'kind': 'plan'}, name='plan_new'),
    path('update/new/', views.entry_create, {'kind': 'update'}, name='update_new'),
    path('entries/status/', views.update_status, name='update_status'),
    path('api/extra-tasks/', views.api_extra_tasks, name='api_extra_tasks'),
    path('export/xlsx/', views.export_xlsx, name='export_xlsx'),
    path('members/', views.members_list, name='members_list'),
    path('members/<int:member_id>/', views.member_detail, name='member_detail'),
    path('reports/', views.reports, name='reports'),
    path('content-requests/', views.content_requests, name='content_requests'),

    # AE daily updates
    path('ae/daily/', views.ae_daily, name='ae_daily'),
    path('ae/daily/submit/', views.ae_daily_submit, name='ae_daily_submit'),
    path('ae/daily/export/', views.ae_daily_export, name='ae_daily_export'),

    # Slack intake API
    path('api/intake/slack', views.api_intake_slack, name='api_intake_slack'),
    path('api/health', views.api_health, name='api_health'),
]
