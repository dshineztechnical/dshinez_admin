from django.db import migrations

def create_admin(apps, schema_editor):
    User = apps.get_model("attendenceapp", "User")
    if not User.objects.filter(username="admin").exists():
        User.objects.create_user(
            username="admin",
            password="admin!2123",
            role="admin",
            full_name="System Admin",
            designation="Administrator"
        )

class Migration(migrations.Migration):
    dependencies = [
        ("attendenceapp", "0001_initial"),
    ]
    operations = [
        migrations.RunPython(create_admin),
    ]