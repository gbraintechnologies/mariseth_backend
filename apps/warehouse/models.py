from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models

from apps.credit.models import InputCredit, InputCreditPurchase, Credit
from apps.customers.models import Customer
from apps.shared.models import BaseModel

User = get_user_model()


class Warehouse(BaseModel):
    """Model representing storage facilities"""
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='warehouses')
    warehouse_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    region = models.ForeignKey('shared.Region', on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey('shared.District', on_delete=models.SET_NULL, null=True, blank=True)
    capacity = models.CharField(max_length=50)
    managers = models.ManyToManyField(User, blank=True, related_name='managed_warehouses')

    def __str__(self):
        return f"{self.name} ({self.warehouse_id})"


class InputCreditWarehouse(BaseModel):
    """
    Represents the stock of an input credit in a warehouse.
    """
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    input_credit = models.ForeignKey(InputCredit, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    weight = models.FloatField()
    quantity = models.PositiveIntegerField()

    class Meta:
        unique_together = ('input_credit', 'warehouse')

    def __str__(self):
        return f"{self.quantity} of {self.input_credit.name} in {self.warehouse.name}"

    def increase_quantity(self, quantity: int, weight: float):
        """Handle inflow of input credits"""
        self.quantity += quantity
        self.weight += weight
        self.save()

    def decrease_quantity(self, quantity: int, weight: float):
        """Handle outflow of input credits"""
        if self.quantity >= quantity:
            self.quantity -= quantity
            self.weight -= float(weight)
            self.save()
        else:
            raise ValueError("Insufficient stock for this operation")


class WarehouseProduct(BaseModel):
    """Model tracking product inventory in warehouses"""
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='warehouse_product')
    product = models.ForeignKey('farm.Product', on_delete=models.CASCADE,
                                related_name='warehouse_stocks')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE,
                                  related_name='product_stocks')
    weight = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        unique_together = ('product', 'warehouse')

    def __str__(self):
        return f"{self.product.name} in {self.warehouse.name}: {self.quantity} bags"

    def add_stock(self, quantity: int):
        """Handle inflow of products"""
        self.quantity = (self.quantity or Decimal(0)) + Decimal(quantity)
        product_weight_decimal = Decimal(self.product.weight) if self.product.weight is not None else Decimal(0)
        self.weight = (self.weight or Decimal(0)) + (Decimal(quantity) * product_weight_decimal)
        self.save()

    def remove_stock(self, quantity: int):
        """Handle outflow of products"""
        print(f"Trying to remove {quantity} from WarehouseProduct {self.product.name} with quantity {self.quantity}")

        if self.quantity >= quantity:
            print("Sufficient stock. Proceeding...")
            self.quantity -= Decimal(quantity)
            self.weight = (self.weight or Decimal(0)) - (Decimal(quantity) * Decimal(self.product.weight))
            self.save()
            print("Stock updated successfully.")
        else:
            print(f"Insufficient stock for this operation: have {self.quantity}, need {quantity}")
            raise ValueError("Insufficient stock for this operation")


class WarehouseProductMovement(BaseModel):
    MOVEMENT_CHOICES = [
        ('inflow', 'Inflow'),
        ('outflow', 'Outflow'),
    ]
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='warehouse_movements')
    warehouse_product = models.ForeignKey(WarehouseProduct, on_delete=models.CASCADE,
                                          related_name='warehouse_movements')
    product = models.ForeignKey('farm.Product', on_delete=models.CASCADE, related_name='warehouse_movements')
    movement_type = models.CharField(max_length=7, choices=MOVEMENT_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True,
                                   null=True)  # total quantity for the order
    weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)  # total weight for the order
    record_date = models.DateField(null=True, blank=True)
    inflow_order = models.ForeignKey('inflow.InflowOrder', on_delete=models.CASCADE,
                                     null=True, blank=True, related_name='movements'
                                     )
    outflow_order = models.ForeignKey('outflow.OutflowOrder', on_delete=models.CASCADE,
                                      null=True, blank=True, related_name='movements')
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    buyer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, related_name='purchases', blank=True)
    aggregator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='aggregations', blank=True)
    procurement_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                            related_name='procurement_activities')
    description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-record_date']

    # def __str__(self):
    #     return f"{self.movement_type} of {self.quantity} {self.warehouse_product.warehouse}"


class InputCreditWarehouseMovement(BaseModel):
    MOVEMENT_CHOICES = [
        ('inflow', 'Inflow'),
        ('outflow', 'Outflow'),
    ]
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='input_credit_warehouse_movements')
    input_credit_warehouse = models.ForeignKey(InputCreditWarehouse, on_delete=models.CASCADE,
                                               related_name='input_credit_warehouse_movements')
    input_credit = models.ForeignKey(InputCredit, on_delete=models.CASCADE,
                                     related_name='input_credit_warehouse_movements')
    movement_type = models.CharField(max_length=7, choices=MOVEMENT_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    record_date = models.DateField(null=True, blank=True)
    inflow_source = models.ForeignKey('credit.InputCreditPurchase', on_delete=models.CASCADE,
                                      null=True, blank=True, related_name='input_credit_movements')
    outflow_source = models.ForeignKey('credit.Credit', on_delete=models.CASCADE,
                                       null=True, blank=True, related_name='input_credit_movements')
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-record_date']