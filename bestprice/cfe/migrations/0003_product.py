# Generated by Django 4.1.7 on 2023-06-25 23:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cfe', '0002_alter_item_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.JSONField()),
            ],
        ),
    ]