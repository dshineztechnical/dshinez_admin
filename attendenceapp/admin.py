from django.contrib import admin
from .models import LaserScreedSubmission
from .models import Submission, ContactSubmission

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone", "email", "location", "submitted_at")
    list_filter = ("submitted_at", "location")
    search_fields = ("name", "phone", "email", "location")
    readonly_fields = ("submitted_at",)
    ordering = ("-submitted_at",)

@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "phone_number", "email", "submitted_at")
    list_filter = ("submitted_at",)
    search_fields = ("name", "phone_number", "email", "message")
    readonly_fields = ("submitted_at",)
    ordering = ("-submitted_at",)


@admin.register(LaserScreedSubmission)
class LaserScreedSubmissionAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'company', 'whatsapp', 'get_services', 'status', 'created_at']
    list_filter = ['status', 'services', 'created_at']
    search_fields = ['name', 'email', 'company', 'whatsapp']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_services(self, obj):
        return ', '.join(obj.services) if obj.services else 'None'
    get_services.short_description = 'Services'