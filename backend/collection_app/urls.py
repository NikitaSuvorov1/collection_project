from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from rest_framework.authtoken import views as drf_views

router = DefaultRouter()
router.register('clients', views.ClientViewSet)
router.register('credits', views.CreditViewSet)
router.register('payments', views.PaymentViewSet)
router.register('interventions', views.InterventionViewSet)
router.register('operators', views.OperatorViewSet)
router.register('scorings', views.ScoringResultViewSet, basename='scorings')
router.register('assignments', views.AssignmentViewSet)
router.register('applications', views.CreditApplicationViewSet)
router.register('credit-states', views.CreditStateViewSet)

# Killer Features endpoints
router.register('profiles', views.ClientBehaviorProfileViewSet)
router.register('nba', views.NextBestActionViewSet)
router.register('scripts', views.SmartScriptViewSet)
router.register('compliance-alerts', views.ComplianceAlertViewSet)
router.register('forecasts', views.ReturnForecastViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('api-token-auth/', drf_views.obtain_auth_token),
    
    # Dashboard endpoints
    path('dashboard/', views.DashboardFullView.as_view(), name='dashboard-full'),
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('dashboard/operator/', views.OperatorStatsView.as_view(), name='operator-stats'),
    path('dashboard/operator/<int:operator_id>/', views.OperatorStatsView.as_view(), name='operator-stats-detail'),
    
    # ML prediction endpoints
    path('overdue-prediction/', views.OverduePredictionView.as_view(), name='overdue-prediction'),
    
    # 230-ФЗ Compliance
    path('compliance/check/', views.ComplianceCheckView.as_view(), name='compliance-check'),
    path('compliance/bankruptcy/', views.BankruptcyCheckView.as_view(), name='bankruptcy-check'),
    path('compliance/summary/', views.ComplianceSummaryView.as_view(), name='compliance-summary'),
    
    # ML Models & Scoring
    path('ml/models/', views.MLModelMetricsView.as_view(), name='ml-models'),
    path('ml/models/<int:model_id>/', views.MLModelMetricsView.as_view(), name='ml-model-detail'),
    path('ml/train-overdue/', views.TrainOverdueModelView.as_view(), name='train-overdue-model'),
    path('ml/train-approval/', views.TrainApprovalModelView.as_view(), name='train-approval-model'),
    path('scoring/dashboard/', views.ScoringDashboardView.as_view(), name='scoring-dashboard'),
    
    # A/B Testing
    path('ab-test/results/', views.ABTestResultsView.as_view(), name='ab-test-results'),
    
    # Smart Distribution
    path('distribution/run/', views.SmartDistributionView.as_view(), name='distribution-run'),
    
    # Audit Log
    path('audit/', views.AuditLogView.as_view(), name='audit-log'),
    
    # Daily credit states (interpolated)
    path('credit-daily-states/', views.CreditDailyStatesView.as_view(), name='credit-daily-states'),
]
