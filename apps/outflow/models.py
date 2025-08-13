from django.db import models
from django.utils import timezone

from apps.shared.models import BaseModel


class OutflowOrder(BaseModel):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('availability_check', 'Availability Check'),
        ('truck_pickup', 'Truck Pickup'),
        ('delivered', 'Delivered'),
        ('partial_payment', 'Partial Payment'),
        ('full_payment', 'Full Payment'),
        ('complete', 'Complete'),
        ('cancelled', 'Cancelled'),
        ('approved', 'Approved'),
    )

    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    order_id = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    customer = models.ForeignKey('customers.Customer', on_delete=models.CASCADE)
    procurement_officer = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True,
                                            related_name='outflow_procurement_orders')
    destination = models.CharField(max_length=255)
    expected_delivery_date = models.DateField()
    actual_delivery_date = models.DateField(null=True, blank=True)
    total_quantity = models.IntegerField(default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    extra_comments = models.TextField(blank=True)
    additional_costs = models.TextField(blank=True)
    additional_cost_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    waybill_id = models.CharField(max_length=50, unique=True, blank=True, null=True)

    class Meta:
        verbose_name = 'Outflow Order'
        verbose_name_plural = 'Outflow Orders'

    def __str__(self):
        return self.order_id

    def log_status_change(self, old_status, new_status, user=None):
        """
        Log status changes for the outflow order
        """
        OutflowOrderHistory.objects.create(
            outflow_order=self,
            field_name='status',
            old_value=old_status,
            new_value=new_status,
            created_by=user,
        )

    def log_field_change(self, field_name, old_value, new_value, user=None):
        """
        Generic method to log any field change
        """
        OutflowOrderHistory.objects.create(
            outflow_order=self,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else '',
            new_value=str(new_value) if new_value is not None else '',
            created_by=user,
        )

    def mark_as_availability_checked_if_all_verified(self, verified_warehouse=None, user=None):
        """
        - Send a notification when a warehouse is verified.
        - If all warehouses are verified, update status and notify procurement officer.
        """
        # if verified_warehouse:
        #     send_notification(
        #         recipient=self.procurement_officer,
        #         message=f"{verified_warehouse.warehouse.name} has completed availability check for order {self.order_id}."
        #     )

        # Check if all warehouses are now verified
        if not self.warehouses.exclude(status='verified').exists():
            old_status = self.status
            self.status = 'availability_check'
            self.save()

            # ADD LOGS
            self.log_status_change(
                old_status=old_status,
                new_status='availability_check',
                user=user,
            )

            # send_notification(
            #     recipient=self.procurement_officer,
            #     message=f"All warehouses have verified availability for order {self.order_id}. Ready for truck pickup."
            # )

    def update_status_to_truck_pickup_if_ready(self, picked_warehouse=None, user=None):
        """
        - Sends notification that a warehouse has been picked up.
        - If all warehouses are picked up, update status and notify aggregator.
        """
        # if picked_warehouse:
        # send_notification(
        #     group='aggregators',
        #     message=f"Truck has picked up items from {picked_warehouse.warehouse.name} for order {self.order_id}"
        # )

        if not self.warehouses.exclude(status='order_pickup').exists():
            old_status = self.status
            self.status = 'truck_pickup'
            self.save()

            # ADD LOGS
            self.log_status_change(
                old_status=old_status,
                new_status='truck_pickup',
                user=user,
            )

            # send_notification(
            #     group='aggregators',
            #     message=f"All warehouses have completed pickup for order {self.order_id}. Truck is on the move."
            # )


class OutflowOrderPayments(BaseModel):
    PAYMENT_TYPES_CHOICES = (
        ('full', 'Full Payment'),
        ('partial', 'Partial Payment')
    )

    PAYMENT_METHOD_CHOICES = (
        ('mobile_money', 'Mobile Money'),
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer')
    )

    payment_date = models.DateTimeField(default=timezone.now)
    outflow_order = models.ForeignKey(OutflowOrder, on_delete=models.CASCADE, related_name='payments')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    amount_due = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES_CHOICES, default='full')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='cash')
    paid_to = models.CharField(max_length=255, blank=True, null=True)
    mobile_money_number = models.CharField(max_length=20, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    bank_account_number = models.CharField(max_length=20, blank=True, null=True)
    bank_account_name = models.CharField(max_length=255, blank=True, null=True)
    invoice_id = models.CharField(max_length=50, unique=True, blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Outflow Order Payment'
        verbose_name_plural = 'Outflow Order Payments'


class OutflowOrderHistory(BaseModel):
    STATUS_CHOICES = (
        ('availability_check', 'Availability Check'),
        ('truck_pickup', 'Truck Pickup'),
        ('delivered', 'Delivered'),
        ('partial_payment', 'Partial Payment'),
        ('full_payment', 'Full Payment'),
        ('complete', 'Complete'),
        ('cancelled', 'Cancelled'),
        ('approved', 'Approved'),
    )

    outflow_order = models.ForeignKey(OutflowOrder, on_delete=models.CASCADE, related_name='history')
    field_name = models.CharField(max_length=100)
    old_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Outflow Order History'


class OutflowOrderWarehouse(BaseModel):
    STATUS = (
        ('pending_verification', 'Pending Verification'),
        ('verified', 'Verified'),
        ('not_enough_stock', 'Not Enough Stock'),
        ('order_pickup', 'Order Pickup'),
        ('complete', 'Complete'),
    )

    outflow_order = models.ForeignKey(OutflowOrder, on_delete=models.CASCADE, related_name='warehouses')
    warehouse = models.ForeignKey('warehouse.Warehouse', on_delete=models.CASCADE)
    total_quantity = models.IntegerField(default=0)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS, default='pending_verification')

    class Meta:
        verbose_name = 'Outflow Order Warehouse'


class OutflowOrderWarehouseProduct(BaseModel):
    STATUS_CHOICES = (
        ('pending_verification', 'Pending Verification'),
        ('verified', 'Verified'),
        ('not_enough_stock', 'Not Enough Stock'),
    )

    outflow_order_warehouse = models.ForeignKey(OutflowOrderWarehouse, on_delete=models.CASCADE,
                                                related_name='products')
    serial_number = models.CharField(max_length=50, unique=True)
    product = models.ForeignKey('farm.Product', on_delete=models.CASCADE)
    expected_quantity = models.IntegerField(default=0)
    available_quantity = models.IntegerField(null=True, blank=True)
    price_per_unit = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_weight = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_verification')
    reason = models.CharField(max_length=255, blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    class Meta:
        verbose_name = 'Outflow Order Warehouse Product'
        unique_together = ('outflow_order_warehouse', 'product')


class OutflowOrderWarehouseImages(BaseModel):
    outflow_order_warehouse = models.ForeignKey(OutflowOrderWarehouse, on_delete=models.CASCADE,
                                                related_name='images')
    image = models.ImageField(upload_to='outflow/warehouse/')

    class Meta:
        verbose_name = 'Outflow Order Warehouse Image'


class OutflowOrderWarehouseHistory(BaseModel):
    STATUS_CHOICES = (
        ('verified', 'Verified'),
        ('not_enough_stock', 'Not Enough Stock'),
        ('order_pickup', 'Order Pickup'),
        ('complete', 'Complete'),
    )
    outflow_order_warehouse = models.ForeignKey(OutflowOrderWarehouse, on_delete=models.CASCADE,
                                                related_name='history')
    product = models.ForeignKey(
        OutflowOrderWarehouseProduct, null=True, blank=True, on_delete=models.CASCADE,
        related_name='history_entries'
    )
    field = models.CharField(max_length=100)
    old_value = models.CharField(max_length=255, blank=True)
    new_value = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Outflow Order Warehouse History'


class OutflowOrderDeliveryInformation(BaseModel):
    outflow_order = models.ForeignKey(OutflowOrder, on_delete=models.CASCADE, related_name='delivery_information')
    driver_name = models.CharField(max_length=255)
    driver_phone_number = models.CharField(max_length=15)
    driver_license_number = models.CharField(max_length=50)
    truck_license_number = models.CharField(max_length=50)
    destination = models.CharField(max_length=255)
    company = models.CharField(max_length=255)
    escort_required = models.BooleanField(default=False)
    escort_details = models.CharField(max_length=255)

    class Meta:
        verbose_name = 'Outflow Order Delivery Information'


class OutflowOrderDeliveryInformationWarehouse(BaseModel):
    outflow_order_delivery_information = models.ForeignKey(OutflowOrderDeliveryInformation, on_delete=models.CASCADE,
                                                           related_name='warehouses')
    warehouse = models.ForeignKey(
        'warehouse.Warehouse', on_delete=models.CASCADE, related_name='outflow_delivery_warehouse'
    )
    pick_up = models.BooleanField(default=False)
    pick_up_datetime = models.DateTimeField(null=True, blank=True)


class OutflowOrderDeliveryInformationImage(BaseModel):
    outflow_order_delivery_information = models.ForeignKey(OutflowOrderDeliveryInformation, on_delete=models.CASCADE,
                                                           related_name='images')
    image = models.ImageField(upload_to='outflow/delivery_information/')

    class Meta:
        verbose_name = 'Outflow Order Delivery Information '


class OutflowRecipientComplaint(BaseModel):
    outflow_order = models.ForeignKey(OutflowOrder, on_delete=models.CASCADE, related_name='customer_complaints')
    product = models.ForeignKey('farm.Product', on_delete=models.CASCADE)
    expected_quantity = models.IntegerField(default=0)
    problematic_quantity = models.IntegerField(default=0)
    reason = models.CharField(max_length=255)
    comments = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Outflow Recipient Complaint'


class OutflowRecipientComplaintImage(BaseModel):
    outflow_order = models.ForeignKey(OutflowOrder, on_delete=models.CASCADE, related_name='complaint_images')
    image = models.ImageField(upload_to='outflow/complaints/')

    class Meta:
        verbose_name = 'Outflow Recipient Complaint Image'
