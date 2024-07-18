from rest_framework import serializers
from .models import User, Loan, Payment

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['aadhar_id', 'name', 'email', 'annual_income']

class LoanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Loan
        fields = ['loan_id', 'user', 'loan_type', 'loan_amount', 'interest_rate', 'term_period', 'disbursement_date', 'emi_due_dates']

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['loan', 'amount', 'payment_date','emi_due_date']
