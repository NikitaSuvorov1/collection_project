from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import (
    Client, Credit, Payment, Intervention, Operator, ScoringResult, 
    Assignment, CreditApplication, CreditState, ClientBehaviorProfile,
    NextBestAction, SmartScript, ConversationAnalysis, ComplianceAlert, ReturnForecast
)
from .serializers import (
    ClientSerializer, CreditSerializer, PaymentSerializer, InterventionSerializer,
    OperatorSerializer, ScoringResultSerializer, AssignmentSerializer, CreditApplicationSerializer,
    Client360Serializer, ClientBehaviorProfileSerializer, NextBestActionSerializer,
    SmartScriptSerializer, ComplianceAlertSerializer, ReturnForecastSerializer,
    OperatorQueueSerializer, CreditStateSerializer
)
from .ml.next_best_action import NextBestActionService
from .ml.psychotyping import PsychotypingService
from .ml.return_forecast import ReturnForecastService
from .ml.compliance import ComplianceService
from .ml.smart_scripts import SmartScriptService
from .ml.loan_predictor import predict_loan_approval, get_predictor


class IsDBAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_superuser


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.AllowAny]  # Для просмотра без авторизации
    
    @action(detail=True, methods=['get'])
    def profile_360(self, request, pk=None):
        """Полный 360° портрет клиента"""
        client = self.get_object()
        serializer = Client360Serializer(client)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def generate_nba(self, request, pk=None):
        """Генерация NBA рекомендаций для клиента"""
        client = self.get_object()
        nba_service = NextBestActionService()
        recommendations = nba_service.generate_recommendations(client)
        return Response({
            'client_id': client.id,
            'recommendations': recommendations
        })
    
    @action(detail=True, methods=['get'])
    def copilot_phrases(self, request, pk=None):
        """Получение фраз Copilot для работы с клиентом"""
        client = self.get_object()
        context = request.query_params.get('context', 'objection')
        objection = request.query_params.get('objection', '')
        
        scripts_service = SmartScriptService()
        phrases = scripts_service.suggest_phrases(client, context, objection)
        return Response({
            'client_id': client.id,
            'context': context,
            'phrases': phrases
        })


class CreditViewSet(viewsets.ModelViewSet):
    queryset = Credit.objects.select_related('client').all()
    serializer_class = CreditSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        qs = super().get_queryset()
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs
    
    @action(detail=True, methods=['get'])
    def forecast(self, request, pk=None):
        """Прогноз возврата по кредиту"""
        credit = self.get_object()
        forecast_service = ReturnForecastService()
        forecast = forecast_service.calculate_forecast(credit)
        return Response({
            'credit_id': credit.id,
            'forecast': forecast
        })


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [permissions.AllowAny]


class InterventionViewSet(viewsets.ModelViewSet):
    queryset = Intervention.objects.select_related('client', 'operator', 'credit').all()
    serializer_class = InterventionSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        qs = super().get_queryset()
        client_id = self.request.query_params.get('client_id', None)
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs.order_by('-datetime')
    
    def perform_create(self, serializer):
        intervention = serializer.save()
        # Проверка compliance после создания интервенции
        compliance_service = ComplianceService()
        alerts = compliance_service.check_intervention(intervention)
        # Алерты автоматически сохраняются сервисом


class OperatorViewSet(viewsets.ModelViewSet):
    queryset = Operator.objects.all()
    serializer_class = OperatorSerializer
    permission_classes = [permissions.AllowAny]


class CreditStateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CreditState.objects.select_related('credit', 'client').all()
    serializer_class = CreditStateSerializer
    permission_classes = [permissions.AllowAny]


class ScoringResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ScoringResult.objects.all()
    serializer_class = ScoringResultSerializer
    permission_classes = [permissions.AllowAny]


class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.select_related('credit__client', 'operator').all()
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        qs = super().get_queryset()
        operator_id = self.request.query_params.get('operator_id', None)
        is_active = self.request.query_params.get('is_active', None)
        
        if operator_id:
            qs = qs.filter(operator_id=operator_id)
        if is_active:
            qs = qs.filter(is_active=True)
        
        return qs.order_by('-assigned_at')
    
    @action(detail=False, methods=['get'])
    def my_queue(self, request):
        """Получить очередь текущего оператора с NBA"""
        try:
            operator = Operator.objects.get(user=request.user)
        except Operator.DoesNotExist:
            return Response({'error': 'Оператор не найден'}, status=404)
        
        assignments = Assignment.objects.filter(
            operator=operator, 
            is_active=True
        ).select_related('credit__client').order_by('priority', '-assigned_at')
        
        serializer = OperatorQueueSerializer(assignments, many=True)
        return Response(serializer.data)


