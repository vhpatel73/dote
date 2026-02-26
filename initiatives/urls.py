from django.urls import path
from . import views

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('analysis/', views.BenefitAnalysisView.as_view(), name='benefit_analysis'),
    path('initiatives/', views.InitiativeListView.as_view(), name='initiative_list'),
    path('initiatives/create/', views.InitiativeCreateView.as_view(), name='initiative_create'),
    path('initiatives/<int:pk>/edit/', views.InitiativeUpdateView.as_view(), name='initiative_edit'),
    path('initiatives/<int:pk>/toast/', views.InitiativeToastView.as_view(), name='initiative_toast'),
    path('initiatives/<int:pk>/delete/', views.InitiativeDeleteView.as_view(), name='initiative_delete'),
    path('initiatives/<int:pk>/benefit/', views.RealizedBenefitEntryView.as_view(), name='benefit_entry'),
    path('csv/download/', views.CSVDownloadView.as_view(), name='csv_download'),
    path('csv/download/benefits/', views.BenefitCSVDownloadView.as_view(), name='benefit_csv_download'),
    path('csv/upload/', views.CSVUploadView.as_view(), name='csv_upload'),
    path('benefit/delete/<int:pk>/', views.RealizedBenefitDeleteView.as_view(), name='benefit_delete'),
    path('csv/sample/', views.SampleCSVDownloadView.as_view(), name='csv_sample'),
    path('webhook/report/', views.RealtimeReportingWebhookView.as_view(), name='webhook_report'),
    path('webhook/docs/', views.WebhookDocsView.as_view(), name='webhook_docs'),
    path('webhook/docs/<int:pk>/', views.WebhookDocsView.as_view(), name='webhook_docs_personal'),
    path('bulk-config/', views.BulkConfigView.as_view(), name='bulk_config'),
    path('audit/', views.AuditLogListView.as_view(), name='audit_list'),
    path('about/', views.AboutView.as_view(), name='about'),
    
    # Technology Configs
    path('technologies/', views.TechnologyListView.as_view(), name='technology_list'),
    path('technologies/create/', views.TechnologyCreateView.as_view(), name='technology_create'),
    path('technologies/<int:pk>/edit/', views.TechnologyUpdateView.as_view(), name='technology_edit'),
    path('technologies/<int:pk>/delete/', views.TechnologyDeleteView.as_view(), name='technology_delete'),
    path('technologies/<int:pk>/usage/', views.TechnologyUsageEntryView.as_view(), name='technology_usage_entry'),
    path('usage/delete/<int:pk>/', views.TechnologyUsageDeleteView.as_view(), name='technology_usage_delete'),
]
