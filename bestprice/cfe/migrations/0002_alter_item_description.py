# Generated by Django 4.1.7 on 2023-06-25 22:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cfe', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='description',
            field=models.CharField(max_length=120),
        ),
    ]
