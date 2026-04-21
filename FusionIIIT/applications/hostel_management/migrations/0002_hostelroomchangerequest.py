from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hostel_management', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='HostelRoomChangeRequest',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('student_name', models.CharField(max_length=100)),
                ('roll_num', models.CharField(max_length=20)),
                ('current_room', models.CharField(max_length=20)),
                ('preferred_room', models.CharField(max_length=20)),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]