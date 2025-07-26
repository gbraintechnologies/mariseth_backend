import base64
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.customers.models import Customer
from apps.customers.serializers import CustomerSerializer
from apps.farm.models import Product
from apps.farm.serializers.products import ShortProductSerializer
from apps.outflow.models import OutflowOrder, OutflowOrderDeliveryInformation, OutflowOrderDeliveryInformationImage, \
    OutflowOrderDeliveryInformationWarehouse, OutflowOrderHistory, OutflowOrderPayments, OutflowOrderWarehouse, \
    OutflowOrderWarehouseImages, OutflowOrderWarehouseProduct, OutflowRecipientComplaint, OutflowRecipientComplaintImage
from apps.outflow.utils import generate_outflow_order_id, generate_outflow_waybill_id, generate_serial_number
from apps.shared.utils.helpers import base64_to_image
from apps.warehouse.models import Warehouse, WarehouseProduct
from apps.warehouse.serializers import ShortWarehouseSerializer

User = get_user_model()


class OutflowOrderProductSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(source='product', queryset=Product.objects.filter(is_active=True))
    warehouse_id = serializers.PrimaryKeyRelatedField(source='warehouse',
                                                      queryset=Warehouse.objects.filter(is_active=True))
    price_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = OutflowOrderWarehouseProduct
        fields = ('warehouse_id', 'product_id', 'expected_quantity', 'price_per_unit')

    def validate(self, data):
        warehouse = data['warehouse']
        product = data['product']
        quantity = data['expected_quantity']

        try:
            wp = WarehouseProduct.objects.get(
                product=product,
                warehouse=warehouse,
                is_active=True
            )
            if wp.quantity < quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock for product {product.name} in warehouse "
                    f"{warehouse.name}. Available: {wp.quantity}"
                )
        except WarehouseProduct.DoesNotExist:
            raise serializers.ValidationError(
                f"Product {product} not available in warehouse {warehouse}"
            )

        data['available_quantity'] = wp.quantity
        data['cost'] = quantity * data['price_per_unit']
        return data


class OutflowOrderSerializer(serializers.ModelSerializer):
    products = OutflowOrderProductSerializer(many=True, source='warehouse_products', allow_null=True)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.filter(is_active=True))
    procurement_officer = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True),
                                                             allow_null=True)

    class Meta:
        model = OutflowOrder
        fields = (
            'customer', 'procurement_officer', 'destination',
            'expected_delivery_date', 'products', 'total_quantity',
            'total_cost', 'extra_comments', 'additional_costs',
            'additional_cost_amount',
        )
        read_only_fields = ('total_quantity', 'total_cost', 'order_id')

    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        products_data = validated_data.pop('warehouse_products')
        validated_data["organization"] = request.organization
        validated_data["created_by"] = request.user
        validated_data["order_id"] = generate_outflow_order_id(request.organization.id)
        order = OutflowOrder.objects.create(**validated_data)
        order.waybill_id = generate_outflow_waybill_id(order.pk)
        order.save(update_fields=['waybill_id'])
        addtional_cost = validated_data.get('additional_cost_amount', 0)

        total_quantity = 0
        total_cost = 0

        # Group products by warehouse
        for product_data in products_data:
            warehouse = product_data['warehouse']
            outflow_order_warehouse, _ = OutflowOrderWarehouse.objects.get_or_create(
                outflow_order=order,
                warehouse=warehouse
            )
            product = product_data['product']
            serial_number = generate_serial_number(
                warehouse.warehouse_id,
                order.id,
                product.name,
                product_data['expected_quantity']
            )

            OutflowOrderWarehouseProduct.objects.create(
                serial_number=serial_number,
                outflow_order_warehouse=outflow_order_warehouse,
                product=product,
                expected_quantity=product_data['expected_quantity'],
                price_per_unit=product_data['price_per_unit'],
                cost=product_data['cost']
            )

            total_quantity += product_data['expected_quantity']
            total_cost += product_data['cost']
        total_cost += addtional_cost
        order.total_quantity = total_quantity
        order.total_cost = total_cost
        order.amount_due = total_cost
        order.save()
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        # Update scalar fields
        for attr in ('destination', 'expected_delivery_date', 'extra_comments'):
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        instance.save()

        #  Sync products if provided
        incoming = validated_data.get('warehouse_products')
        if incoming is not None:
            # Track which warehouse-product combinations to keep (using original warehouse IDs)
            keep = set()
            warehouse_mapping = {}  # Maps warehouse IDs to OutflowOrderWarehouse instances

            for item in incoming:
                wh_id = item['warehouse'].id  # Original warehouse ID
                prod_id = item['product'].id
                qty = int(item['expected_quantity'])
                price = Decimal(str(item['price_per_unit']))
                cost = qty * price

                # Get or create warehouse group using original warehouse ID
                if wh_id not in warehouse_mapping:
                    warehouse_mapping[wh_id] = OutflowOrderWarehouse.objects.get_or_create(
                        outflow_order=instance,
                        warehouse_id=wh_id
                    )[0]

                wh_group = warehouse_mapping[wh_id]

                # Get or create product line
                line, created = OutflowOrderWarehouseProduct.objects.update_or_create(
                    outflow_order_warehouse=wh_group,
                    product_id=prod_id,
                    defaults={
                        'expected_quantity': qty,
                        'price_per_unit': price,
                        'cost': cost,
                        'serial_number': generate_serial_number(
                            wh_group.warehouse.warehouse_id,
                            instance.id,
                            item['product'].name,
                            qty
                        )
                    }
                )

                # Clamp available to actual stock
                stock = WarehouseProduct.objects.get(
                    warehouse_id=wh_id,
                    product_id=prod_id,
                    is_active=True
                ).quantity
                line.available_quantity = min(qty, stock)
                line.save()

                keep.add((wh_id, prod_id))  # Track by original warehouse ID and product ID

            # Delete only products not present in update data
            for existing_wh in instance.warehouses.all():
                for existing_product in existing_wh.products.all():
                    key = (existing_wh.warehouse.id, existing_product.product.id)
                    if key not in keep:
                        existing_product.delete()

        # 3) Remove empty warehouse groups
        instance.warehouses.filter(products__isnull=True).delete()

        # 4) Recalculate totals (same as before)
        total_qty = 0
        total_cost = Decimal('0.00')
        for wh_group in instance.warehouses.all():
            for line in wh_group.products.filter(is_active=True):
                total_qty += line.expected_quantity
                total_cost += line.cost

        instance.total_quantity = total_qty
        instance.total_cost = total_cost + instance.additional_cost_amount
        instance.amount_due = total_cost
        instance.save()

        return instance


