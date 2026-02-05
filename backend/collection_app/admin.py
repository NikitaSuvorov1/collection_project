from django.contrib import admin
from .models import Operator, Client, Credit, CreditState, Payment, Intervention, ScoringResult, Assignment, CreditApplication

admin.site.register(Operator)
admin.site.register(Client)
admin.site.register(Credit)
admin.site.register(CreditState)
admin.site.register(Payment)
admin.site.register(Intervention)
admin.site.register(ScoringResult)
admin.site.register(Assignment)
admin.site.register(CreditApplication)
