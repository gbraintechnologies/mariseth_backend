from django.db import transaction
from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.farm.models import Farm, Farmer, FarmerDocument
from apps.farm.serializers.farm import FullFarmSerializer
from apps.farm.utils import generate_farmer_id
from apps.shared.models import District, Region
from apps.shared.serializers.regions import DistrictSerializer, ShortRegionSerializer


class FarmerDocumentSerializer(serializers.ModelSerializer):
    document = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = FarmerDocument
        fields = ('id', 'title', 'description', 'document')


class ShortFarmerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farmer
        fields = ('id', 'first_name', 'last_name', 'type')
        read_only_fields = ('id',)


class FarmerSerializer(serializers.ModelSerializer):
    farm = serializers.PrimaryKeyRelatedField(
        queryset=Farm.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    lead_farmer = serializers.PrimaryKeyRelatedField(
        queryset=Farmer.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    district = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(),
        required=False,
        allow_null=True,
    )
    region = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(),
        required=False,
        allow_null=True,
    )

    documents = FarmerDocumentSerializer(many=True, required=False)

    class Meta:
        model = Farmer
        fields = (
            'id', 'type', 'first_name', 'last_name', 'other_names', 'gender',
            'date_of_birth', 'id_number', 'phone_number', 'email', 'address',
            'village', 'region', 'district', 'country', 'farm', 'lead_farmer',
            'leadership_experience', 'support_assistance', 'id_type', 'documents'
        )
        read_only_fields = ('id',)

    def validate(self, data):
        if data.get('type') == 'smallholder':
            # if not data.get('lead_farmer'):
            #     raise serializers.ValidationError(
            #         {'lead_farmer': 'Smallholder farmers must have a lead farmer assigned'}
            #     )

            if data.get('lead_farmer') and data['lead_farmer'].type != 'lead':
                raise serializers.ValidationError(
                    {'lead_farmer': 'Assigned lead farmer must be of type "lead"'}
                )
        if data.get('district') and not data.get('region'):
            raise serializers.ValidationError(
                {'region': 'Region must be provided when district is specified.'}
            )
        return data

    def create(self, validated_data):
        request = self.context['request']
        documents_data = validated_data.pop('documents', [])

        with transaction.atomic():
            # Lock the Farmer table for this organization to prevent race conditions
            _ = list(Farmer.objects.filter(organization=request.organization).select_for_update())

            # Safely generate the ID
            farmer_id = generate_farmer_id(request.organization.id)

            validated_data['created_by'] = request.user
            validated_data['organization'] = request.organization
            validated_data['farmer_id'] = farmer_id
            
            farmer = Farmer.objects.create(**validated_data)

            for document_data in documents_data:
                FarmerDocument.objects.create(farmer=farmer, **document_data)
            
            return farmer

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = self.context['request'].user
        instance.save()
        return instance


class FullFarmerSerializer(serializers.ModelSerializer):
    created_by = ShortUserSerializer()
    farm = FullFarmSerializer(allow_null=True, required=False)
    lead_farmer = serializers.SerializerMethodField()
    region = ShortRegionSerializer()
    district = DistrictSerializer()
    number_of_smallholders = serializers.SerializerMethodField()
    documents = serializers.SerializerMethodField()


    class Meta:
        model = Farmer
        fields = (
            'id', 'type', 'farmer_id', 'first_name', 'last_name', 'other_names', 'gender',
            'date_of_birth', 'id_number', 'phone_number', 'email', 'address',
            'village', 'region', 'district', 'country', 'farm', 'lead_farmer',
            'leadership_experience', 'support_assistance', 'created_by',
            'date_created', 'farm', 'id_type', 'number_of_smallholders', 'documents'
        )
        read_only_fields = ('id', 'created_by', 'date_created')

    def get_lead_farmer(self, obj):
        if obj.lead_farmer:
            return ShortFarmerSerializer(obj.lead_farmer).data
        return None

    def get_number_of_smallholders(self, obj):
        if obj.type == 'lead':
            return Farmer.objects.filter(lead_farmer=obj).count()
        return None

    def get_documents(self, obj):
        return FarmerDocumentSerializer(obj.documents.filter(is_active=True), many=True).data


class FarmerExportSerializer(serializers.ModelSerializer):
    type = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    lead_farmer = serializers.SerializerMethodField()
    farm = serializers.SerializerMethodField()
    date_created = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True, allow_null=True)
    date_of_birth = serializers.DateField(format="%Y-%m-%d", allow_null=True)
    region = serializers.StringRelatedField(source='region.name')
    district = serializers.StringRelatedField(source='district.name')

    class Meta:
        model = Farmer
        fields = (
            'farmer_id', 'type', 'first_name', 'last_name', 'other_names', 'gender',
            'date_of_birth', 'id_number', 'phone_number', 'email', 'address',
            'village', 'region', 'district', 'country', 'farm', 'lead_farmer',
            'leadership_experience', 'support_assistance',
            'created_by', 'date_created', 'id_type',
        )

    def get_type(self, obj):
        return dict(Farmer.FARMER_TYPE_CHOICES).get(obj.type, "")

    def get_gender(self, obj):
        return dict(Farmer.GENDER_CHOICES).get(obj.gender, "")

    def get_created_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else ""

    def get_lead_farmer(self, obj):
        if obj.lead_farmer:
            return f"{obj.lead_farmer.first_name} {obj.lead_farmer.last_name}"
        return ""

    def get_farm(self, obj):
        if obj.farm:
            return obj.farm.name
        return ""


class ReassignSmallholderFarmerSerializer(serializers.Serializer):
    lead_farmer_id = serializers.IntegerField(required=True)
    smallholder_farmer_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        required=True
    )

    def validate_lead_farmer_id(self, value):
        try:
            lead_farmer = Farmer.objects.get(id=value, type='lead', is_active=True)
        except Farmer.DoesNotExist:
            raise serializers.ValidationError("Lead farmer with this ID does not exist or is not a lead farmer.")
        return lead_farmer

    def validate_smallholder_farmer_ids(self, values):
        smallholder_farmers = Farmer.objects.filter(id__in=values, type='smallholder', is_active=True)
        if len(smallholder_farmers) != len(values):
            raise serializers.ValidationError("One or more smallholder farmer IDs are invalid or do not exist.")
        return smallholder_farmers

    def save(self):
        lead_farmer = self.validated_data['lead_farmer_id']
        smallholder_farmers = self.validated_data['smallholder_farmer_ids']

        updated_count = 0
        with transaction.atomic():
            for smallholder in smallholder_farmers:
                if smallholder.lead_farmer != lead_farmer:
                    smallholder.lead_farmer = lead_farmer
                    smallholder.save(update_fields=['lead_farmer'])
                    updated_count += 1
        return {
            'message': f'{updated_count} Smallholder farmers re-assigned successfully.',
        }