class OutflowWarehouseProductSerializer(serializers.ModelSerializer):
    product = ShortProductSerializer(read_only=True)
    price_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2)
    cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    warehouse = ShortWarehouseSerializer(source='outflow_order_warehouse.warehouse', read_only=True)

    class Meta:
        model = OutflowOrderWarehouseProduct
        fields = (
            'id', 'serial_number', 'available_quantity', 'expected_quantity', 'price_per_unit',
            'cost', 'status', 'product', 'warehouse', 'reason', 'comments'
        )


class OutflowWarehouseImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutflowOrderWarehouseImages
        fields = ('id', 'image', 'date_created')


class OutflowOrderWarehouseSerializer(serializers.ModelSerializer):
    products = OutflowWarehouseProductSerializer(
        many=True,
        source='products.all'
    )
    total_quantity = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    warehouse = ShortWarehouseSerializer()
    images = OutflowWarehouseImageSerializer(many=True, source='images.all', read_only=True)

    class Meta:
        model = OutflowOrderWarehouse
        fields = (
            'id', 'warehouse', 'status', 'total_quantity',
            'total_cost', 'products', 'images'
        )

    def get_total_quantity(self, obj):
        return sum(p.expected_quantity for p in obj.products.filter(is_active=True))

    def get_total_cost(self, obj):
        return sum(float(p.cost) for p in obj.products.filter(is_active=True))


class OutflowOrderDeliveryInfoResponseSerializer(serializers.ModelSerializer):
    warehouses = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    class Meta:
        model = OutflowOrderDeliveryInformation
        fields = [
            'id', 'driver_name', 'driver_phone_number', 'driver_license_number',
            'truck_license_number', 'destination', 'company', 'escort_required',
            'escort_details', 'warehouses', 'images'
        ]

    def get_warehouses(self, obj):
        warehouse_links = obj.warehouses.filter(is_active=True)
        return ShortWarehouseSerializer(
            [link.warehouse for link in warehouse_links],
            many=True
        ).data

    def get_images(self, obj):
        return OutflowOrderDeliveryInfoImageSerializer(
            obj.images.all(),
            many=True,
            context=self.context
        ).data


