import os
from celery import shared_task
from .models import User
import csv

@shared_task
def calculate_credit_score(aadhar_id):
    script_dir = os.path.dirname(os.path.abspath(__file__))

    csv_path = os.path.join(script_dir, 'transactions.csv')
    with open(csv_path, 'r') as file:
        reader = csv.DictReader(file)
        transactions = [row for row in reader if row['user'] == aadhar_id]
    
    total_balance=0
    print(transactions)
    for transaction in transactions:
        if transaction['transaction_type']=='CREDIT':
            total_balance += int(transaction['amount'])
        else:
            total_balance -= int(transaction['amount'])
    
    print("Total Balance")
    print(total_balance)
    if total_balance >= 1000000:
        credit_score = 900
    elif total_balance <= 100000:
        credit_score = 300
    else:
        credit_score = 300 + ((total_balance) // 15000) * 10
    
    user = User.objects.get(aadhar_id=aadhar_id)
    user.credit_score = credit_score
    user.save()
