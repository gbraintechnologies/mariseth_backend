from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


from apps.shared.models import BaseModel


class InputCredit(BaseModel):
    """
    Represents an input credit item.
    """
    input_credit_id = models.CharField(max_length=50, unique=True, null=True, blank=True)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    category = models.ForeignKey('shared.CustomType', on_delete=models.CASCADE,
                                 related_name="input_credits")
    name = models.CharField(max_length=255, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    quantity = models.PositiveIntegerField(null=True, blank=True, default=0)

    def __str__(self):
        return f"{self.id} - {self.name}"

    def change_approval_and_quantity(self, approved: bool, quantity: int):
        """
        Changes the approval status and quantity of the input credit.
        """
        # TODO: Implement the logic for changing approval and quantity.
        pass


class InputCreditPurchase(BaseModel):
    """
    Represents a purchase of an input credit.
    """
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    input_credit_purchase_id = models.CharField(max_length=50, unique=True)
    input_credit = models.ForeignKey(InputCredit, on_delete=models.CASCADE)
    purchase_date = models.DateField()
    source = models.CharField(max_length=255)
    warehouse = models.ForeignKey('warehouse.Warehouse', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, null=True)
    total_weight = models.FloatField()

    def __str__(self):
        return f"Purchase of {self.input_credit.name} on {self.purchase_date}"

    def add_input_credits(self, price, weight):
        """
        Increases the quantity of a product in the warehouse and in the input credit.
        """
        from apps.warehouse.models import InputCreditWarehouse, InputCreditWarehouseMovement
        input_credit_warehouse, created = InputCreditWarehouse.objects.get_or_create(
            input_credit=self.input_credit,
            warehouse=self.warehouse,
            defaults={
                'organization': self.warehouse.organization,
                'weight': 0,
                'quantity': 0
            }
        )
        input_credit_warehouse.increase_quantity(self.quantity, self.total_weight)
        if self.input_credit.quantity is None:
            self.input_credit.quantity = 0
        self.input_credit.quantity += self.quantity
        self.input_credit.price = price
        self.input_credit.weight = weight
        self.input_credit.save()

        # Create InputCreditWarehouseMovement for inflow
        InputCreditWarehouseMovement.objects.create(
            warehouse=self.warehouse,
            input_credit_warehouse=input_credit_warehouse,
            input_credit=self.input_credit,
            movement_type='inflow',
            quantity=self.quantity,
            weight=self.total_weight,
            record_date=self.purchase_date,
            inflow_source=self,
            amount=self.total_price,
            description=f"Inflow from Input Credit Purchase {self.input_credit_purchase_id}",
            notes=self.notes
        )


class Credit(BaseModel):
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('partial', 'Partial'),
        ('overdue', 'Overdue'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('fulfilled', 'Fulfilled'),
    ]
    APPROVAL_STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('denied', 'Denied'),
        ('pending', 'Pending'),
    ]

    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    credit_id = models.CharField(max_length=50, unique=True)
    farmer = models.ForeignKey('farm.Farmer', on_delete=models.CASCADE)
    input_credit_category = models.ForeignKey('shared.CustomType', on_delete=models.SET_NULL, null=True, blank=True,
                                              related_name='credits')
    input_credit = models.ForeignKey(InputCredit, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.IntegerField(validators=[MinValueValidator(0)])
    quantity_metric = models.ForeignKey('shared.CustomType', on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='credit_quantity_metrics',
                                        limit_choices_to={'category_name': 'quantity_metric'})
    notes = models.TextField(blank=True, null=True)
    credit_amount = models.DecimalField(max_digits=10, decimal_places=2)
    issue_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, null=True, blank=True,
                                        validators=[MinValueValidator(0)])
    outstanding_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='inactive')
    approval_status = models.CharField(max_length=10, choices=APPROVAL_STATUS_CHOICES, default='pending')
    denial_notes = models.TextField(blank=True, null=True)
    main_crops = models.CharField(max_length=255, blank=True, null=True)
    self_application = models.BooleanField(default=False)

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

    def decrease_input_credits(self):
        """
        Decreases the quantity of an input credit in the warehouse based on the credit's allocated quantities.
        """
        from apps.warehouse.models import InputCreditWarehouse, InputCreditWarehouseMovement
        
        # Get all CreditWarehouse entries for this Credit
        credit_warehouses = self.creditwarehouse_set.all()

        if not credit_warehouses.exists():
            raise ValueError("No warehouse allocations found for this credit.")

        for cw in credit_warehouses:
            try:
                input_credit_warehouse = InputCreditWarehouse.objects.get(
                    input_credit=self.input_credit,
                    warehouse=cw.warehouse
                )
                # Decrease quantity in InputCreditWarehouse
                input_credit_warehouse.decrease_quantity(cw.quantity, self.input_credit.weight * cw.quantity)

                # Create InputCreditWarehouseMovement for outflow
                InputCreditWarehouseMovement.objects.create(
                    warehouse=cw.warehouse,
                    input_credit_warehouse=input_credit_warehouse,
                    input_credit=self.input_credit,
                    movement_type='outflow',
                    quantity=cw.quantity,
                    weight=self.input_credit.weight * cw.quantity,
                    record_date=self.issue_date or timezone.now().date(),
                    outflow_source=self,
                    amount=self.credit_amount,
                    description=f"Outflow for Credit {self.credit_id} from {cw.warehouse.name}",
                    notes=self.notes
                )
            except InputCreditWarehouse.DoesNotExist:
                raise ValueError(f"Input credit {self.input_credit.name} not found in warehouse {cw.warehouse.name}.")
            except ValueError as e:
                raise ValueError(f"Insufficient stock for input credit {self.input_credit.name} in warehouse {cw.warehouse.name}: {e}")

        # Update the overall input_credit quantity (sum of all decreases)
        total_decreased_quantity = sum(cw.quantity for cw in credit_warehouses)
        self.input_credit.quantity -= total_decreased_quantity
        self.input_credit.save()

    def decrease_input_credit_for_warehouse(self, warehouse):
        """
        Decreases the quantity of an input credit in a specific warehouse.
        """
        from apps.warehouse.models import InputCreditWarehouse, InputCreditWarehouseMovement

        try:
            cw = self.creditwarehouse_set.get(warehouse=warehouse)
        except CreditWarehouse.DoesNotExist:
            raise ValueError("No allocation found for this credit in the specified warehouse.")

        if cw.is_fulfilled:
            raise ValueError("This credit has already been fulfilled for this warehouse.")

        try:
            input_credit_warehouse = InputCreditWarehouse.objects.get(
                input_credit=self.input_credit,
                warehouse=cw.warehouse
            )
            # Decrease quantity in InputCreditWarehouse
            input_credit_warehouse.decrease_quantity(cw.quantity, self.input_credit.weight * cw.quantity)

            # Create InputCreditWarehouseMovement for outflow
            InputCreditWarehouseMovement.objects.create(
                warehouse=cw.warehouse,
                input_credit_warehouse=input_credit_warehouse,
                input_credit=self.input_credit,
                movement_type='outflow',
                quantity=cw.quantity,
                weight=self.input_credit.weight * cw.quantity,
                record_date=self.issue_date or timezone.now().date(),
                outflow_source=self,
                amount=self.credit_amount, # This might need adjustment if credit amount is for the whole credit
                description=f"Outflow for Credit {self.credit_id} from {cw.warehouse.name}",
                notes=self.notes
            )
            
            # Mark the CreditWarehouse as fulfilled
            cw.is_fulfilled = True
            cw.save()

            # Update the overall input_credit quantity
            self.input_credit.quantity -= cw.quantity
            self.input_credit.save()

        except InputCreditWarehouse.DoesNotExist:
            raise ValueError(f"Input credit {self.input_credit.name} not found in warehouse {cw.warehouse.name}.")
        except ValueError as e:
            raise ValueError(f"Insufficient stock for input credit {self.input_credit.name} in warehouse {cw.warehouse.name}: {e}")


class CreditWarehouse(BaseModel):
    """
    Represents the relationship between a credit, an input credit, and the quantity.
    """
    credit = models.ForeignKey(Credit, on_delete=models.CASCADE)
    input_credit = models.ForeignKey(InputCredit, on_delete=models.CASCADE)
    warehouse = models.ForeignKey('warehouse.Warehouse', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    is_fulfilled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.quantity} of {self.input_credit.name} for credit {self.credit.id}"


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