class OutflowOrderDeliveryInformationSerializer(serializers.ModelSerializer):
    warehouse_ids = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.filter(is_active=True)),
        write_only=True
    )
    images = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True
    )
    escort_details = serializers.CharField(required=False, allow_blank=True)
    destination = serializers.CharField(required=True)
    company = serializers.CharField(required=True)

    class Meta:
        model = OutflowOrderDeliveryInformation
        fields = [
            'driver_name', 'driver_phone_number', 'driver_license_number',
            'truck_license_number', 'destination', 'company', 'escort_required',
            'escort_details', 'warehouse_ids', 'images'
        ]

    def validate(self, attrs):
        order = self.context.get('order')
        if order.status != 'availability_check':
            raise serializers.ValidationError("Delivery info can not be created for this order")

        if attrs.get('escort_required') and not attrs.get('escort_details'):
            raise serializers.ValidationError("Escort details are required when escort is required")

        warehouse_ids = attrs.get('warehouse_ids', [])
        for warehouse in warehouse_ids:
            exists = OutflowOrderWarehouse.objects.filter(outflow_order=order, warehouse=warehouse).exists()
            if not exists:
                raise serializers.ValidationError(
                    f"Warehouse {warehouse.name} does not belong to this order"
                )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        # Extract related data
        warehouse_ids = validated_data.pop('warehouse_ids', [])
        images = validated_data.pop('images', [])

        # Create delivery info
        delivery_info = OutflowOrderDeliveryInformation.objects.create(
            outflow_order=self.context['order'],
            **validated_data
        )

        # Create warehouse assignments
        for warehouse in warehouse_ids:
            OutflowOrderDeliveryInformationWarehouse.objects.create(
                outflow_order_delivery_information=delivery_info,
                warehouse=warehouse
            )

        # Create images
        for image in images:
            OutflowOrderDeliveryInformationImage.objects.create(
                outflow_order_delivery_information=delivery_info,
                image=base64_to_image(image)
            )

        return delivery_info


class OutflowOrderDeliveryInfoImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutflowOrderDeliveryInformationImage
        fields = ['id', 'image']


class OutflowOrderPaymentRequestSerializer(serializers.ModelSerializer):
    paid_to = serializers.CharField(required=True)
    mobile_money_number = serializers.CharField(required=False, allow_blank=True)
    bank_name = serializers.CharField(required=False, allow_blank=True)
    bank_account_number = serializers.CharField(required=False, allow_blank=True)
    bank_account_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = OutflowOrderPayments
        fields = (
            'id', 'amount_paid', 'amount_due',
            'payment_type', 'payment_method', 'notes',
            'paid_to', 'payment_date', 'mobile_money_number',
            'bank_name', 'bank_account_number', 'bank_account_name'
        )

    def validate(self, attrs):
        order = self.context['order']
        amount_paid = attrs.get('amount_paid', 0)
        if order.amount_due == 0 or order.amount_paid == order.amount_due:
            raise serializers.ValidationError("Order is already fully paid")
        if amount_paid > order.amount_due:
            raise serializers.ValidationError("Amount being paid is more than the outstanding amount")
        if amount_paid <= 0:
            raise serializers.ValidationError("Amount must be greater than zero")
        if amount_paid < order.amount_due and attrs.get('payment_type') == 'full':
            raise serializers.ValidationError("Amount being paid is less than the outstanding amount it cannot be full")

        method = attrs.get('payment_method')

        if method == 'mobile_money' and not attrs.get('mobile_money_number'):
            raise serializers.ValidationError({'mobile_money_number': 'Mobile Money number is required.'})

        if method == 'bank_transfer':
            missing_fields = []
            if not attrs.get('bank_name'):
                missing_fields.append('bank_name')
            if not attrs.get('bank_account_number'):
                missing_fields.append('bank_account_number')
            if not attrs.get('bank_account_name'):
                missing_fields.append('bank_account_name')

            if missing_fields:
                raise serializers.ValidationError({
                    field: 'This field is required for bank transfers.'
                    for field in missing_fields
                })

        return attrs

    def create(self, validated_data):
        order = self.context['order']
        request = self.context['request']
        validated_data['outflow_order'] = order
        validated_data['created_by'] = request.user
        payment = OutflowOrderPayments.objects.create(**validated_data)

        order.amount_paid += payment.amount_paid
        order.amount_due -= payment.amount_paid
        payment.amount_due = order.amount_due
        payment.save()
        if order.amount_paid >= order.total_cost:
            order.status = 'full_payment'
        elif order.amount_paid > 0:
            order.status = 'partial_payment'

        order.save()
        return payment


class OutflowOrderHistorySerializer(serializers.ModelSerializer):
    created_by = ShortUserSerializer()

    class Meta:
        model = OutflowOrderHistory
        fields = (
            'id', 'field_name', 'old_value', 'new_value',
            'date_created', 'created_by',
        )


class OutflowRecipientComplaintSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())
    expected_quantity = serializers.IntegerField(min_value=0)
    problematic_quantity = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=255)
    comments = serializers.CharField(allow_blank=True, required=False)

    def validate(self, data):
        if data['problematic_quantity'] > data['expected_quantity']:
            raise serializers.ValidationError("Problematic quantity cannot exceed expected quantity.")
        return data


