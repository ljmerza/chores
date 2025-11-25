from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('households', '0002_leaderboard_leaderboard_househo_e8ed20_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='household',
            name='ha_base_url',
            field=models.URLField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='household',
            name='ha_default_target',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
        migrations.AddField(
            model_name='household',
            name='ha_token',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='household',
            name='ha_verify_ssl',
            field=models.BooleanField(default=True),
        ),
    ]
