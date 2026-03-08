"""
Distribution service for assigning clients to operators.
Can be used from views, Celery tasks, or management commands.

Интегрирован с ML-моделью прогнозирования просрочки:
  - При распределении учитывается risk_score из OverdueRiskModel
  - Если свежий ScoringResult отсутствует (>7 дней), прогноз делается на лету
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Tuple
from django.db.models import Count, Q, Avg, Max

from collection_app.models import (
    Client, Operator, Credit, Assignment, ScoringResult, Intervention
)


def _build_credit_features(credit: Credit) -> dict:
    """Build ML feature vector for predict_risk. Shared with score_all_credits command."""
    client = credit.client
    today = date.today()
    year_ago = today - timedelta(days=365)

    payments = credit.payments.all()
    interventions = credit.interventions.all()

    age = (today - client.birth_date).days / 365.25 if client.birth_date else 35
    gender = 1 if client.gender == 'M' else 0
    marital_map = {'single': 0, 'married': 1, 'divorced': 2, 'widowed': 3}
    empl_map = {'employed': 1, 'self_employed': 2, 'unemployed': 0, 'retired': 3, 'student': 4}

    monthly_income = float(client.income) if client.income else 0
    other_count = Credit.objects.filter(client=client).exclude(id=credit.id).count()

    credit_amount = float(credit.principal_amount) if credit.principal_amount else 0
    td = (credit.planned_close_date - credit.open_date).days if credit.planned_close_date and credit.open_date else 365
    credit_term = max(td // 30, 1)
    interest_rate = float(credit.interest_rate) if credit.interest_rate else 0
    monthly_pay = float(credit.monthly_payment) if credit.monthly_payment else 0
    lti = (credit_amount / (monthly_income * 12)) if monthly_income > 0 else 0
    credit_age = (today - credit.open_date).days if credit.open_date else 0
    status_map = {'active': 1, 'closed': 0, 'overdue': 2, 'default': 3, 'restructured': 4, 'legal': 5, 'sold': 6, 'written_off': 7}

    total_p = payments.count()
    overdue_p = payments.filter(overdue_days__gt=0).count()
    max_od = payments.aggregate(m=Max('overdue_days'))['m'] or 0
    avg_pay = payments.aggregate(a=Avg('amount'))['a'] or 0
    p12 = payments.filter(payment_date__gte=year_ago)
    p12_cnt = p12.count()
    od12_cnt = p12.filter(overdue_days__gt=0).count()
    od12_share = od12_cnt / p12_cnt if p12_cnt > 0 else 0
    max_od_12 = p12.aggregate(m=Max('overdue_days'))['m'] or 0

    total_iv = interventions.count()
    compl_iv = interventions.filter(status='completed').count()
    promises = interventions.filter(status='promise').count()

    return {
        'age': age, 'gender': gender,
        'marital_status': marital_map.get(client.marital_status, 0),
        'employment': empl_map.get(client.employment, 1),
        'dependents': client.children_count or 0,
        'monthly_income': monthly_income,
        'has_other_credits': 1 if other_count > 0 else 0,
        'other_credits_count': other_count,
        'credit_amount': credit_amount, 'credit_term': credit_term,
        'interest_rate': interest_rate, 'lti_ratio': lti,
        'credit_age': credit_age,
        'credit_status': status_map.get(credit.status, 1),
        'monthly_payment': monthly_pay,
        'total_payments': total_p, 'overdue_payments': overdue_p,
        'max_overdue_days': max_od, 'avg_payment': float(avg_pay),
        'payments_count_12m': p12_cnt, 'overdue_count_12m': od12_cnt,
        'overdue_share_12m': od12_share, 'max_overdue_12m': max_od_12,
        'total_interventions': total_iv, 'completed_interventions': compl_iv,
        'promises_count': promises,
    }


class DistributionService:
    """
    Service for intelligent client-to-operator distribution.
    
    Matching logic:
    - High-risk/high-value clients → Experienced operators
    - New/simple cases → Junior operators (for training)
    - Balances workload across team
    """

    def __init__(self, max_load_per_operator: int = 60):
        self.max_load = max_load_per_operator

    def calculate_operator_experience(self, operator: Operator) -> Dict:
        """
        Calculate operator experience score (0-100).
        
        Factors:
        - Years of service (0-40 pts)
        - Role/seniority (0-30 pts)
        - Historical success rate (0-30 pts)
        """
        today = date.today()
        
        # Role weights
        role_weights = {
            'operator': 10,
            'senior_operator': 20,
            'supervisor': 25,
            'manager': 30,
        }

        # Experience from tenure
        if operator.hire_date:
            years = (today - operator.hire_date).days / 365
            tenure_score = min(40, years * 8)
        else:
            tenure_score = 20

        # Role score
        role_score = role_weights.get(operator.role, 10)

        # Success rate
        interventions = Intervention.objects.filter(operator=operator)
        total = interventions.count()
        successful = interventions.filter(status__in=['promise', 'completed']).count()
        
        if total > 0:
            success_score = (successful / total) * 30
        else:
            success_score = 15  # Neutral for new operators

        return {
            'total_score': tenure_score + role_score + success_score,
            'tenure_score': tenure_score,
            'role_score': role_score,
            'success_score': success_score,
            'success_rate': successful / total if total > 0 else None,
            'total_interventions': total,
        }

    def calculate_client_priority(self, credit: Credit) -> Dict:
        """
        Calculate client/credit priority (0-100).
        Higher = more problematic = needs experienced operator.
        
        Factors:
        - Overdue amount (0-25 pts)
        - Days past due (0-25 pts)
        - ML risk score (0-30 pts)  ← новый фактор
        - Failed contact attempts (0-10 pts)
        - Risk segment from scoring (0-10 pts)
        """
        # Get overdue info from latest state
        latest_state = credit.states.order_by('-state_date').first()
        overdue_amount = float(latest_state.overdue_principal) if latest_state else 0
        
        # Estimate days overdue
        if credit.status in ['overdue', 'default']:
            monthly = max(float(credit.monthly_payment), 1)
            days_overdue = min(180, int(overdue_amount / monthly * 30))
        else:
            days_overdue = 0

        # Amount score (normalized to 500k max)
        amount_score = min(25, (overdue_amount / 500000) * 25)

        # Days score
        days_score = min(25, (days_overdue / 180) * 25)

        # --- ML risk score (0-30 pts) ---
        ml_risk_score = None
        latest_scoring = credit.scorings.order_by('-calculation_date').first()
        cutoff_date = date.today() - timedelta(days=7)

        if latest_scoring and latest_scoring.calculation_date >= cutoff_date:
            # Use fresh scoring result — convert score_value (300-850) back to risk_score (0-1)
            ml_risk_score = max(0.0, min(1.0, (850 - (latest_scoring.score_value or 575)) / 550))
        else:
            # No fresh scoring → compute on-the-fly
            try:
                from collection_app.ml.overdue_predictor import predict_risk
                features = _build_credit_features(credit)
                pred = predict_risk(features)
                ml_risk_score = pred.get('risk_score', 0.5)
            except Exception:
                ml_risk_score = 0.5  # fallback

        ml_risk_pts = ml_risk_score * 30  # 0-30 pts

        # Failed attempts (0-10 pts)
        failed = Intervention.objects.filter(
            credit=credit,
            status__in=['no_answer', 'refuse']
        ).count()
        failed_score = min(10, failed * 2)

        # Segment bonus (0-10 pts) from static segment
        segment_weights = {'low': 2, 'medium': 5, 'high': 8, 'critical': 10}
        segment_label = latest_scoring.risk_segment if latest_scoring else 'medium'
        segment_score = segment_weights.get(segment_label, 5)

        total_priority = amount_score + days_score + ml_risk_pts + failed_score + segment_score

        return {
            'total_priority': total_priority,
            'overdue_amount': overdue_amount,
            'days_overdue': days_overdue,
            'ml_risk_score': ml_risk_score,
            'risk_segment': segment_label,
            'failed_attempts': failed,
        }

    def get_recommended_operator(self, credit: Credit, available_operators: List[Operator]) -> Tuple[Operator, Dict]:
        """
        Get the best operator for a specific credit based on matching logic.
        Returns (operator, match_info).
        """
        if not available_operators:
            return None, {}

        client_priority = self.calculate_client_priority(credit)
        priority_score = client_priority['total_priority']

        # Calculate scores for all operators
        operator_matches = []
        for op in available_operators:
            if op.current_load >= self.max_load:
                continue
                
            exp = self.calculate_operator_experience(op)
            exp_score = exp['total_score']
            
            # Match score: high priority clients should go to experienced operators
            # Score difference should be minimal for good match
            if priority_score > 70:  # High priority client
                # Prefer experienced operators
                match_quality = exp_score
            elif priority_score > 40:  # Medium priority
                # Balance - slight preference for experienced
                match_quality = exp_score * 0.7 + (100 - op.current_load) * 0.3
            else:  # Low priority
                # Good for training junior operators
                match_quality = (100 - exp_score) * 0.5 + (100 - op.current_load) * 0.5

            operator_matches.append({
                'operator': op,
                'match_quality': match_quality,
                'experience': exp,
            })

        if not operator_matches:
            return None, {}

        # Sort by match quality (descending)
        operator_matches.sort(key=lambda x: x['match_quality'], reverse=True)
        best = operator_matches[0]

        return best['operator'], {
            'client_priority': client_priority,
            'operator_experience': best['experience'],
            'match_quality': best['match_quality'],
        }

    def distribute_batch(self, credits: List[Credit], operators: List[Operator], 
                         assignment_date: date = None) -> List[Assignment]:
        """
        Distribute a batch of credits to operators.
        Returns list of created Assignment objects.
        """
        if assignment_date is None:
            assignment_date = date.today()

        # Calculate all scores upfront
        credit_priorities = [
            (credit, self.calculate_client_priority(credit))
            for credit in credits
        ]
        
        # Sort by priority (highest first)
        credit_priorities.sort(key=lambda x: x[1]['total_priority'], reverse=True)

        operator_exp = {
            op.id: self.calculate_operator_experience(op)
            for op in operators
        }
        
        # Track loads
        loads = {op.id: op.current_load for op in operators}
        
        assignments = []

        for credit, priority_info in credit_priorities:
            # Find available operators
            available = [op for op in operators if loads[op.id] < self.max_load]
            if not available:
                break

            # Get best match
            best_op, _ = self.get_recommended_operator(credit, available)
            if not best_op:
                continue

            # Create assignment
            assignment = Assignment.objects.create(
                operator=best_op,
                debtor_name=credit.client.full_name,
                credit=credit,
                overdue_amount=Decimal(priority_info['overdue_amount']).quantize(Decimal('0.01')),
                overdue_days=priority_info['days_overdue'],
                priority=self._priority_to_level(priority_info['total_priority']),
                assignment_date=assignment_date
            )
            assignments.append(assignment)
            loads[best_op.id] += 1

        # Update operator loads in DB
        for op in operators:
            if loads[op.id] != op.current_load:
                op.current_load = loads[op.id]
                op.save(update_fields=['current_load'])

        return assignments

    def _priority_to_level(self, priority_score: float) -> int:
        """Convert priority score to 1-5 level"""
        if priority_score >= 80:
            return 5
        elif priority_score >= 60:
            return 4
        elif priority_score >= 40:
            return 3
        elif priority_score >= 20:
            return 2
        return 1

    def get_distribution_stats(self, assignment_date: date = None) -> Dict:
        """Get statistics for distribution on a given date"""
        if assignment_date is None:
            assignment_date = date.today()

        assignments = Assignment.objects.filter(assignment_date=assignment_date)
        
        total = assignments.count()
        by_priority = assignments.values('priority').annotate(count=Count('id'))
        by_operator = assignments.values('operator__full_name').annotate(
            count=Count('id'),
            total_overdue=models.Sum('overdue_amount')
        )

        return {
            'date': assignment_date,
            'total_assignments': total,
            'by_priority': list(by_priority),
            'by_operator': list(by_operator),
        }


# Convenience function for quick distribution
def auto_distribute(max_load: int = 60, clear_existing: bool = False) -> List[Assignment]:
    """
    Automatically distribute all overdue credits to active operators.
    """
    from collection_app.models import Credit, Operator, Assignment
    
    today = date.today()
    
    if clear_existing:
        Assignment.objects.filter(assignment_date=today).delete()

    operators = list(Operator.objects.filter(status__in=['active', 'on_call', 'break']))
    credits = list(Credit.objects.filter(
        status__in=['overdue', 'default']
    ).select_related('client').prefetch_related('states', 'scorings'))

    service = DistributionService(max_load_per_operator=max_load)
    return service.distribute_batch(credits, operators, today)
