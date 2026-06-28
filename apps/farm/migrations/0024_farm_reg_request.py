from django.db import migrations
from django.db import models

from django.conf import settings


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ('farm','0023_alter_farm_size')
    ]
    operations = [
        migrations.CreateModel(
            name='FarmerRegistrationRequest',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('phone_number', models.CharField(blank=True, max_length=100, null=True, unique=True)),
                ('id_type', models.CharField(blank=True, max_length=50, null=True)),
                ('id_number', models.CharField(blank=True, max_length=50, null=True)),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('gender', models.CharField(choices=[('M', 'Male'), ('F', 'Female')], max_length=1)),
                ('other_names', models.CharField(blank=True, max_length=100, null=True)),
                ('request_channel', models.CharField(choices=[('USSD', 'USSD')], default='USSD', max_length=100)),
                ('country', models.CharField(blank=True, max_length=100, null=True)),
                ('address', models.CharField(blank=True, max_length=255, null=True)),
                ('date_of_birth', models.DateField(blank=True, null=True)),
                ('email', models.EmailField(blank=True, max_length=254, null=True, unique=True)),
                ('status',
                 models.CharField(choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')],
                                  default='Pending', max_length=50)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_modified', models.DateTimeField(auto_now=True)),
                ('approved_at', models.DateTimeField(blank=True, null=True)),

                ('approved_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=models.deletion.SET_NULL,
                    to='accounts.user'
                )),

                ('region', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=models.deletion.SET_NULL,
                    to='shared.region'
                )),

                ('district', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=models.deletion.SET_NULL,
                    to='shared.district'
                )),
            ],
        ),
    ]