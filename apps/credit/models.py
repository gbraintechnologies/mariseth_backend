from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.shared.models import BaseModel


class Credit(BaseModel):
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('overdue', 'Overdue'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    APPROVAL_STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('pending', 'Pending'),
    ]
    TYPE_CHOICES = [
        ('fertilizer', 'Fertilizer'),
        ('hybrid_seed', 'Hybrid Seed'),
        ('agro_chemicals', 'Agro Chemicals'),
        ('mechanisation', 'Mechanisation(Ploughing)'),
    ]
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    credit_id = models.CharField(max_length=50, unique=True)
    farmer = models.ForeignKey('farm.Farmer', on_delete=models.CASCADE)
    input_credits = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    quantity_metric = models.ForeignKey('shared.CustomType', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='credit_quantity_metrics',
                                        limit_choices_to={'category_name': 'quantity_metric'})
    notes = models.TextField(blank=True, null=True)
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    issue_date = models.DateField()
    due_date = models.DateField()
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, null=True, blank=True,
                                        validators=[MinValueValidator(0)])
    outstanding_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='inactive')
    approval_status = models.CharField(max_length=10, choices=APPROVAL_STATUS_CHOICES, default='pending')
    denial_notes = models.TextField(blank=True, null=True)
    main_crops = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"Credit {self.id} - {self.farmer.first_name} {self.farmer.last_name}"

    def update_payment_status(self):
        """Automatically update payment status based on outstanding amount"""
        if self.outstanding_amount <= Decimal(0.00):
            self.payment_status = 'paid'
        elif self.outstanding_amount < self.credit_amount:
            self.payment_status = 'partial'
        else:
            self.payment_status = 'active'
        self.save()


class CreditPayback(BaseModel):
    PAYBACK_METHOD_CHOICES = [
        ('cash_payback', 'Cash Payback'),
        ('crop_exchange', 'Crop Exchange'),
    ]
    STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('partial', 'Partial'),
    ]

    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    credit = models.ForeignKey('Credit', on_delete=models.CASCADE, related_name='paybacks')
    payback_method = models.CharField(max_length=20, choices=PAYBACK_METHOD_CHOICES, blank=True, null=True,
                                      help_text="Select payment method - cash or crop exchange")
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount being paid back in GHe")
    # Add these two new fields
    outstanding_before = models.DecimalField(max_digits=10, decimal_places=2,
                                             help_text="Outstanding amount before this payment")
    outstanding_after = models.DecimalField(
        max_digits=10, decimal_places=2, help_text="Outstanding amount after this payment"
    )
    product = models.ForeignKey('farm.Product', on_delete=models.SET_NULL, null=True, blank=True,
                                help_text="Product traded in crop exchange (e.g. Maize)")
    quantity_bags = models.IntegerField(validators=[MinValueValidator(0)], blank=True, null=True,
                                        help_text="Number of bags/units exchanged")
    # warehouse = models.ForeignKey('Warehouse', on_delete=models.SET_NULL, null=True, blank=True,
    #                               help_text="Warehouse location for crop storage")
    comments = models.TextField(blank=True, null=True, help_text="Additional notes about this payment")
    date_paid = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='paid')

    def __str__(self):
        return f"Payback {self.id} - {self.credit.id}"


class CreditChangeLog(BaseModel):
    EVENT_CHOICES = [
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('status_change', 'Status Change'),
        ('amount_change', 'Amount Change'),
        ('payment_created', 'Payment Created'),
        ('payment_updated', 'Payment Updated'),
        ('field_updated', 'Field Updated'),
    ]

    credit = models.ForeignKey(Credit, on_delete=models.CASCADE, related_name='history')
    payback = models.ForeignKey(CreditPayback, null=True, blank=True, on_delete=models.SET_NULL)
    event = models.CharField(max_length=20, choices=EVENT_CHOICES)
    notes = models.TextField(blank=True, null=True)
    old_value = models.CharField(max_length=255, blank=True, null=True)
    new_value = models.CharField(max_length=255, blank=True, null=True)
    field_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"History {self.id} - {self.credit.id}"