class CreditApplicationViewSet(viewsets.ModelViewSet):
    queryset = CreditApplication.objects.select_related('client').all()
    serializer_class = CreditApplicationSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'predict_approval']:
            return [permissions.AllowAny()]
        return super().get_permissions()
    
    def list(self, request):
        """Получить все заявки с прогнозами"""
        queryset = self.get_queryset().order_by('-created_at')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def predict_approval(self, request):
        """
        Прогнозирование вероятности одобрения кредитной заявки.
        
        Принимает данные клиента и параметры заявки, возвращает:
        - approved_probability: вероятность одобрения (0-1)
        - decision: рекомендуемое решение (approved/rejected)
        - confidence: уверенность в решении
        - risk_factors: список факторов риска
        
        Пример запроса:
        POST /api/applications/predict_approval/
        {
            "client_id": 123,  // опционально, если указан - берёт данные клиента из БД
            "loan_amount": 500000,
            "loan_term": 36,
            // или вручную все данные:
            "gender": "M",
            "marital_status": "married",
            "employment": "employed",
            "income": 100000,
            "monthly_expenses": 30000,
            "children_count": 2,
            "credit_history": 1
        }
        """
        data = request.data.copy()
        
        # Если указан client_id - получаем данные клиента из БД
        client_id = data.get('client_id')
        if client_id:
            try:
                client = Client.objects.get(id=client_id)
                
                # Проверяем кредитную историю
                has_overdue = Credit.objects.filter(
                    client=client,
                    status__in=['overdue', 'default']
                ).exists()
                
                # Заполняем данные из профиля клиента
                data.setdefault('gender', client.gender)
                data.setdefault('marital_status', client.marital_status)
                data.setdefault('employment', client.employment)
                data.setdefault('income', float(client.income))
                data.setdefault('monthly_expenses', float(client.monthly_expenses))
                data.setdefault('children_count', client.children_count)
                data.setdefault('credit_history', 0 if has_overdue else 1)
                data.setdefault('region', client.region or 'unknown')
                
            except Client.DoesNotExist:
                return Response(
                    {'error': 'Клиент не найден'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Проверяем обязательные поля
        loan_amount = data.get('loan_amount')
        loan_term = data.get('loan_term', 12)
        
        if not loan_amount:
            return Response(
                {'error': 'Укажите сумму кредита (loan_amount)'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Формируем данные для предсказания
        prediction_data = {
            'gender': data.get('gender', 'M'),
            'marital_status': data.get('marital_status', 'single'),
            'employment': data.get('employment', 'employed'),
            'income': float(data.get('income', 0)),
            'monthly_expenses': float(data.get('monthly_expenses', 0)),
            'loan_amount': float(loan_amount),
            'loan_term': int(loan_term),
            'children_count': int(data.get('children_count', 0)),
            'credit_history': int(data.get('credit_history', 1)),
            'region': data.get('region', 'unknown')
        }
        
        # Получаем предсказание
        result = predict_loan_approval(prediction_data)
        
        return Response(result)
    
    @action(detail=True, methods=['post'])
    def process_application(self, request, pk=None):
        """
        Обработка заявки: прогнозирование и сохранение результата.
        
        POST /api/applications/{id}/process_application/
        """
        application = self.get_object()
        client = application.client
        
        # Проверяем кредитную историю
        has_overdue = Credit.objects.filter(
            client=client,
            status__in=['overdue', 'default']
        ).exists()
        
        prediction_data = {
            'gender': client.gender,
            'marital_status': client.marital_status,
            'employment': client.employment,
            'income': float(client.income),
            'monthly_expenses': float(client.monthly_expenses),
            'loan_amount': float(application.amount),
            'loan_term': application.requested_term,
            'children_count': client.children_count,
            'credit_history': 0 if has_overdue else 1,
            'region': client.region or 'unknown'
        }
        
        result = predict_loan_approval(prediction_data)
        
        # Сохраняем результаты в заявку
        application.approved_probability = result['approved_probability']
        application.overdue_risk_probability = 1 - result['approved_probability']  # упрощённо
        
        # Автоматическое решение при высокой уверенности
        auto_decide = request.data.get('auto_decide', False)
        if auto_decide and result['confidence'] > 0.7:
            application.decision = result['decision']
            application.decision_date = timezone.now()
        
        application.save()
        
        return Response({
            'application_id': application.id,
            'prediction': result,
            'auto_decision_applied': auto_decide and result['confidence'] > 0.7
        })


# ===== KILLER FEATURES VIEWSETS =====

class ClientBehaviorProfileViewSet(viewsets.ModelViewSet):
    queryset = ClientBehaviorProfile.objects.select_related('client').all()
    serializer_class = ClientBehaviorProfileSerializer
    
    @action(detail=False, methods=['post'])
    def analyze_client(self, request):
        """Анализ психотипа клиента"""
        client_id = request.data.get('client_id')
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return Response({'error': 'Клиент не найден'}, status=404)
        
        psycho_service = PsychotypingService()
        profile = psycho_service.analyze_client(client)
        return Response(profile)


class NextBestActionViewSet(viewsets.ModelViewSet):
    queryset = NextBestAction.objects.select_related('client', 'credit').all()
    serializer_class = NextBestActionSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        client_id = self.request.query_params.get('client_id', None)
        status_filter = self.request.query_params.get('status', None)
        
        if client_id:
            qs = qs.filter(client_id=client_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        
        return qs.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Отметить рекомендацию как выполненную"""
        nba = self.get_object()
        nba.status = 'executed'
        nba.executed_at = timezone.now()
        nba.save()
        return Response({'status': 'executed'})
    
    @action(detail=True, methods=['post'])
    def skip(self, request, pk=None):
        """Пропустить рекомендацию"""
        nba = self.get_object()
        nba.status = 'skipped'
        nba.save()
        return Response({'status': 'skipped'})


class SmartScriptViewSet(viewsets.ModelViewSet):
    queryset = SmartScript.objects.all()
    serializer_class = SmartScriptSerializer
    
    @action(detail=False, methods=['get'])
    def for_context(self, request):
        """Получить скрипты для контекста"""
        context_type = request.query_params.get('context', 'objection')
        psychotype = request.query_params.get('psychotype', None)
        
        qs = self.queryset.filter(context_type=context_type, is_active=True)
        if psychotype:
            qs = qs.filter(Q(target_psychotype=psychotype) | Q(target_psychotype=''))
        
        qs = qs.order_by('-success_rate')[:10]
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class ComplianceAlertViewSet(viewsets.ModelViewSet):
    queryset = ComplianceAlert.objects.select_related('operator', 'intervention').all()
    serializer_class = ComplianceAlertSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        is_resolved = self.request.query_params.get('is_resolved', None)
        severity = self.request.query_params.get('severity', None)
        
        if is_resolved is not None:
            qs = qs.filter(is_resolved=is_resolved == 'true')
        if severity:
            qs = qs.filter(severity=severity)
        
        return qs.order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Закрыть алерт"""
        alert = self.get_object()
        resolution = request.data.get('resolution', '')
        alert.is_resolved = True
        alert.resolution_notes = resolution
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.save()
        return Response({'status': 'resolved'})


class ReturnForecastViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReturnForecast.objects.select_related('credit__client').all()
    serializer_class = ReturnForecastSerializer
    
    def get_queryset(self):
        qs = super().get_queryset()
        credit_id = self.request.query_params.get('credit_id', None)
        if credit_id:
            qs = qs.filter(credit_id=credit_id)
        return qs.order_by('-calculated_at')


# ===== DASHBOARD API =====

class DashboardStatsView(APIView):
    """Статистика для дашборда"""
    
    def get(self, request):
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Общая статистика
        total_clients = Client.objects.count()
        total_credits = Credit.objects.count()
        overdue_credits = Credit.objects.filter(status='overdue').count()
        
        # Статистика за месяц
        payments_this_month = Payment.objects.filter(
            payment_date__gte=month_start
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        interventions_today = Intervention.objects.filter(
            datetime__date=today
        ).count()
        
        # Статистика по каналам
        channel_stats = Intervention.objects.filter(
            datetime__date__gte=month_start
        ).values('channel').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Статистика результатов
        result_stats = Intervention.objects.filter(
            datetime__date__gte=month_start
        ).values('result').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Compliance алерты
        active_alerts = ComplianceAlert.objects.filter(is_resolved=False).count()
        
        # Эффективность NBA
        nba_stats = NextBestAction.objects.filter(
            created_at__date__gte=month_start
        ).values('status').annotate(count=Count('id'))
        
        return Response({
            'summary': {
                'total_clients': total_clients,
                'total_credits': total_credits,
                'overdue_credits': overdue_credits,
                'payments_this_month': float(payments_this_month),
                'interventions_today': interventions_today,
                'active_compliance_alerts': active_alerts,
            },
            'channel_stats': list(channel_stats),
            'result_stats': list(result_stats),
            'nba_stats': list(nba_stats),
        })


class OperatorStatsView(APIView):
    """Статистика оператора"""
    
    def get(self, request, operator_id=None):
        if operator_id is None:
            try:
                operator = Operator.objects.get(user=request.user)
            except Operator.DoesNotExist:
                return Response({'error': 'Оператор не найден'}, status=404)
        else:
            try:
                operator = Operator.objects.get(id=operator_id)
            except Operator.DoesNotExist:
                return Response({'error': 'Оператор не найден'}, status=404)
        
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Интервенции за сегодня
        interventions_today = Intervention.objects.filter(
            operator=operator,
            datetime__date=today
        ).count()
        
        # Успешные контакты
        successful_contacts = Intervention.objects.filter(
            operator=operator,
            datetime__date=today,
            result__in=['promise_to_pay', 'partial_payment', 'full_payment']
        ).count()
        
        # Платежи благодаря оператору
        payments_today = Payment.objects.filter(
            credit__assignments__operator=operator,
            payment_date=today
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Активные назначения
        active_assignments = Assignment.objects.filter(
            operator=operator,
            is_active=True
        ).count()
        
        # Compliance статус
        compliance_alerts = ComplianceAlert.objects.filter(
            operator=operator,
            is_resolved=False
        ).count()
        
        return Response({
            'operator_id': operator.id,
            'operator_name': operator.full_name,
            'today': {
                'interventions': interventions_today,
                'successful_contacts': successful_contacts,
                'payments_collected': float(payments_today),
            },
            'queue': {
                'active_assignments': active_assignments,
            },
            'compliance': {
                'active_alerts': compliance_alerts,
            }
        })
