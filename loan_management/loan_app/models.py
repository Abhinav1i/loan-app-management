from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from uuid import uuid4

class UserManager(BaseUserManager):
    def create_user(self, aadhar_id, name, email, annual_income, password=None):
        if not email:
            raise ValueError('Users must have an email address')
        if not aadhar_id:
            raise ValueError('Users must have an Aadhar ID')
        
        user = self.model(
            aadhar_id=aadhar_id,
            name=name,
            email=self.normalize_email(email),
            annual_income=annual_income,
        )
        
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, aadhar_id, name, email, annual_income, password=None):
        user = self.create_user(
            aadhar_id=aadhar_id,
            name=name,
            email=email,
            annual_income=annual_income,
            password=password,
        )
        user.is_admin = True
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    aadhar_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    email = models.EmailField(max_length=255, unique=True)
    annual_income = models.DecimalField(max_digits=15, decimal_places=2)
    credit_score = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    
    objects = UserManager()

    USERNAME_FIELD = 'aadhar_id'
    REQUIRED_FIELDS = ['name', 'email', 'annual_income']

    def __str__(self):
        return self.email

class Loan(models.Model):
    LOAN_TYPES = [
        ('Car', 'Car'),
        ('Home', 'Home'),
        ('Education', 'Education'),
        ('Personal', 'Personal'),
    ]
    
    loan_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    loan_type = models.CharField(max_length=10, choices=LOAN_TYPES)
    loan_amount = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=4, decimal_places=2)
    term_period = models.IntegerField()
    disbursement_date = models.DateField()
    emi_due_dates = models.JSONField(default=list)
    
    def __str__(self):
        return str(self.loan_id)

class Payment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    emi_due_date = models.DateField() 

    def __str__(self):
        return f"Payment of {self.amount} on {self.payment_date} for loan {self.loan.id}"