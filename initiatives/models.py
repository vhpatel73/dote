from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator

class Initiative(models.Model):
    DEPARTMENT_CHOICES = [
        ('Insurance', 'Insurance'),
        ('Claims', 'Claims'),
        ('Membership', 'Membership'),
        ('Travel', 'Travel'),
        ('ERS', 'ERS'),
        ('D&R', 'D&R'),
        ('IT', 'IT'),
        ('HR', 'HR'),
        ('Others', 'Others'),
    ]

    STATUS_CHOICES = [
        ('Live', 'Live'),
        ('Pilot', 'Pilot'),
        ('In-progress', 'In-progress'),
        ('Planning', 'Planning'),
    ]

    requester_name = models.CharField(max_length=32)
    description = models.TextField(max_length=2048)
    lob_owner = models.CharField(max_length=32, verbose_name="LOB Owner")
    it_owner = models.CharField(max_length=32, verbose_name="IT Owner")
    department = models.CharField(max_length=32, choices=DEPARTMENT_CHOICES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES)
    technology = models.CharField(max_length=32)
    value = models.TextField(max_length=1024)
    benefit_name = models.CharField(max_length=64)
    benefit = models.FloatField()  # double in DB

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.requester_name} - {self.department} - {self.status}"

class RealizedBenefit(models.Model):
    BENEFIT_TYPE_CHOICES = [
        ('Dollars saved', 'Dollars saved'),
        ('Hours saved', 'Hours saved'),
        ('Revenue increased', 'Revenue increased'),
        ('Member Acquired', 'Member Acquired'),
    ]

    initiative = models.ForeignKey(Initiative, on_delete=models.CASCADE, related_name='realized_benefits')
    month = models.DateField()
    benefit_type = models.CharField(max_length=64, choices=BENEFIT_TYPE_CHOICES)
    amount = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-month']
        unique_together = ('initiative', 'month', 'benefit_type')

    def __str__(self):
        return f"{self.initiative.requester_name} - {self.month} - {self.benefit_type}"
