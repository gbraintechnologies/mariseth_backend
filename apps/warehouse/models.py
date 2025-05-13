from django.db import models
from decimal import Decimal
# Create your models here.
# TODO: MAKE SURE TO UPDATE THE PRODUCT QUANTITY IN THE WAREHOUSE AND THE OVERALL PRODUCT TABLE

from django.db import models
from django.contrib.auth import get_user_model

from apps.shared.models import BaseModel

User = get_user_model()


class Warehouse(BaseModel):
    """Model representing storage facilities"""
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='warehouses')
    warehouse_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    region = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    capacity = models.CharField(max_length=50)
    manager = models.ForeignKey(User, on_delete=models.SET_NULL,
                                null=True, blank=True,
                                related_name='managed_warehouses')

    def __str__(self):
        return f"{self.name} ({self.warehouse_id})"


class WarehouseProduct(BaseModel):
    """Model tracking product inventory in warehouses"""
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='warehouse_product')
    product = models.ForeignKey('farm.Product', on_delete=models.CASCADE,
                                related_name='warehouse_stocks')
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE,
                                  related_name='product_stocks')
    weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        unique_together = ('product', 'warehouse')

    def __str__(self):
        return f"{self.product.name} in {self.warehouse.name}: {self.quantity} bags"

    def add_stock(self, quantity: int, weight: int):
        """Handle inflow of products"""
        self.quantity -= Decimal(quantity)
        self.weight -= Decimal(weight)
        self.save()

    def remove_stock(self, quantity: int, weight: int):
        """Handle outflow of products"""
        if self.quantity >= quantity and self.weight >= weight:
            self.quantity += Decimal(quantity)
            self.weight += Decimal(weight)
            self.save()
        else:
            raise ValueError("Insufficient stock for this operation")


class WarehouseProductMovement(BaseModel):
    MOVEMENT_CHOICES = [
        ('INFLOW', 'Inflow'),
        ('OUTFLOW', 'Outflow'),
    ]
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE, related_name='warehouse_movements')
    warehouse_product = models.ForeignKey(WarehouseProduct, on_delete=models.CASCADE,
                                          related_name='warehouse_movements')
    product = models.ForeignKey('farm.Product', on_delete=models.CASCADE, related_name='warehouse_movements')
    movement_type = models.CharField(max_length=7, choices=MOVEMENT_CHOICES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)

    # Future-proof foreign keys (commented out for now)
    # inflow_order = models.ForeignKey('Inflow', on_delete=models.CASCADE,
    #                                 null=True, blank=True,
    #                                 related_name='movements')
    # outflow_order = models.ForeignKey('Outflow', on_delete=models.CASCADE,
    #                                  null=True, blank=True,
    #                                  related_name='movements')
    amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    buyer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='purchases', blank=True)
    aggregator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='aggregations', blank=True)
    procurement_officer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,
                                            related_name='procurement_activities')
    description = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.movement_type} of {self.quantity} {self.warehouse_product.warehouse}"