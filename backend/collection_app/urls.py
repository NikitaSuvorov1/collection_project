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
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('dashboard/operator/', views.OperatorStatsView.as_view(), name='operator-stats'),
    path('dashboard/operator/<int:operator_id>/', views.OperatorStatsView.as_view(), name='operator-stats-detail'),
]
