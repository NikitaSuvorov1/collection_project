from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.db.models import Sum, Count, Q, Avg, F
from django.utils import timezone
from datetime import timedelta, date as date_type
from decimal import Decimal

from .models import (
    Client, Credit, Payment, Intervention, Operator, ScoringResult, 
    Assignment, CreditApplication, CreditState, ClientBehaviorProfile,
    NextBestAction, SmartScript, ConversationAnalysis, ComplianceAlert, ReturnForecast,
    BankruptcyCheck, MLModelVersion, AuditLog, ViolationLog,
)
from .serializers import (
    ClientSerializer, CreditSerializer, PaymentSerializer, InterventionSerializer,
    OperatorSerializer, ScoringResultSerializer, AssignmentSerializer, CreditApplicationSerializer,
    Client360Serializer, ClientBehaviorProfileSerializer, NextBestActionSerializer,
    SmartScriptSerializer, ComplianceAlertSerializer, ReturnForecastSerializer,
    OperatorQueueSerializer, CreditStateSerializer,
    BankruptcyCheckSerializer, MLModelVersionSerializer, AuditLogSerializer,
    ViolationLogSerializer,
)
from .ml.next_best_action import NextBestActionService
from .ml.psychotyping import PsychotypingService
from .ml.return_forecast import ReturnForecastService
from .ml.compliance import ComplianceService
from .ml.smart_scripts import SmartScriptService
from .ml.loan_predictor import predict_loan_approval, get_predictor
from .ml.overdue_predictor import predict_risk, predict_risk_batch
from .services.compliance_230fz import can_contact, log_compliance_violation, check_bankruptcy, validate_intervention, get_compliance_summary


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
            # Поддержка нескольких статусов через запятую: ?status=overdue,default
            statuses = [s.strip() for s in status_filter.split(',')]
            qs = qs.filter(status__in=statuses)
        client_id = self.request.query_params.get('client', None)
        if client_id:
            qs = qs.filter(client_id=client_id)
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

    def get_queryset(self):
        qs = super().get_queryset()
        credit_id = self.request.query_params.get('credit', None)
        if credit_id:
            qs = qs.filter(credit_id=credit_id)
        client_id = self.request.query_params.get('client', None)
        if client_id:
            qs = qs.filter(credit__client_id=client_id)
        return qs.order_by('-payment_date')


class InterventionViewSet(viewsets.ModelViewSet):
    queryset = Intervention.objects.select_related('client', 'operator', 'credit').all()
    serializer_class = InterventionSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        qs = super().get_queryset()
        client_id = self.request.query_params.get('client_id') or self.request.query_params.get('client')
        if client_id:
            qs = qs.filter(client_id=client_id)
        ordering = self.request.query_params.get('ordering', '-datetime')
        return qs.order_by(ordering)
    
    def perform_create(self, serializer):
        # === 230-ФЗ: Предварительная проверка перед созданием интервенции ===
        client_id = serializer.validated_data.get('client_id') or (
            serializer.validated_data.get('client').id if serializer.validated_data.get('client') else None
        )
        contact_type = serializer.validated_data.get('intervention_type', 'phone')
        operator_id = serializer.validated_data.get('operator_id') or (
            serializer.validated_data.get('operator').id if serializer.validated_data.get('operator') else None
        )

        if client_id:
            result = can_contact(client_id, contact_type)
            if not result['allowed']:
                # Логируем блокировку
                if operator_id:
                    log_compliance_violation(client_id, operator_id, result['violations'])
                # Аудит
                AuditLog.objects.create(
                    action='contact_blocked',
                    operator_id=operator_id,
                    client_id=client_id,
                    severity='warning',
                    details={
                        'reason': result['reason'],
                        'violations': result['violations'],
                        'contact_type': contact_type,
                    },
                )
                raise DRFValidationError({
                    'compliance_error': True,
                    'message': f'230-ФЗ: {result["reason"]}',
                    'violations': result['violations'],
                    'limits': result.get('limits'),
                    'counts': result.get('counts'),
                })

        intervention = serializer.save()

        # Аудит: успешное создание
        AuditLog.objects.create(
            action='intervention_create',
            operator_id=operator_id,
            client_id=client_id,
            severity='info',
            details={
                'intervention_id': intervention.id,
                'type': contact_type,
                'status': intervention.status,
            },
        )

        # Проверка compliance после создания интервенции
        try:
            compliance_service = ComplianceService()
            if hasattr(compliance_service, 'check_intervention'):
                alerts = compliance_service.check_intervention(intervention)
        except Exception:
            pass  # Compliance check is optional


class OperatorViewSet(viewsets.ModelViewSet):
    queryset = Operator.objects.all()
    serializer_class = OperatorSerializer
    permission_classes = [permissions.AllowAny]


class CreditStateViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CreditState.objects.select_related('credit', 'client').all()
    serializer_class = CreditStateSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        credit_id = self.request.query_params.get('credit', None)
        if credit_id:
            qs = qs.filter(credit_id=credit_id)
        client_id = self.request.query_params.get('client', None)
        if client_id:
            qs = qs.filter(client_id=client_id)
        return qs.order_by('-state_date')


class CreditDailyStatesView(APIView):
    """Возвращает ежедневные состояния кредита, интерполированные из помесячных."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        credit_id = request.query_params.get('credit')
        if not credit_id:
            return Response({'error': 'credit parameter required'}, status=400)

        try:
            credit = Credit.objects.get(id=credit_id)
        except Credit.DoesNotExist:
            return Response({'error': 'credit not found'}, status=404)

        monthly_states = list(
            CreditState.objects.filter(credit=credit)
            .order_by('state_date')
            .values('state_date', 'principal_debt', 'overdue_principal',
                    'interest', 'overdue_interest', 'penalties', 'overdue_days')
        )

        if not monthly_states:
            return Response([])

        fields = ['principal_debt', 'overdue_principal', 'interest',
                  'overdue_interest', 'penalties']

        daily = []
        for i in range(len(monthly_states) - 1):
            s1 = monthly_states[i]
            s2 = monthly_states[i + 1]
            d1 = s1['state_date']
            d2 = s2['state_date']
            total_days = (d2 - d1).days
            if total_days <= 0:
                continue

            cur = d1
            while cur < d2:
                frac = (cur - d1).days / total_days
                row = {'state_date': cur.isoformat()}
                for f in fields:
                    v1 = float(s1[f] or 0)
                    v2 = float(s2[f] or 0)
                    row[f] = str(round(v1 + (v2 - v1) * frac, 2))
                dpd1 = s1['overdue_days'] or 0
                dpd2 = s2['overdue_days'] or 0
                row['overdue_days'] = round(dpd1 + (dpd2 - dpd1) * frac)
                daily.append(row)
                cur += timedelta(days=1)

        # Добавляем последнюю точку
        last = monthly_states[-1]
        row = {'state_date': last['state_date'].isoformat()}
        for f in fields:
            row[f] = str(float(last[f] or 0))
        row['overdue_days'] = last['overdue_days'] or 0
        daily.append(row)

        # Отдаём в обратном хронологическом порядке
        daily.reverse()
        return Response(daily)


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
        operator_id = self.request.query_params.get('operator_id') or self.request.query_params.get('operator')
        
        if operator_id:
            qs = qs.filter(operator_id=operator_id)
        
        # Only show assignments with overdue > 0
        qs = qs.filter(overdue_days__gt=0)
        
        # 230-ФЗ: исключаем банкротов и отказавшихся от контактов
        qs = qs.exclude(credit__client__is_bankrupt=True)
        qs = qs.exclude(credit__client__contact_refused=True)
        
        return qs.order_by('-priority', '-overdue_amount')
    
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


# ===== OVERDUE PREDICTION API =====

class OverduePredictionView(APIView):
    """
    API для прогнозирования просрочки с ранжированием по рискам.
    
    GET  /api/overdue-prediction/?credit_id=123
         → прогноз для одного кредита
    
    GET  /api/overdue-prediction/?client_id=456
         → прогноз по всем кредитам клиента
    
    POST /api/overdue-prediction/
         → пакетный прогноз для списка кредитов / всех просроченных
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        credit_id = request.query_params.get('credit_id')
        client_id = request.query_params.get('client_id')

        if credit_id:
            try:
                credit = Credit.objects.select_related('client').get(id=credit_id)
            except Credit.DoesNotExist:
                return Response({'error': 'Кредит не найден'}, status=status.HTTP_404_NOT_FOUND)
            features = self._build_features(credit)
            result = predict_risk(features)
            result['credit_id'] = credit.id
            result['client_id'] = credit.client.id
            result['client_name'] = credit.client.full_name
            result['features'] = features
            return Response(result)

        if client_id:
            try:
                client = Client.objects.get(id=client_id)
            except Client.DoesNotExist:
                return Response({'error': 'Клиент не найден'}, status=status.HTTP_404_NOT_FOUND)
            credits = Credit.objects.filter(client=client, status__in=['active', 'overdue', 'restructured'])
            records = []
            for c in credits:
                f = self._build_features(c)
                f['client_id'] = client.id
                f['credit_id'] = c.id
                records.append(f)
            if not records:
                return Response({'results': [], 'message': 'Нет активных кредитов'})
            results = predict_risk_batch(records)
            for r in results:
                r['client_name'] = client.full_name
            return Response({'results': results})

        return Response({'error': 'Укажите credit_id или client_id'}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request):
        """Пакетный прогноз с ранжированием."""
        credit_ids = request.data.get('credit_ids', [])
        top_n = int(request.data.get('top', 50))

        if credit_ids:
            credits = Credit.objects.filter(id__in=credit_ids).select_related('client')
        else:
            # По умолчанию: все активные/просроченные
            credits = Credit.objects.filter(
                status__in=['active', 'overdue', 'restructured']
            ).select_related('client')[:top_n * 2]

        records = []
        client_names = {}
        for c in credits:
            f = self._build_features(c)
            f['client_id'] = c.client.id
            f['credit_id'] = c.id
            records.append(f)
            client_names[c.client.id] = c.client.full_name

        if not records:
            return Response({'results': []})

        results = predict_risk_batch(records)
        for r in results:
            r['client_name'] = client_names.get(r.get('client_id'), '')

        return Response({
            'total': len(results),
            'results': results[:top_n],
        })

    @staticmethod
    def _build_features(credit) -> dict:
        """Собирает вектор признаков из Credit → Client, Payment, Intervention."""
        from datetime import date as dt_date
        from django.db.models import Avg, Max, Count, Q
        from datetime import timedelta

        client = credit.client
        today = dt_date.today()
        year_ago = today - timedelta(days=365)

        payments = credit.payments.all()
        interventions = credit.interventions.all()

        # Клиент
        age = (today - client.birth_date).days / 365.25 if client.birth_date else 35
        gender = 1 if client.gender == 'M' else 0
        marital_map = {'single': 0, 'married': 1, 'divorced': 2, 'widowed': 3}
        empl_map = {'employed': 1, 'self_employed': 2, 'unemployed': 0, 'retired': 3, 'student': 4}

        monthly_income = float(client.income) if client.income else 0
        other_count = Credit.objects.filter(client=client).exclude(id=credit.id).count()

        # Кредит
        credit_amount = float(credit.principal_amount) if credit.principal_amount else 0
        td = (credit.planned_close_date - credit.open_date).days if credit.planned_close_date and credit.open_date else 365
        credit_term = max(td // 30, 1)
        interest_rate = float(credit.interest_rate) if credit.interest_rate else 0
        monthly_pay = float(credit.monthly_payment) if credit.monthly_payment else 0
        lti = (credit_amount / (monthly_income * 12)) if monthly_income > 0 else 0
        credit_age = (today - credit.open_date).days if credit.open_date else 0
        status_map = {'active': 1, 'closed': 0, 'overdue': 2, 'default': 3, 'restructured': 4, 'legal': 5, 'sold': 6, 'written_off': 7}

        # Платежи
        total_p = payments.count()
        overdue_p = payments.filter(overdue_days__gt=0).count()
        max_od = payments.aggregate(m=Max('overdue_days'))['m'] or 0
        avg_pay = payments.aggregate(a=Avg('amount'))['a'] or 0
        p12 = payments.filter(payment_date__gte=year_ago)
        p12_cnt = p12.count()
        od12_cnt = p12.filter(overdue_days__gt=0).count()
        od12_share = od12_cnt / p12_cnt if p12_cnt > 0 else 0
        max_od_12 = p12.aggregate(m=Max('overdue_days'))['m'] or 0

        # Взаимодействие
        total_iv = interventions.count()
        compl_iv = interventions.filter(status='completed').count()
        promises = interventions.filter(status='promise').count()

        return {
            'age': age,
            'gender': gender,
            'marital_status': marital_map.get(client.marital_status, 0),
            'employment': empl_map.get(client.employment, 1),
            'dependents': client.children_count or 0,
            'monthly_income': monthly_income,
            'has_other_credits': 1 if other_count > 0 else 0,
            'other_credits_count': other_count,
            'credit_amount': credit_amount,
            'credit_term': credit_term,
            'interest_rate': interest_rate,
            'lti_ratio': lti,
            'credit_age': credit_age,
            'credit_status': status_map.get(credit.status, 1),
            'monthly_payment': monthly_pay,
            'total_payments': total_p,
            'overdue_payments': overdue_p,
            'max_overdue_days': max_od,
            'avg_payment': float(avg_pay),
            'payments_count_12m': p12_cnt,
            'overdue_count_12m': od12_cnt,
            'overdue_share_12m': od12_share,
            'max_overdue_12m': max_od_12,
            'total_interventions': total_iv,
            'completed_interventions': compl_iv,
            'promises_count': promises,
        }


class TrainOverdueModelView(APIView):
    """API для запуска обучения модели прогнозирования просрочки."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.core.management import call_command
        from io import StringIO
        import json

        buf = StringIO()
        try:
            call_command('train_overdue_model', stdout=buf, stderr=buf)
        except Exception as e:
            return Response({'error': str(e), 'log': buf.getvalue()}, status=500)

        # Load saved metrics from the model
        from .ml.overdue_predictor import get_model, MODEL_PATH
        model = get_model()
        if model.is_fitted:
            # Do a quick self-check to return metrics
            result = {'status': 'ok', 'log': buf.getvalue()}
            # Parse metrics from buffer output
            log_text = buf.getvalue()
            result['log'] = log_text
            # Try to provide structured metrics by re-running predict on test
            try:
                import pickle
                from pathlib import Path
                model_dir = Path(__file__).parent / 'ml' / 'saved_models'
                meta_path = model_dir / 'overdue_train_meta.json'
                if meta_path.exists():
                    with open(meta_path) as f:
                        result.update(json.load(f))
            except Exception:
                pass
            return Response(result)
        else:
            return Response({'error': 'Модель не была обучена', 'log': buf.getvalue()}, status=500)


class TrainApprovalModelView(APIView):
    """API для запуска обучения модели одобрения кредитных заявок."""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from django.core.management import call_command
        from io import StringIO
        import json

        buf = StringIO()
        try:
            call_command('train_approval_model', stdout=buf, stderr=buf)
        except Exception as e:
            return Response({'error': str(e), 'log': buf.getvalue()}, status=500)

        result = {'status': 'ok', 'log': buf.getvalue()}
        try:
            from pathlib import Path
            meta_path = Path(__file__).parent / 'ml' / 'saved_models' / 'approval_train_meta.json'
            if meta_path.exists():
                with open(meta_path) as f:
                    result.update(json.load(f))
        except Exception:
            pass
        return Response(result)


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

class DashboardFullView(APIView):
    """Полная статистика для дашборда руководителя"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        from django.db.models.functions import TruncDate, TruncHour, ExtractHour
        from collections import defaultdict
        
        today = timezone.now().date()
        period = request.query_params.get('period', 'day')
        
        # Определяем период
        if period == 'day':
            start_date = today
        elif period == 'week':
            start_date = today - timedelta(days=7)
        else:  # month
            start_date = today - timedelta(days=30)
        
        # Получаем интервенции за период
        interventions = Intervention.objects.filter(
            datetime__date__gte=start_date
        ).select_related('operator', 'client', 'credit')
        
        # === Статистика по операторам ===
        operators = Operator.objects.all()
        operator_stats = []
        
        for op in operators:
            op_interventions = interventions.filter(operator=op)
            total_calls = op_interventions.filter(intervention_type='phone').count()
            contacts = op_interventions.filter(
                intervention_type='phone',
                status__in=['completed', 'promise', 'refuse', 'callback']
            ).count()
            ptp_count = op_interventions.filter(status='promise').count()
            ptp_amount = op_interventions.filter(status='promise').aggregate(
                total=Sum('promise_amount')
            )['total'] or 0
            
            # Расчёт времени на звонках
            total_duration = op_interventions.filter(intervention_type='phone').aggregate(
                total=Sum('duration')
            )['total'] or 0
            
            avg_duration = 0
            if total_calls > 0:
                avg_duration = total_duration // total_calls
            
            contact_rate = round((contacts / total_calls * 100), 1) if total_calls > 0 else 0
            
            # Время работы (эмуляция)
            total_time_min = total_duration // 60
            break_time_min = int(total_time_min * 0.12)  # ~12% на перерывы
            
            operator_stats.append({
                'id': op.id,
                'name': op.full_name,
                'calls': total_calls,
                'contacts': contacts,
                'contactRate': contact_rate,
                'avgDuration': avg_duration,
                'totalTime': total_time_min,
                'breakTime': break_time_min,
                'ptpCount': ptp_count,
                'ptpAmount': float(ptp_amount),
            })
        
        # === Динамика звонков по дням ===
        daily_calls = interventions.filter(intervention_type='phone').annotate(
            date=TruncDate('datetime')
        ).values('date').annotate(
            calls=Count('id'),
            contacts=Count('id', filter=Q(status__in=['completed', 'promise', 'refuse', 'callback'])),
            ptp=Count('id', filter=Q(status='promise'))
        ).order_by('date')
        
        daily_data = []
        for day in daily_calls:
            daily_data.append({
                'date': day['date'].strftime('%d.%m') if day['date'] else '',
                'calls': day['calls'],
                'contacts': day['contacts'],
                'ptp': day['ptp']
            })
        
        # === Распределение по часам ===
        hourly_calls = interventions.filter(intervention_type='phone').annotate(
            hour=ExtractHour('datetime')
        ).values('hour').annotate(
            calls=Count('id'),
            total_duration=Sum('duration'),
            contacts=Count('id', filter=Q(status__in=['completed', 'promise', 'refuse', 'callback']))
        ).order_by('hour')
        
        hourly_data = []
        for h in hourly_calls:
            avg_dur = h['total_duration'] // h['calls'] if h['calls'] > 0 else 0
            contact_rate = round(h['contacts'] / h['calls'] * 100, 1) if h['calls'] > 0 else 0
            hourly_data.append({
                'hour': f"{h['hour']:02d}:00",
                'calls': h['calls'],
                'avgDuration': avg_dur,
                'contactRate': contact_rate
            })
        
        # === Распределение результатов ===
        result_distribution = interventions.filter(intervention_type='phone').values('status').annotate(
            count=Count('id')
        )
        
        status_mapping = {
            'no_answer': ('Не дозвон', '#94a3b8'),
            'promise': ('Обещание', '#22c55e'),
            'refuse': ('Отказ', '#ef4444'),
            'callback': ('Перезвонить', '#f59e0b'),
            'completed': ('Контакт', '#3b82f6'),
        }
        
        call_results = []
        total_results = sum(r['count'] for r in result_distribution)
        for r in result_distribution:
            status = r['status']
            if status in status_mapping:
                name, color = status_mapping[status]
                value = round(r['count'] / total_results * 100) if total_results > 0 else 0
                call_results.append({
                    'name': name,
                    'value': value,
                    'color': color
                })
        
        # === Распределение времени ===
        time_distribution = [
            {'name': 'На звонке', 'value': 65, 'color': '#22c55e'},
            {'name': 'Постобработка', 'value': 15, 'color': '#3b82f6'},
            {'name': 'Ожидание', 'value': 12, 'color': '#f59e0b'},
            {'name': 'Перерыв', 'value': 8, 'color': '#94a3b8'},
        ]
        
        # === Агрегированная статистика ===
        totals = {
            'calls': sum(op['calls'] for op in operator_stats),
            'contacts': sum(op['contacts'] for op in operator_stats),
            'totalTime': sum(op['totalTime'] for op in operator_stats),
            'breakTime': sum(op['breakTime'] for op in operator_stats),
            'ptpCount': sum(op['ptpCount'] for op in operator_stats),
            'ptpAmount': sum(op['ptpAmount'] for op in operator_stats),
        }
        totals['contactRate'] = round(totals['contacts'] / totals['calls'] * 100, 1) if totals['calls'] > 0 else 0
        totals['avgDuration'] = sum(op['avgDuration'] for op in operator_stats) // len(operator_stats) if operator_stats else 0
        
        return Response({
            'period': period,
            'startDate': start_date.isoformat(),
            'endDate': today.isoformat(),
            'totals': totals,
            'operatorStats': operator_stats,
            'dailyCalls': daily_data,
            'hourlyCalls': hourly_data,
            'callResults': call_results,
            'timeDistribution': time_distribution,
        })

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
    """Подробная статистика оператора для страницы личной статистики"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request, operator_id=None):
        from django.db.models.functions import TruncDate
        from collections import defaultdict
        
        if operator_id is None:
            operator_id = request.query_params.get('operator_id')
            if not operator_id:
                return Response({'error': 'operator_id обязателен'}, status=400)
        
        try:
            operator = Operator.objects.get(id=operator_id)
        except Operator.DoesNotExist:
            return Response({'error': 'Оператор не найден'}, status=404)
        
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Все интервенции оператора
        all_interventions = Intervention.objects.filter(operator=operator)
        today_ints = all_interventions.filter(datetime__date=today)
        week_ints = all_interventions.filter(datetime__date__gte=week_ago)
        month_ints = all_interventions.filter(datetime__date__gte=month_ago)
        
        def calc_stats(qs):
            total = qs.count()
            calls = qs.filter(intervention_type='phone').count()
            contacts = qs.filter(
                intervention_type='phone',
                status__in=['completed', 'promise', 'refuse', 'callback']
            ).count()
            no_answer = qs.filter(status='no_answer').count()
            promises = qs.filter(status='promise').count()
            promise_amount = float(qs.filter(status='promise').aggregate(s=Sum('promise_amount'))['s'] or 0)
            refusals = qs.filter(status='refuse').count()
            completed = qs.filter(status='completed').count()
            callbacks = qs.filter(status='callback').count()
            total_duration = qs.filter(intervention_type='phone').aggregate(s=Sum('duration'))['s'] or 0
            avg_duration = total_duration // calls if calls > 0 else 0
            contact_rate = round(contacts / calls * 100, 1) if calls > 0 else 0
            promise_rate = round(promises / contacts * 100, 1) if contacts > 0 else 0
            return {
                'total': total,
                'calls': calls,
                'contacts': contacts,
                'noAnswer': no_answer,
                'promises': promises,
                'promiseAmount': promise_amount,
                'refusals': refusals,
                'completed': completed,
                'callbacks': callbacks,
                'totalDuration': total_duration,
                'avgDuration': avg_duration,
                'contactRate': contact_rate,
                'promiseRate': promise_rate,
            }
        
        # === Ежедневная динамика за 30 дней ===
        daily_data = []
        daily_qs = month_ints.filter(intervention_type='phone').annotate(
            date=TruncDate('datetime')
        ).values('date').annotate(
            calls=Count('id'),
            contacts=Count('id', filter=Q(status__in=['completed', 'promise', 'refuse', 'callback'])),
            promises=Count('id', filter=Q(status='promise')),
            promise_amount=Sum('promise_amount', filter=Q(status='promise')),
            total_duration=Sum('duration'),
        ).order_by('date')
        
        for day in daily_qs:
            daily_data.append({
                'date': day['date'].strftime('%d.%m') if day['date'] else '',
                'dateFull': day['date'].isoformat() if day['date'] else '',
                'calls': day['calls'],
                'contacts': day['contacts'],
                'promises': day['promises'],
                'promiseAmount': float(day['promise_amount'] or 0),
                'avgDuration': (day['total_duration'] or 0) // day['calls'] if day['calls'] > 0 else 0,
            })
        
        # === Распределение по статусам (за месяц) ===
        status_dist = list(month_ints.values('status').annotate(count=Count('id')).order_by('-count'))
        
        # === Распределение по часам (за месяц) ===
        from django.db.models.functions import ExtractHour
        hourly = month_ints.filter(intervention_type='phone').annotate(
            hour=ExtractHour('datetime')
        ).values('hour').annotate(
            calls=Count('id')
        ).order_by('hour')
        hourly_data = [{'hour': f"{h['hour']:02d}:00", 'calls': h['calls']} for h in hourly]
        
        # === Активные назначения ===
        active_assignments = Assignment.objects.filter(
            operator=operator,
            overdue_days__gt=0
        ).count()
        
        # === Топ обещаний (за 30 дней) ===
        top_promises = list(
            month_ints.filter(status='promise', promise_amount__gt=0)
            .select_related('client')
            .order_by('-promise_amount')[:10]
            .values('id', 'client__full_name', 'promise_amount', 'promise_date', 'datetime')
        )
        for p in top_promises:
            p['promise_amount'] = float(p['promise_amount'])
            p['datetime'] = p['datetime'].isoformat() if p['datetime'] else None
            p['promise_date'] = p['promise_date'].isoformat() if p['promise_date'] else None
        
        return Response({
            'operator': {
                'id': operator.id,
                'name': operator.full_name,
                'role': operator.role,
                'specialization': operator.specialization,
                'hireDate': operator.hire_date.isoformat() if operator.hire_date else None,
                'status': operator.status,
            },
            'today': calc_stats(today_ints),
            'week': calc_stats(week_ints),
            'month': calc_stats(month_ints),
            'allTime': {
                'totalInterventions': all_interventions.count(),
                'totalCollected': float(operator.total_collected),
                'successRate': operator.success_rate,
            },
            'daily': daily_data,
            'statusDistribution': status_dist,
            'hourly': hourly_data,
            'activeAssignments': active_assignments,
            'topPromises': top_promises,
        })


# ===== 230-ФЗ COMPLIANCE API =====

class ComplianceCheckView(APIView):
    """
    Проверка возможности контакта с клиентом по 230-ФЗ.

    GET /api/compliance/check/?client_id=123&type=phone
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        client_id = request.query_params.get('client_id')
        contact_type = request.query_params.get('type', 'phone')
        if not client_id:
            return Response({'error': 'client_id обязателен'}, status=400)
        result = can_contact(int(client_id), contact_type)
        return Response(result)


class BankruptcyCheckView(APIView):
    """
    Проверка и регистрация банкротства клиента.

    GET  /api/compliance/bankruptcy/?client_id=123
    POST /api/compliance/bankruptcy/  {client_id, is_bankrupt, case_number?}
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        client_id = request.query_params.get('client_id')
        if not client_id:
            return Response({'error': 'client_id обязателен'}, status=400)
        result = check_bankruptcy(int(client_id))
        return Response(result)

    def post(self, request):
        client_id = request.data.get('client_id')
        is_bankrupt = request.data.get('is_bankrupt', False)
        case_number = request.data.get('case_number', '')
        if not client_id:
            return Response({'error': 'client_id обязателен'}, status=400)
        try:
            client = Client.objects.get(id=client_id)
        except Client.DoesNotExist:
            return Response({'error': 'Клиент не найден'}, status=404)

        client.is_bankrupt = is_bankrupt
        if is_bankrupt:
            client.bankruptcy_date = timezone.now().date()
        client.save()

        BankruptcyCheck.objects.create(
            client=client,
            is_bankrupt=is_bankrupt,
            case_number=case_number,
            source='manual',
        )

        AuditLog.objects.create(
            action='bankruptcy_check',
            client_id=client_id,
            severity='critical' if is_bankrupt else 'info',
            details={'is_bankrupt': is_bankrupt, 'case_number': case_number},
        )

        return Response({'status': 'ok', 'is_bankrupt': is_bankrupt})


class ComplianceSummaryView(APIView):
    """
    Сводка по соблюдению 230-ФЗ для дашборда руководителя.

    GET /api/compliance/summary/
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(get_compliance_summary())


# ===== ML MODEL METRICS & VERSIONING API =====

class MLModelMetricsView(APIView):
    """
    Метрики ML-моделей: ROC-AUC, feature importances, ROC-кривая, сравнение версий.

    GET /api/ml/models/                  — все версии
    GET /api/ml/models/?active=true      — только активные
    GET /api/ml/models/<id>/             — конкретная версия
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, model_id=None):
        if model_id:
            try:
                mv = MLModelVersion.objects.get(id=model_id)
            except MLModelVersion.DoesNotExist:
                return Response({'error': 'Модель не найдена'}, status=404)
            return Response(MLModelVersionSerializer(mv).data)

        qs = MLModelVersion.objects.all().order_by('-created_at')
        active_only = request.query_params.get('active')
        if active_only == 'true':
            qs = qs.filter(is_active=True)
        return Response(MLModelVersionSerializer(qs, many=True).data)


# ===== A/B TESTING API =====

class ABTestResultsView(APIView):
    """
    Результаты A/B-тестирования алгоритмов распределения.

    GET /api/ab-test/results/?period=month
    Сравнивает группы A (случайное) и B (умное) по ключевым метрикам.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        period = request.query_params.get('period', 'month')
        today = timezone.now().date()
        if period == 'day':
            start = today
        elif period == 'week':
            start = today - timedelta(days=7)
        else:
            start = today - timedelta(days=30)

        groups = {}
        for group_label in ['A', 'B']:
            assigns = Assignment.objects.filter(
                ab_group=group_label,
                assigned_at__date__gte=start,
            )
            total = assigns.count()
            if total == 0:
                groups[group_label] = {
                    'total_assignments': 0,
                    'message': 'Нет данных',
                }
                continue

            # Кредиты, связанные с назначениями
            credit_ids = list(assigns.values_list('credit_id', flat=True))

            # Интервенции по этим кредитам за период
            interventions = Intervention.objects.filter(
                credit_id__in=credit_ids,
                datetime__date__gte=start,
            )
            total_calls = interventions.filter(intervention_type='phone').count()
            contacts = interventions.filter(
                intervention_type='phone',
                status__in=['completed', 'promise', 'refuse', 'callback'],
            ).count()
            promises = interventions.filter(status='promise').count()
            promise_amt = float(interventions.filter(status='promise').aggregate(
                s=Sum('promise_amount')
            )['s'] or 0)

            contact_rate = round(contacts / total_calls * 100, 1) if total_calls > 0 else 0
            promise_rate = round(promises / contacts * 100, 1) if contacts > 0 else 0

            # Средний match_score
            avg_match = assigns.aggregate(avg=Avg('match_score'))['avg'] or 0

            groups[group_label] = {
                'total_assignments': total,
                'total_calls': total_calls,
                'contacts': contacts,
                'contact_rate': contact_rate,
                'promises': promises,
                'promise_rate': promise_rate,
                'promise_amount': promise_amt,
                'avg_match_score': round(float(avg_match), 2),
            }

        # Статистический вывод
        a = groups.get('A', {})
        b = groups.get('B', {})
        lift = None
        if a.get('contact_rate', 0) > 0 and b.get('contact_rate', 0) > 0:
            lift = round((b['contact_rate'] - a['contact_rate']) / a['contact_rate'] * 100, 1)

        return Response({
            'period': period,
            'start_date': start.isoformat(),
            'groups': groups,
            'lift_contact_rate_pct': lift,
            'conclusion': (
                f'Группа B (smart) показывает {"+" if lift and lift > 0 else ""}'
                f'{lift}% к contact rate по сравнению с группой A (random)'
            ) if lift else 'Недостаточно данных',
        })


# ===== VIOLATION LOG API =====

class ViolationLogView(APIView):
    """Журнал нарушений 230-ФЗ"""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = ViolationLog.objects.select_related('client', 'operator').all()
        client_id = request.query_params.get('client_id')
        operator_id = request.query_params.get('operator_id')
        rule_type = request.query_params.get('rule_type')
        severity = request.query_params.get('severity')
        if client_id:
            qs = qs.filter(client_id=client_id)
        if operator_id:
            qs = qs.filter(operator_id=operator_id)
        if rule_type:
            qs = qs.filter(rule_type=rule_type)
        if severity:
            qs = qs.filter(severity=severity)
        qs = qs[:200]
        return Response(ViolationLogSerializer(qs, many=True).data)


# ===== SMART DISTRIBUTION API =====

class SmartDistributionView(APIView):
    """
    Запуск интеллектуального распределения клиентов по операторам.

    POST /api/distribution/run/  {strategy: 'smart'|'random'|'round_robin', ab_test: true}
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from .services.distribution import DistributionService

        strategy = request.data.get('strategy', 'smart')
        ab_test = request.data.get('ab_test', False)

        svc = DistributionService()

        # Кредиты без оператора, исключая банкротов
        unassigned = Credit.objects.filter(
            status__in=['overdue', 'default'],
        ).exclude(
            client__is_bankrupt=True,
        ).exclude(
            client__contact_refused=True,
        ).exclude(
            id__in=Assignment.objects.filter(overdue_days__gt=0).values_list('credit_id', flat=True),
        )

        results = {'assigned': 0, 'skipped': 0, 'errors': []}

        for credit in unassigned[:200]:
            try:
                rec = svc.get_recommended_operator(credit)
                if not rec:
                    results['skipped'] += 1
                    continue

                ab_group = 'B' if strategy == 'smart' else 'A'
                if ab_test:
                    import random
                    ab_group = random.choice(['A', 'B'])

                Assignment.objects.create(
                    credit=credit,
                    operator=rec['operator'],
                    assigned_at=timezone.now(),
                    priority=rec.get('priority', 'medium'),
                    overdue_amount=credit.states.order_by('-state_date').first().overdue_principal if credit.states.exists() else 0,
                    overdue_days=credit.states.order_by('-state_date').first().overdue_days if credit.states.exists() else 0,
                    ab_group=ab_group,
                    assignment_method=strategy,
                    match_score=rec.get('score', 0),
                )
                results['assigned'] += 1
            except Exception as e:
                results['errors'].append(str(e))

        AuditLog.objects.create(
            action='distribution_run',
            severity='info',
            details={
                'strategy': strategy,
                'ab_test': ab_test,
                'assigned': results['assigned'],
                'skipped': results['skipped'],
            },
        )

        return Response(results)


# ===== AUDIT LOG API =====

class AuditLogView(APIView):
    """
    Журнал аудита действий в системе.

    GET /api/audit/?action=contact_blocked&limit=100
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = AuditLog.objects.all().order_by('-timestamp')

        action_filter = request.query_params.get('action')
        if action_filter:
            qs = qs.filter(action=action_filter)

        severity_filter = request.query_params.get('severity')
        if severity_filter:
            qs = qs.filter(severity=severity_filter)

        operator_id = request.query_params.get('operator_id')
        if operator_id:
            qs = qs.filter(operator_id=operator_id)

        client_id = request.query_params.get('client_id')
        if client_id:
            qs = qs.filter(client_id=client_id)

        limit = int(request.query_params.get('limit', 100))
        qs = qs[:limit]

        return Response(AuditLogSerializer(qs, many=True).data)


# ===== SCORING RESULTS (enhanced) =====

class ScoringDashboardView(APIView):
    """
    Дашборд скоринга: распределение баллов, грейдов, economic model.

    GET /api/scoring/dashboard/
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Последние скоринги (один на клиента)
        latest = ScoringResult.objects.filter(
            score_value__isnull=False,
        ).order_by('client', '-scoring_date').distinct('client') if hasattr(ScoringResult.objects, 'distinct') else ScoringResult.objects.filter(score_value__isnull=False).order_by('-scoring_date')

        # SQLite не поддерживает distinct('client'), поэтому группируем вручную
        all_scores = ScoringResult.objects.filter(score_value__isnull=False).order_by('-scoring_date')
        seen_clients = set()
        unique_scores = []
        for sc in all_scores:
            if sc.client_id not in seen_clients:
                seen_clients.add(sc.client_id)
                unique_scores.append(sc)

        grade_dist = {}
        score_histogram = {}
        total_expected_profit = 0
        total_expected_recovery = 0

        for sc in unique_scores:
            g = sc.grade or 'N/A'
            grade_dist[g] = grade_dist.get(g, 0) + 1

            bucket = ((sc.score_value or 0) // 50) * 50
            key = f'{int(bucket)}-{int(bucket+49)}'
            score_histogram[key] = score_histogram.get(key, 0) + 1

            total_expected_profit += float(sc.expected_profit or 0)
            total_expected_recovery += float(sc.expected_recovery or 0)

        # Активная модель
        active_model = MLModelVersion.objects.filter(is_active=True).first()
        model_info = MLModelVersionSerializer(active_model).data if active_model else None

        return Response({
            'total_scored': len(unique_scores),
            'grade_distribution': grade_dist,
            'score_histogram': score_histogram,
            'total_expected_profit': total_expected_profit,
            'total_expected_recovery': total_expected_recovery,
            'active_model': model_info,
        })
