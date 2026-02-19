from django.db import models
from django.core.validators import MinLengthValidator, MaxLengthValidator

class Initiative(models.Model):
    DEPARTMENT_CHOICES = [
        ('Insurance', 'Insurance'),
        ('Claims', 'Claims'),
        ('Membership', 'Membership'),
        ('Travel', 'Travel'),
        ('Automotive Services', 'Automotive Services'),
        ('D&R', 'D&R'),
        ('IT', 'IT'),
        ('Human Resources', 'Human Resources'),
        ('Experience Organization', 'Experience Organization'),
        ('Data/Insight', 'Data/Insight'),
        ('Finance & Procurement', 'Finance & Procurement'),
        ('Field Operations', 'Field Operations'),
    ]

    STATUS_CHOICES = [
        ('Live', 'Live'),
        ('Pilot', 'Pilot'),
        ('In-progress', 'In-progress'),
        ('Planning', 'Planning'),
    ]

    BENEFIT_NAME_CHOICES = [
        ('Productivity Gain', 'Productivity Gain'),
        ('New Business', 'New Business'),
    ]

    name = models.CharField(max_length=32, default="Untitled Initiative")
    requester_name = models.CharField(max_length=32)
    lob_owner = models.CharField(max_length=32, verbose_name="LOB Owner")
    description = models.TextField(max_length=2048)
    it_owner = models.CharField(max_length=32, verbose_name="IT Owner")
    it_owner_email = models.EmailField(max_length=128, verbose_name="IT Owner Email", default="it@example.com")
    department = models.CharField(max_length=32, choices=DEPARTMENT_CHOICES)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES)
    technology = models.CharField(max_length=32)
    value = models.TextField(max_length=1024, verbose_name="Business Value")
    benefit_name = models.CharField(max_length=32, choices=BENEFIT_NAME_CHOICES)
    
    # Webhook Integration
    webhook_key = models.CharField(max_length=64, unique=True, blank=True, null=True, help_text="Secret key for external reporting via webhook")
    
    # New Multiplier Fields
    kpi_name = models.CharField(max_length=64, blank=True, null=True, verbose_name="KPI Name", help_text="Name of the KPI to be tracked")
    multiplier_minutes = models.FloatField(default=0, help_text="KPI x this = minutes saved")
    multiplier_dollars = models.FloatField(default=0, help_text="Minutes saved x this = dollars saved")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.webhook_key:
            import secrets
            self.webhook_key = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.department})"

class WebhookAuditLog(models.Model):
    initiative = models.ForeignKey(Initiative, on_delete=models.SET_NULL, null=True, blank=True)
    status_code = models.IntegerField()
    payload = models.JSONField()
    response_body = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Webhook Log - {self.initiative.name if self.initiative else 'Unknown'} - {self.created_at}"

class RealizedBenefit(models.Model):
    initiative = models.ForeignKey(Initiative, on_delete=models.CASCADE, related_name='realized_benefits')
    month = models.DateField()
    
    # KPI Tracking Fields
    kpi_value = models.FloatField(default=0)
    
    # Manual Input (for New Business)
    revenue_impact = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def calculated_minutes(self):
        if self.initiative.benefit_name == 'Productivity Gain':
            return self.kpi_value * self.initiative.multiplier_minutes
        return 0

    @property
    def calculated_dollars(self):
        if self.initiative.benefit_name == 'Productivity Gain':
            return self.kpi_value * self.initiative.multiplier_minutes * self.initiative.multiplier_dollars
        return 0

    class Meta:
        ordering = ['-month']
        unique_together = ('initiative', 'month')

    def __str__(self):
        return f"{self.initiative.name} - {self.month}"
