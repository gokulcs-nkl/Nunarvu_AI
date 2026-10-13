from django.db import migrations


def create_default_webcam(apps, schema_editor):
    Camera = apps.get_model('monitoring', 'Camera')
    if not Camera.objects.exists():
        Camera.objects.create(name='Laptop webcam', source_type='webcam', source='0')


class Migration(migrations.Migration):

    dependencies = [
        ('monitoring', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_webcam, migrations.RunPython.noop),
    ]
