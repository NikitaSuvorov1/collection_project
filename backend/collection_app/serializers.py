from rest_framework import serializers
from .models import (
    Client, Credit, Payment, Intervention, Operator, ScoringResult, 
    Assignment, CreditApplication, CreditState, ClientBehaviorProfile,
    NextBestAction, SmartScript, ConversationAnalysis, ComplianceAlert, ReturnForecast
)
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']

class OperatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Operator
        fields = '__all__'

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = '__all__'

class CreditStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditState
        fields = '__all__'

class CreditSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    latest_state = serializers.SerializerMethodField()
    
    class Meta:
        model = Credit
        fields = '__all__'
    
    def get_latest_state(self, obj):
        state = obj.states.order_by('-state_date').first()
        if state:
            return CreditStateSerializer(state).data
        return None

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class InterventionSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.full_name', read_only=True)
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    
    class Meta:
        model = Intervention
        fields = '__all__'

class ScoringResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoringResult
        fields = '__all__'

class AssignmentSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.full_name', read_only=True)
    client_name = serializers.CharField(source='credit.client.full_name', read_only=True)
    client_phone = serializers.CharField(source='credit.client.phone_mobile', read_only=True)
    
    class Meta:
        model = Assignment
        fields = '__all__'

class CreditApplicationSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    decision_display = serializers.CharField(source='get_decision_display', read_only=True)
    
    class Meta:
        model = CreditApplication
        fields = '__all__'

# ===== KILLER FEATURES SERIALIZERS =====

class ClientBehaviorProfileSerializer(serializers.ModelSerializer):
    psychotype_display = serializers.CharField(source='get_psychotype_display', read_only=True)
    preferred_channel_display = serializers.CharField(source='get_preferred_channel_display', read_only=True)
    strategic_recommendation_display = serializers.CharField(source='get_strategic_recommendation_display', read_only=True)
    
    class Meta:
        model = ClientBehaviorProfile
        fields = '__all__'

class NextBestActionSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(source='get_recommended_channel_display', read_only=True)
    scenario_display = serializers.CharField(source='get_recommended_scenario_display', read_only=True)
    offer_display = serializers.CharField(source='get_recommended_offer_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = NextBestAction
        fields = '__all__'

class SmartScriptSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmartScript
        fields = '__all__'

class ConversationAnalysisSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationAnalysis
        fields = '__all__'

class ComplianceAlertSerializer(serializers.ModelSerializer):
    operator_name = serializers.CharField(source='operator.full_name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    alert_type_display = serializers.CharField(source='get_alert_type_display', read_only=True)
    
    class Meta:
        model = ComplianceAlert
        fields = '__all__'

class ReturnForecastSerializer(serializers.ModelSerializer):
    recommendation_display = serializers.CharField(source='get_recommendation_display', read_only=True)
    
    class Meta:
        model = ReturnForecast
        fields = '__all__'

# ===== COMPOSITE SERIALIZERS =====

class Client360Serializer(serializers.ModelSerializer):
    """Полный 360° профиль клиента"""
    behavior_profile = ClientBehaviorProfileSerializer(read_only=True)
    credits = serializers.SerializerMethodField()
    interventions = serializers.SerializerMethodField()
    total_debt = serializers.SerializerMethodField()
    total_overdue = serializers.SerializerMethodField()
    nba_recommendations = serializers.SerializerMethodField()
    latest_forecast = serializers.SerializerMethodField()
    
    class Meta:
        model = Client
        fields = '__all__'
    
    def get_credits(self, obj):
        credits = obj.credits.all()
        return CreditSerializer(credits, many=True).data
    
    def get_interventions(self, obj):
        interventions = obj.interventions.order_by('-datetime')[:20]
        return InterventionSerializer(interventions, many=True).data
    
    def get_total_debt(self, obj):
        total = 0
        for credit in obj.credits.all():
            state = credit.states.order_by('-state_date').first()
            if state:
                total += float(state.principal_debt)
        return total
    
    def get_total_overdue(self, obj):
        total = 0
        for credit in obj.credits.all():
            state = credit.states.order_by('-state_date').first()
            if state:
                total += float(state.overdue_principal)
        return total
    
    def get_nba_recommendations(self, obj):
        nbas = NextBestAction.objects.filter(client=obj, status='pending').order_by('-created_at')[:5]
        return NextBestActionSerializer(nbas, many=True).data
    
    def get_latest_forecast(self, obj):
        for credit in obj.credits.filter(status='overdue'):
            forecast = credit.forecasts.order_by('-calculated_at').first()
            if forecast:
                return ReturnForecastSerializer(forecast).data
        return None

class OperatorQueueSerializer(serializers.ModelSerializer):
    """Очередь оператора с расширенными данными"""
    client = serializers.SerializerMethodField()
    nba = serializers.SerializerMethodField()
    
    class Meta:
        model = Assignment
        fields = '__all__'
    
    def get_client(self, obj):
        client = obj.credit.client
        profile = getattr(client, 'behavior_profile', None)
        return {
            'id': client.id,
            'full_name': client.full_name,
            'phone_mobile': client.phone_mobile,
            'city': client.city,
            'psychotype': profile.psychotype if profile else 'unknown',
            'psychotype_label': profile.get_psychotype_display() if profile else 'Неизвестно',
        }
    
    def get_nba(self, obj):
        nba = NextBestAction.objects.filter(
            credit=obj.credit, status='pending'
        ).order_by('-created_at').first()
        if nba:
            return {
                'channel': nba.get_recommended_channel_display(),
                'scenario': nba.get_recommended_scenario_display(),
                'offer': nba.get_recommended_offer_display(),
                'urgency': nba.urgency,
                'confidence': nba.confidence_score,
                'reasoning': nba.reasoning,
            }
        return None
