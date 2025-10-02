from django.urls import path
from django.conf import settings
from django.http import FileResponse, Http404 
import os  
from .views import (LoginView, RegisterEmployeeView, MeView, ProfilePhotoUploadView, employee_list, offline_employees, 
    manage_employee, online_employees,LaserScreedSubmissionListCreateView,LaserScreedSubmissionDetailView, submit_form, submissions_list, delete_submission, 
    submit_contact, contact_submissions_list, delete_contact_submission)
from . import views_tracking



def download_pdf(request):
    pdf_path = os.path.join(settings.MEDIA_ROOT, 'bookquotes', 'dshinez.pdf')
    if os.path.exists(pdf_path):
        return FileResponse(
            open(pdf_path, 'rb'), 
            as_attachment=True, 
            filename='dshinez-quote.pdf',
            content_type='application/pdf'
        )
    else:
        raise Http404("PDF not found")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register-employee/", RegisterEmployeeView.as_view(), name="register-employee"),
    path("me/", MeView.as_view(), name="me"),
    path("me/photo/", ProfilePhotoUploadView.as_view(), name="me-photo"),
    path("employees/", employee_list, name="employee-list"),
    path("offline-employees/", offline_employees, name="offline-employees"),
    path("employees/<int:pk>/", manage_employee, name="manage-employee"),
    path("online-employees/", online_employees, name="online-employees"),

    # Location tracking endpoints
    path("location/start/", views_tracking.start_session, name="start-session"),
    path("location/stop/<int:pk>/", views_tracking.stop_session, name="stop-session"),
    path("location/pinpoint/<int:session_id>/", views_tracking.add_pinpoint, name="add-pinpoint"),
    path("location/my-session/", views_tracking.my_session_snapshot, name="my-session"),
    path("location/report/<int:session_id>/", views_tracking.session_report, name="session-report"),
    path("admin/sessions-today/", views_tracking.sessions_today, name="sessions-today"),

    path("location/live-all/", views_tracking.live_all_locations, name="live-all-locations"),
    path("location/history/<int:employee_id>/", views_tracking.location_history, name="location-history"),
    path("location/update/", views_tracking.update_location, name="update-location"),
    path("location/live-update/", views_tracking.update_live_location, name="update-live-location"),

    # ✅ NEW: Admin PDF report endpoints
    path("reports/daily-pdf/<int:employee_id>/", views_tracking.generate_daily_pdf, name="daily-pdf"),
    path("reports/session-pdf/<int:session_id>/", views_tracking.generate_session_pdf, name="session-pdf"),
    path("reports/date-range-pdf/<int:employee_id>/", views_tracking.generate_date_range_pdf, name="date-range-pdf"),


    path('laser-screed-submissions/', LaserScreedSubmissionListCreateView.as_view(), name='laser_screed_submissions'),
    path('laser-screed-submissions/<int:pk>/',LaserScreedSubmissionDetailView.as_view(), name='laser_screed_submission_detail'),


    path("submit/", submit_form, name="submit_form"),
    path("submit-contact/", submit_contact, name="submit_contact"),
    
    # Admin endpoints for viewing submissions
    path("quote/submissions/", submissions_list, name="submissions"),
    path("contact/submissions/", contact_submissions_list, name="contact_submissions"),
    path("quote/submissions/<int:pk>/", delete_submission, name="delete_submission"), 
    path("contact/submissions/<int:pk>/", delete_contact_submission, name="delete_contact_submission"),
    
    
    path("download-pdf/", download_pdf, name="download_pdf"),
]