from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hostel_management', '0002_hostelroomchangerequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='hostelcomplaint',
            name='category',
            field=models.CharField(default='General', max_length=50),
        ),
        migrations.AddField(
            model_name='hostelcomplaint',
            name='image_upload',
            field=models.FileField(blank=True, null=True, upload_to='hostel_management/complaints/'),
        ),
    ]