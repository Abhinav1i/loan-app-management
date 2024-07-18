import asyncio
import datetime
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User, Loan, Payment
from .serializers import UserSerializer, LoanSerializer, PaymentSerializer
from .tasks import calculate_credit_score

class RegisterUserView(APIView):
    def post(self, request, *args, **kwargs):
        serializer = UserSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.save()
            print(user.aadhar_id)
            calculate_credit_score(user.aadhar_id)
            return Response({'unique_user_id': user.aadhar_id}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ApplyLoanView(APIView):
    def post(self, request, *args, **kwargs):
        user = User.objects.get(aadhar_id=request.data['aadhar_id'])
        
        if user.credit_score < 450 or user.annual_income < 150000:
            return Response({'error': 'User does not qualify for a loan'}, status=status.HTTP_400_BAD_REQUEST)
        
        loan_amount = request.data['loan_amount']
        loan_term = request.data['term_period']
        interest_rate = request.data['interest_rate']
        monthly_income = user.annual_income / 12
        type = request.data['loan_type']
        
        r = interest_rate / (12 * 100) 
        n = loan_term  
        emi = loan_amount * r * (1 + r)**n / ((1 + r)**n - 1)
        
        if (type == 'Car' and loan_amount >750000) or (type=='Home' and loan_amount > 8500000) or (type=='Educational' and loan_amount > 5000000) or (type =='Personal' and loan_amount > 1000000):
            return Response({'error':'Loan Amount is out of bound'} , status=status.HTTP_400_BAD_REQUEST)
    
        if emi > (6 * monthly_income)/10:
            return Response({'error': 'EMI amount exceeds 60% of the monthly income'}, status=status.HTTP_400_BAD_REQUEST)
        
        if interest_rate < 14:
            return Response({'error': 'Interest rate must be at least 14%'}, status=status.HTTP_400_BAD_REQUEST)
        
        total_payment = emi * loan_term
        total_interest_earned = abs(total_payment - loan_amount)
        print(total_interest_earned)
        
        if total_interest_earned <= 10000:
            return Response({'error': 'Total interest earned must be greater than 10,000'}, status=status.HTTP_400_BAD_REQUEST)
        
        emi_due_dates = []
        disbursement_date = datetime.date.today()
        first_due_date = disbursement_date.replace(day=1) + datetime.timedelta(days=32)
        first_due_date = first_due_date.replace(day=1)
        for i in range(loan_term):
            due_date = first_due_date + datetime.timedelta(days=32 * i)
            due_date = due_date.replace(day=1)
            emi_due_dates.append({
                'date': due_date.strftime('%Y-%m-%d'),
                'amount_due': round(emi, 2)
            })
        
        
        loan_data = request.data.copy()
        loan_data['user'] = user.id
        loan_data['emi_due_dates'] = emi_due_dates
        print(f"Loan data is {loan_data}" )
        serializer = LoanSerializer(data=loan_data)
        if serializer.is_valid():
            loan = serializer.save()
            return Response({'loan_id': loan.loan_id}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class MakePaymentView(APIView):
    def post(self, request, *args, **kwargs):
        loan_id = request.data.get('loan_id')
        amount = request.data.get('amount')
        payment_date = request.data.get('payment_date', datetime.date.today().strftime('%Y-%m-%d'))

        if not loan_id or amount is None:
            return Response({'error': 'Loan_id and amount are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            loan = Loan.objects.get(loan_id=loan_id)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)

        today = datetime.date.today()
        next_due_date = None
        for emi_date in loan.emi_due_dates:
            due_date = datetime.datetime.strptime(emi_date['date'], '%Y-%m-%d').date()
            if due_date > today:
                next_due_date = due_date
                break

        if not next_due_date:
            return Response({'error': 'No upcoming EMIs found'}, status=status.HTTP_400_BAD_REQUEST)

        if Payment.objects.filter(loan=loan, emi_due_date=next_due_date).exists():
            return Response({'error': 'Payment already made for this due date'}, status=status.HTTP_400_BAD_REQUEST)

        for emi_date in loan.emi_due_dates:
            due_date = datetime.datetime.strptime(emi_date['date'], '%Y-%m-%d').date()
            if due_date < next_due_date and emi_date['amount_due'] > 0:
                return Response({'error': 'Previous EMIs are due'}, status=status.HTTP_400_BAD_REQUEST)

        due_amount = next((d['amount_due'] for d in loan.emi_due_dates if d['date'] == next_due_date.strftime('%Y-%m-%d')), None)
        if due_amount is None:
            return Response({'error': 'Invalid EMI due date'}, status=status.HTTP_400_BAD_REQUEST)

        payment_data = {
            'loan': loan.id,
            'amount': amount,
            'payment_date': payment_date,
            'emi_due_date': next_due_date.strftime('%Y-%m-%d')
        }
        serializer = PaymentSerializer(data=payment_data)
        if serializer.is_valid():
            serializer.save()

            if amount != due_amount:
                remaining_amount = max(0 , due_amount - amount)
        
                for emi_date in loan.emi_due_dates:
                    if emi_date['date'] == next_due_date.strftime('%Y-%m-%d'):
                        emi_date['amount_due'] = remaining_amount
                        break
                loan.save()
            print("get value")
            print(loan)
            return Response({'message': 'Loan amount updated'}, status=status.HTTP_200_OK)
        return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class GetStatementView(APIView):
     def get(self, request, *args, **kwargs):
        loan_id = request.query_params.get('loan_id')

        if not loan_id:
            return Response({'error': 'Loan_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            loan = Loan.objects.get(loan_id=loan_id)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found or closed'}, status=status.HTTP_404_NOT_FOUND)

        past_transactions = []
        payments = Payment.objects.filter(loan=loan).order_by('payment_date')
        for payment in payments:
            emi_due_date = payment.emi_due_date.strftime('%Y-%m-%d')
            amount_paid = payment.amount
            principal = amount_paid / (1 + (loan.interest_rate / 100))
            interest = amount_paid - principal
            past_transactions.append({
                'date': payment.payment_date.strftime('%Y-%m-%d'),
                'principal': principal,
                'interest': interest,
                'amount_paid': amount_paid
            })

        upcoming_transactions = []
        for emi in loan.emi_due_dates:
            due_date = datetime.datetime.strptime(emi['date'], '%Y-%m-%d').date()
            if due_date >= datetime.date.today():
                upcoming_transactions.append({
                    'date': emi['date'],
                    'amount_due': emi['amount_due']
                })

        return Response({
            'error': None,
            'past_transactions': past_transactions,
            'upcoming_transactions': upcoming_transactions
        }, status=status.HTTP_200_OK)
