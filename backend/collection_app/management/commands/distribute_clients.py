"""
Management command to distribute clients to operators based on:
- Operator experience (hire date, role, current load)
- Client problem level (overdue amount, days overdue, risk segment)

Algorithm:
1. Calculate operator experience score (0-100)
2. Calculate client priority score (0-100)  
3. Match high-priority clients to experienced operators
4. Balance workload across operators
"""
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum, Count, Avg, Max
from collection_app.models import (
    Client, Operator, Credit, CreditState, Assignment, ScoringResult, Intervention
)


class Command(BaseCommand):
    help = 'Distribute clients to operators based on experience and client problem level'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=str, help='Assignment date (YYYY-MM-DD), default is today')
        parser.add_argument('--max-load', type=int, default=60, help='Maximum assignments per operator')
        parser.add_argument('--clear', action='store_true', help='Clear existing assignments for the date')

    def handle(self, *args, **options):
        assignment_date = date.today()
        if options['date']:
            assignment_date = date.fromisoformat(options['date'])
        
        max_load = options['max_load']
        
        if options['clear']:
            deleted, _ = Assignment.objects.filter(assignment_date=assignment_date).delete()
            self.stdout.write(f'Cleared {deleted} existing assignments for {assignment_date}')

        # Get active operators
        operators = list(Operator.objects.filter(status__in=['active', 'on_call', 'break']))
        if not operators:
            self.stdout.write(self.style.ERROR('No active operators found!'))
            return

        # Get overdue credits that need attention
        overdue_credits = self._get_overdue_credits()
        if not overdue_credits:
            self.stdout.write(self.style.WARNING('No overdue credits found!'))
            return

        self.stdout.write(f'Found {len(operators)} operators and {len(overdue_credits)} overdue credits')

        # Calculate scores
        operator_scores = self._calculate_operator_scores(operators)
        client_scores = self._calculate_client_scores(overdue_credits)

        # Sort operators by experience (descending) and clients by priority (descending)
        sorted_operators = sorted(operator_scores.items(), key=lambda x: x[1]['score'], reverse=True)
        sorted_clients = sorted(client_scores.items(), key=lambda x: x[1]['priority'], reverse=True)

        # Distribute clients to operators
        assignments = self._distribute_clients(sorted_operators, sorted_clients, max_load, assignment_date)

        self.stdout.write(self.style.SUCCESS(f'Created {len(assignments)} assignments for {assignment_date}'))
        
        # Print summary
        self._print_summary(assignments, operator_scores)

    def _get_overdue_credits(self):
        """Get credits that are overdue or at risk"""
        return Credit.objects.filter(
            status__in=['overdue', 'default', 'active']
        ).select_related('client').prefetch_related('states', 'scorings')

    def _calculate_operator_scores(self, operators):
        """
        Calculate experience score for each operator (0-100)
        Factors:
        - Years of experience (0-40 points)
        - Role seniority (0-30 points)
        - Success rate from past interventions (0-30 points)
        """
        scores = {}
        today = date.today()
        
        role_weights = {
            'operator': 10,
            'senior_operator': 20,
            'supervisor': 25,
            'manager': 30,
        }

        for op in operators:
            # Experience score (up to 40 points for 5+ years)
            if op.hire_date:
                years = (today - op.hire_date).days / 365
                experience_score = min(40, years * 8)  # 8 points per year, max 40
            else:
                experience_score = 20  # Default if no hire date

            # Role score
            role_score = role_weights.get(op.role, 10)

            # Success rate from interventions (promises obtained)
            interventions = Intervention.objects.filter(operator=op)
            total_interventions = interventions.count()
            successful = interventions.filter(status__in=['promise', 'completed']).count()
            
            if total_interventions > 0:
                success_rate = successful / total_interventions
                success_score = success_rate * 30
            else:
                success_score = 15  # Default for new operators

            total_score = experience_score + role_score + success_score
            
            scores[op.id] = {
                'operator': op,
                'score': total_score,
                'experience': experience_score,
                'role': role_score,
                'success': success_score,
                'current_load': op.current_load,
            }

        return scores

    def _calculate_client_scores(self, credits):
        """
        Calculate priority score for each credit/client (0-100)
        Higher score = more problematic = needs experienced operator
        Factors:
        - Overdue amount (0-30 points)
        - Days past due (0-30 points)
        - Risk segment from scoring (0-25 points)
        - Number of failed interventions (0-15 points)
        """
        scores = {}
        
        # Get max values for normalization
        max_overdue = 500000  # Normalize against 500k
        max_days = 180  # Normalize against 180 days

        for credit in credits:
            client = credit.client
            
            # Get latest credit state for overdue info
            latest_state = credit.states.order_by('-state_date').first()
            overdue_amount = float(latest_state.overdue_principal) if latest_state else 0
            
            # Calculate days past due
            if credit.status in ['overdue', 'default']:
                # Estimate from latest state or use monthly payment as indicator
                days_overdue = min(180, int(overdue_amount / max(float(credit.monthly_payment), 1) * 30))
            else:
                days_overdue = 0

            # Overdue amount score (0-30)
            amount_score = min(30, (overdue_amount / max_overdue) * 30)

            # Days overdue score (0-30)
            days_score = min(30, (days_overdue / max_days) * 30)

            # Risk segment score (0-25)
            latest_scoring = credit.scorings.order_by('-calculation_date').first()
            if latest_scoring:
                segment_weights = {'low': 5, 'medium': 12, 'high': 20, 'critical': 25}
                risk_score = segment_weights.get(latest_scoring.risk_segment, 12)
            else:
                risk_score = 12  # Default medium risk

            # Failed interventions score (0-15)
            failed_interventions = Intervention.objects.filter(
                credit=credit,
                status__in=['no_answer', 'refuse']
            ).count()
            failed_score = min(15, failed_interventions * 3)

            priority = amount_score + days_score + risk_score + failed_score

            scores[credit.id] = {
                'credit': credit,
                'client': client,
                'priority': priority,
                'overdue_amount': overdue_amount,
                'days_overdue': days_overdue,
                'risk_segment': latest_scoring.risk_segment if latest_scoring else 'medium',
            }

        return scores

    def _distribute_clients(self, sorted_operators, sorted_clients, max_load, assignment_date):
        """
        Distribute clients to operators:
        - High priority clients go to experienced operators
        - Balance workload across operators
        """
        assignments = []
        operator_loads = {op_id: data['current_load'] for op_id, data in sorted_operators}
        
        # Split clients into priority tiers
        total_clients = len(sorted_clients)
        high_priority = sorted_clients[:int(total_clients * 0.3)]  # Top 30%
        medium_priority = sorted_clients[int(total_clients * 0.3):int(total_clients * 0.7)]
        low_priority = sorted_clients[int(total_clients * 0.7):]

        # Assign high priority to top operators
        top_operators = sorted_operators[:max(1, len(sorted_operators) // 3)]
        assignments.extend(self._assign_tier(high_priority, top_operators, operator_loads, max_load, assignment_date, 5))

        # Assign medium priority to mid-tier operators
        mid_operators = sorted_operators[len(sorted_operators) // 3:2 * len(sorted_operators) // 3]
        if not mid_operators:
            mid_operators = sorted_operators
        assignments.extend(self._assign_tier(medium_priority, mid_operators, operator_loads, max_load, assignment_date, 3))

        # Assign low priority to all operators (round-robin to balance)
        assignments.extend(self._assign_tier(low_priority, sorted_operators, operator_loads, max_load, assignment_date, 1))

        return assignments

    def _assign_tier(self, clients, operators, operator_loads, max_load, assignment_date, base_priority):
        """Assign a tier of clients to a set of operators"""
        assignments = []
        op_index = 0
        
        for credit_id, client_data in clients:
            # Find operator with lowest load in this tier
            available_ops = [(op_id, data) for op_id, data in operators if operator_loads[op_id] < max_load]
            
            if not available_ops:
                continue  # All operators at max load
            
            # Sort by current load (ascending) to balance
            available_ops.sort(key=lambda x: operator_loads[x[0]])
            op_id, op_data = available_ops[0]
            
            credit = client_data['credit']
            
            assignment = Assignment.objects.create(
                operator=op_data['operator'],
                debtor_name=client_data['client'].full_name,
                credit=credit,
                overdue_amount=Decimal(client_data['overdue_amount']).quantize(Decimal('0.01')),
                overdue_days=client_data['days_overdue'],
                priority=base_priority,
                assignment_date=assignment_date
            )
            assignments.append(assignment)
            operator_loads[op_id] += 1

        return assignments

    def _print_summary(self, assignments, operator_scores):
        """Print distribution summary"""
        self.stdout.write('\n--- Distribution Summary ---')
        
        # Group by operator
        from collections import defaultdict
        by_operator = defaultdict(list)
        for a in assignments:
            by_operator[a.operator_id].append(a)
        
        for op_id, op_assignments in sorted(by_operator.items(), key=lambda x: len(x[1]), reverse=True):
            op_data = operator_scores.get(op_id, {})
            op = op_data.get('operator')
            if op:
                total_amount = sum(float(a.overdue_amount) for a in op_assignments)
                avg_priority = sum(a.priority for a in op_assignments) / len(op_assignments)
                self.stdout.write(
                    f'  {op.full_name}: {len(op_assignments)} clients, '
                    f'total overdue: {total_amount:,.0f} ₽, '
                    f'avg priority: {avg_priority:.1f}, '
                    f'experience score: {op_data.get("score", 0):.1f}'
                )
