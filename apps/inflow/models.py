# Create your models here.
# models.py
from django.contrib.auth import get_user_model
from django.db import models

from apps.shared.models import BaseModel

User = get_user_model()


class InflowOrder(BaseModel):
    STATUS_CHOICES = [
        ('delivery_inspection', 'Delivery Inspection'),
        ('order_approval', 'Order Approval'),
        ('approved', 'Approved'),
        ('cancelled', 'Cancelled')
    ]
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    order_id = models.CharField(max_length=50, unique=True)
    aggregator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='aggregator_orders')
    procurement_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                            related_name='procurement_orders')
    destination_warehouse = models.ForeignKey('warehouse.Warehouse', on_delete=models.CASCADE)
    order_creation_date = models.DateField()
    expected_delivery_date = models.DateField()
    actual_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='delivery_inspection')
    total_bags = models.IntegerField(default=0)
    order_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    additional_costs = models.TextField(blank=True)
    additional_cost_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_products_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    comments = models.TextField(blank=True)
    waybill_id = models.CharField(max_length=50, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.order_id} - {self.get_status_display()}"


class InflowOrderProduct(BaseModel):
    serial_number = models.CharField(max_length=50, unique=True)
    order = models.ForeignKey(InflowOrder, on_delete=models.CASCADE, related_name='products')
    product = models.ForeignKey('farm.Product', on_delete=models.CASCADE)
    farm = models.ForeignKey('farm.Farm', on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    problematic_quantity = models.IntegerField(default=0)
    reason = models.CharField(max_length=255, blank=True)
    comment = models.TextField(blank=True)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('order', 'product', 'farm')

    def __str__(self):
        return f"{self.id} - {self.product.name} - {self.farm.name}"


class InflowMedia(BaseModel):
    order = models.ForeignKey(InflowOrder, on_delete=models.CASCADE, related_name='media_files')
    file = models.FileField(upload_to='inflow_media/')
    name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_complaint = models.BooleanField(default=False)
    related_product = models.ForeignKey(InflowOrderProduct, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.name


class InflowOrderHistory(BaseModel):
    EVENT_CHOICES = [
        ('status_change', 'Status Change'),
        ('comment', 'Comment'),
        ('document_upload', 'Document Upload'),
    ]

    order = models.ForeignKey(InflowOrder, on_delete=models.CASCADE, related_name='history')
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    notes = models.TextField(blank=True)
    old_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255, blank=True)
    field_name = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.order.order_id} - {self.get_event_type_display()}"
