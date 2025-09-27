from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("employee", "Employee"),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="employee")
    full_name = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=120, blank=True)
    location = models.CharField(max_length=120, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    profile_photo = models.ImageField(upload_to="profiles/", null=True, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"


class LiveSession(models.Model):
    employee = models.ForeignKey(User, on_delete=models.CASCADE, related_name="live_sessions")
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Live location tracking fields
    current_latitude = models.FloatField(null=True, blank=True)
    current_longitude = models.FloatField(null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        status = "Active" if self.is_active else "Ended"
        return f"{self.employee.username} - {status}"


class Pinpoint(models.Model):
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name="pinpoints", null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    place = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    message = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Pinpoint {self.place or ''} ({self.latitude}, {self.longitude})"


class LocationPoint(models.Model):
    """Stores continuous location data for path tracking"""
    session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name="location_points")
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"Location at {self.timestamp} - {self.session.employee.username}"





# lasescreed

class LaserScreedSubmission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('contacted', 'Contacted'),
        ('completed', 'Completed'),
    ]
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    company = models.CharField(max_length=200, blank=True, null=True)
    whatsapp = models.CharField(max_length=20)
    services = models.JSONField()  
    need_troweling = models.CharField(max_length=10, blank=True, null=True)
    troweling_color = models.CharField(max_length=20, blank=True, null=True)
    sqft_range = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.email} ({self.status})"
    



# Dshinez Digital quote and contactform submission

class Submission(models.Model):
    """Quote submissions from Dshinez Digital website"""
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField(max_length=254, null=True, blank=True)  # Made optional like LaserScreed
    location = models.CharField(max_length=200)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']  # Keep consistent with your other models
        verbose_name = "Quote Submission"
        verbose_name_plural = "Quote Submissions"

    def __str__(self):
        return f"{self.name} - {self.phone}"

class ContactSubmission(models.Model):
    """Contact form submissions from Dshinez Digital website"""
    name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()
    message = models.TextField(blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']  # Keep consistent with your other models
        verbose_name = "Contact Submission"
        verbose_name_plural = "Contact Submissions"

    def __str__(self):
        return f"{self.name} - {self.email}"
