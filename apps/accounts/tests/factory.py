from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from factory import PostGenerationMethodCall, Sequence, SubFactory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice, FuzzyInteger
from faker import Faker
import factory

from apps.accounts.models import AppGroup, AppPermission, GroupRank

fake = Faker()
User = get_user_model()


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    first_name = fake.first_name()
    last_name = fake.last_name()
    username = Sequence(lambda n: f"{fake.first_name().lower()}_{n}")
    email = Sequence(lambda n: f"user{n}@example.com")
    phone_number = Sequence(lambda n: f'10000000000{n}')
    avatar = factory.django.FileField(filename='test_image.jpg')
    date_verified = timezone.now()
    gender = FuzzyChoice(['m', 'f'])
    password = PostGenerationMethodCall('set_password', 'password')

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default _create to use set_password."""
        kwargs['password'] = make_password('password')
        return super()._create(model_class, *args, **kwargs)


class ContentTypeFactory(DjangoModelFactory):
    class Meta:
        model = ContentType

    app_label = Sequence(lambda n: f'app_label_{n}')
    model = Sequence(lambda n: f'model_{n}')


class AppPermissionFactory(DjangoModelFactory):
    class Meta:
        model = AppPermission

    name = Sequence(lambda n: f'permission_{n}')
    codename = Sequence(lambda n: f'permission_code_{n}')
    content_type = SubFactory(ContentTypeFactory)


class AppGroupFactory(DjangoModelFactory):
    class Meta:
        model = AppGroup

    name = Sequence(lambda n: f'group_{n}')

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        group = super()._create(model_class, *args, **kwargs)
        GroupRankFactory(group=group)
        return group


class GroupRankFactory(DjangoModelFactory):
    class Meta:
        model = GroupRank

    group = SubFactory(AppGroupFactory)
    rank = FuzzyInteger(1, 100)
    is_default = False
