from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_username_login'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='homeassistant_target',
            field=models.CharField(
                max_length=150,
                null=True,
                blank=True,
                help_text='Home Assistant notify target (e.g., notify.mobile_app_bobs_iphone)',
            ),
        ),
    ]
