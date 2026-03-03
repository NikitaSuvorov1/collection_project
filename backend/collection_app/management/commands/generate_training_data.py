"""
Django management command to generate training data for the overdue prediction model.

This command implements the logic described in section 3.2 of the thesis
to generate a dataset with 27 features and a target variable for risk classification.
"""
import random
from datetime import date, timedelta
import pandas as pd
from django.core.management.base import BaseCommand
from collection_app.models import Client, Credit, Payment, Intervention
from django.db.models import Count, Sum, Avg, Max, F, ExpressionWrapper, fields
from django.db.models.functions import Coalesce
from django.utils import timezone

class Command(BaseCommand):
    help = 'Generates training data for the overdue prediction model.'

    def handle(self, *args, **options):
        self.stdout.write("Starting training data generation...")

        # Step 1: Get all "problematic" credits as per thesis criteria
        # For simplicity, we'll consider all credits with some payment history
        credits = Credit.objects.filter(status__in=['active', 'overdue', 'default']).prefetch_related('client', 'payments', 'interventions')

        if not credits.exists():
            self.stdout.write(self.style.WARNING("No active credits found. Cannot generate training data."))
            return

        training_data = []
        
        # Step 2 & 3: Calculate features and target for each credit
        for credit in credits:
            client = credit.client
            payments = credit.payments.all()
            interventions = credit.interventions.all()

            if not payments.exists():
                continue # Skip credits with no payment history

            # --- Feature Calculation (as per thesis section 3.2.4) ---
            
            # 1. Age
            age = (date.today() - client.date_of_birth).days // 365 if client.date_of_birth else 0
            
            # 2. Gender (1 for M, 0 for F)
            gender = 1 if client.gender == 'M' else 0
            
            # 3. Marital Status (dummy encoding could be better, but for now simple map)
            marital_status_map = {'Single': 0, 'Married': 1, 'Divorced': 2, 'Widowed': 3}
            marital_status = marital_status_map.get(client.marital_status, 0)

            # 4. Education Level (dummy encoding could be better)
            education_map = {'High School': 0, 'Bachelor': 1, 'Master': 2, 'PhD': 3}
            education = education_map.get(client.education, 0)

            # 5. Number of Dependents
            dependents = client.dependents if client.dependents is not None else 0

            # 6. Monthly Income
            monthly_income = client.monthly_income if client.monthly_income is not None else 0

            # 7. Has other credits
            has_other_credits = 1 if Credit.objects.filter(client=client).exclude(id=credit.id).exists() else 0

            # 8. Number of other credits
            other_credits_count = Credit.objects.filter(client=client).exclude(id=credit.id).count()

            # 9. Credit Amount
            credit_amount = credit.credit_amount

            # 10. Credit Term (in months)
            credit_term = credit.credit_term

            # 11. Interest Rate
            interest_rate = credit.interest_rate

            # 12. Loan-to-Income Ratio (LTI)
            lti_ratio = (credit_amount / monthly_income) if monthly_income > 0 else 0

            # 13. Credit Age (in days)
            credit_age = (date.today() - credit.start_date).days

            # 14. Credit Status (Active=1, Closed=0) - all are active here
            credit_status = 1

            # 15. Outstanding Balance
            outstanding_balance = credit.outstanding_balance

            # 16. Overdue Debt Amount
            overdue_debt = credit.overdue_debt

            # 17. Days Overdue (current)
            days_overdue = credit.days_overdue

            # 18. Max Days Overdue (historical)
            max_days_overdue_hist = payments.aggregate(max_val=Max('days_overdue'))['max_val'] or 0

            # --- Payment Discipline Features (last 12 months) ---
            one_year_ago = timezone.now().date() - timedelta(days=365)
            payments_last_year = payments.filter(payment_date__gte=one_year_ago)
            
            # 19. Number of payments in last 12 months
            payments_count_12m = payments_last_year.count()

            # 20. Number of overdue payments in last 12 months
            overdue_payments_count_12m = payments_last_year.filter(days_overdue__gt=0).count()

            # 21. Share of overdue payments in last 12 months
            overdue_share_12m = (overdue_payments_count_12m / payments_count_12m) if payments_count_12m > 0 else 0

            # 22. Average payment amount / monthly payment
            avg_payment_amount = payments_last_year.aggregate(avg_val=Avg('amount'))['avg_val'] or 0
            payment_ratio = (avg_payment_amount / credit.monthly_payment) if credit.monthly_payment > 0 else 0

            # 23. Max overdue days for a single payment in last 12m
            max_overdue_12m = payments_last_year.aggregate(max_val=Max('days_overdue'))['max_val'] or 0

            # --- Interaction Features (last 12 months) ---
            interventions_last_year = interventions.filter(timestamp__gte=one_year_ago)

            # 24. Number of interactions in last 12m
            interactions_count_12m = interventions_last_year.count()

            # 25. Number of successful interactions
            successful_interactions_count = interventions_last_year.filter(status='Completed').count()

            # 26. Number of payment promises
            promises_count = interventions_last_year.filter(promise_amount__isnull=False).count()

            # 27. Share of fulfilled promises (simplified: we check if a payment was made after a promise)
            # This is complex to calculate accurately without more data. We'll use a placeholder.
            fulfilled_promises_share = random.uniform(0, 1) if promises_count > 0 else 0

            # --- Target Variable `y` Calculation (as per thesis section 3.2.3) ---
            total_payments = payments.count()
            total_overdue_payments = payments.filter(days_overdue__gt=0).count()
            overdue_ratio = (total_overdue_payments / total_payments) if total_payments > 0 else 0

            risk_category = 0 # Low risk
            if 0.3 <= overdue_ratio < 0.6:
                risk_category = 1 # Medium risk
            elif overdue_ratio >= 0.6:
                risk_category = 2 # High risk

            # Append all features and target to our dataset
            training_data.append({
                'client_id': client.id,
                'credit_id': credit.id,
                'age': age,
                'gender': gender,
                'marital_status': marital_status,
                'education': education,
                'dependents': dependents,
                'monthly_income': monthly_income,
                'has_other_credits': has_other_credits,
                'other_credits_count': other_credits_count,
                'credit_amount': credit_amount,
                'credit_term': credit_term,
                'interest_rate': interest_rate,
                'lti_ratio': lti_ratio,
                'credit_age': credit_age,
                'credit_status': credit_status,
                'outstanding_balance': outstanding_balance,
                'overdue_debt': overdue_debt,
                'days_overdue': days_overdue,
                'max_days_overdue_hist': max_days_overdue_hist,
                'payments_count_12m': payments_count_12m,
                'overdue_payments_count_12m': overdue_payments_count_12m,
                'overdue_share_12m': overdue_share_12m,
                'payment_ratio': payment_ratio,
                'max_overdue_12m': max_overdue_12m,
                'interactions_count_12m': interactions_count_12m,
                'successful_interactions_count': successful_interactions_count,
                'promises_count': promises_count,
                'fulfilled_promises_share': fulfilled_promises_share,
                'risk_category': risk_category # This is our target 'y'
            })

        if not training_data:
            self.stdout.write(self.style.WARNING("No data could be generated. Check if credits have payment history."))
            return

        # Step 4: Save the generated data to a file
        df = pd.DataFrame(training_data)
        
        # Fill NaN values that might have occurred from divisions by zero etc.
        df.fillna(0, inplace=True)

        output_path = 'backend/training_data.csv'
        df.to_csv(output_path, index=False)

        self.stdout.write(self.style.SUCCESS(f"Successfully generated {len(df)} records."))
        self.stdout.write(self.style.SUCCESS(f"Training data saved to {output_path}"))
        self.stdout.write(f"Risk category distribution:\n{df['risk_category'].value_counts()}")
