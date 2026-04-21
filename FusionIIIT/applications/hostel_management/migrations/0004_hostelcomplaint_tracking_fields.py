from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('hostel_management', '0003_hostelcomplaint_category_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='hostelcomplaint',
            name='status',
            field=models.CharField(choices=[('open', 'Open'), ('in_progress', 'In Progress'), ('resolved', 'Resolved')], default='open', max_length=20),
        ),
        migrations.AddField(
            model_name='hostelcomplaint',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='hostelcomplaint',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]