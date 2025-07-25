from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from apps.shared.models import BaseModel


class Expense(BaseModel):
    ORDER_TYPE_CHOICES = (
        ('inflow', 'Inflow'),
        ('outflow', 'Outflow'),
    )

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    order = GenericForeignKey('content_type', 'object_id')
    order_type = models.CharField(max_length=10, choices=ORDER_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Expense"
        verbose_name_plural = "Expenses"
        ordering = ['-date_created']

    def __str__(self):
        return f"Expense for {self.order_type} on {self.order.order_id} - {self.amount}"