class MarkCompleteSerializer(serializers.Serializer):
    complaints = OutflowRecipientComplaintSerializer(many=True, required=False)
    images = serializers.ListField(
        child=serializers.CharField(), required=False, allow_empty=True
    )

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop('order', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def validate_images(self, image_list):
        validated = []
        for idx, image_str in enumerate(image_list):
            try:
                format, imgstr = image_str.split(';base64,')
                ext = format.split('/')[-1]
                decoded_file = base64.b64decode(imgstr)
                file_name = f"complaint_{self.order.id}_{idx}.{ext}"
                validated.append(ContentFile(decoded_file, name=file_name))
            except Exception:
                raise serializers.ValidationError(f"Invalid base64 image at index {idx}")
        return validated

    def save(self):
        complaints = self.validated_data.get('complaints', [])
        images = self.validated_data.get('images', [])

        # Save complaints
        for complaint in complaints:
            OutflowRecipientComplaint.objects.create(
                outflow_order=self.order,
                product=complaint['product'],
                expected_quantity=complaint['expected_quantity'],
                problematic_quantity=complaint['problematic_quantity'],
                reason=complaint['reason'],
                comments=complaint.get('comments', '')
            )

        # Save images
        for image_file in images:
            OutflowRecipientComplaintImage.objects.create(
                outflow_order=self.order,
                image=image_file
            )

        # Mark order complete
        old_status = self.order.status
        self.order.status = 'complete'
        self.order.save()
        self.order.log_status_change(old_status, 'complete', self.user)

        return self.order


class GetOutflowRecipientComplaintSerializer(serializers.ModelSerializer):
    product = ShortProductSerializer()

    class Meta:
        model = OutflowRecipientComplaint
        fields = (
            'id', 'product', 'expected_quantity',
            'problematic_quantity', 'reason', 'comments'
        )


class FullOutflowOrderSerializer(serializers.ModelSerializer):
    warehouses = OutflowOrderWarehouseSerializer(
        many=True,
        source='warehouses.all'
    )
    customer = CustomerSerializer()
    procurement_officer = ShortUserSerializer()
    total_quantity = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    delivery_information = OutflowOrderDeliveryInfoResponseSerializer(many=True)
    products = serializers.SerializerMethodField()
    payments = OutflowOrderPaymentRequestSerializer(many=True)
    logs = OutflowOrderHistorySerializer(source='history.all', many=True)
    recipient_complaints = serializers.SerializerMethodField()

    class Meta:
        model = OutflowOrder
        fields = (
            'id', 'order_id', 'customer', 'procurement_officer',
            'destination', 'expected_delivery_date', 'status',
            'additional_costs', 'additional_cost_amount', 'total_quantity',
            'total_cost', 'amount_paid', 'amount_due', 'products', 'warehouses',
            'delivery_information', 'payments', 'logs', 'recipient_complaints',
            'waybill_id'
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Sort warehouses by ID for consistent output
        representation['warehouses'] = sorted(
            representation['warehouses'],
            key=lambda x: x['id']
        )
        return representation

    def get_products(self, obj):
        all_products = OutflowOrderWarehouseProduct.objects.filter(
            outflow_order_warehouse__outflow_order=obj,
            is_active=True
        )
        return OutflowWarehouseProductSerializer(all_products, many=True).data

    def get_recipient_complaints(self, obj):
        request = self.context.get('request')

        # Complaints
        complaints_qs = obj.customer_complaints.all()
        complaints_data = GetOutflowRecipientComplaintSerializer(
            complaints_qs, many=True, context={'request': request}
        ).data

        # Images: just return the accessible URL
        image_qs = obj.complaint_images.all()
        image_urls = []
        for image in image_qs:
            if image.image:
                if request:
                    image_urls.append(request.build_absolute_uri(image.image.url))
                else:
                    image_urls.append(image.image.url)

        return {
            'complaints': complaints_data,
            'images': image_urls
        }


class ListOutflowOrderSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer()
    total_quantity = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    products = serializers.SerializerMethodField()

    class Meta:
        model = OutflowOrder
        fields = (
            'id', 'order_id', 'customer', 'procurement_officer',
            'destination', 'expected_delivery_date', 'status', 'products',
            'total_quantity', 'total_cost',
        )

    def get_products(self, obj):
        all_products = OutflowOrderWarehouseProduct.objects.filter(
            outflow_order_warehouse__outflow_order=obj,
            is_active=True
        )
        return OutflowWarehouseProductSerializer(all_products, many=True).data


class ShortOutflowOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutflowOrder
        fields = ('id', 'order_id', 'total_cost', 'status')


