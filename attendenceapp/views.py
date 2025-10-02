from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import LiveSession
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import User
from .serializers import (
    LoginSerializer, RegisterEmployeeSerializer, UserProfileSerializer, ProfilePhotoSerializer
)
from .models import Submission, ContactSubmission
from .serializers import SubmissionSerializer, ContactSubmissionSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny

#laserscreed
from rest_framework import generics, status
from .models import LaserScreedSubmission
from .serializers import LaserScreedSubmissionSerializer


# Login
class LoginView(APIView):
    def post(self, request):
        ser = LoginSerializer(data=request.data)
        if ser.is_valid():
            return Response(ser.validated_data, status=200)
        return Response(ser.errors, status=400)

# Register (admin only)
class RegisterEmployeeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "admin":
            return Response({"error": "Only admins can register employees"}, status=403)
        ser = RegisterEmployeeSerializer(data=request.data)
        if ser.is_valid():
            ser.save()
            return Response({"message": "Employee registered successfully"}, status=201)
        return Response(ser.errors, status=400)

# Me
class MeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        return Response(UserProfileSerializer(request.user, context={"request": request}).data)

# Upload profile photo
class ProfilePhotoUploadView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def patch(self, request):
        ser = ProfilePhotoSerializer(instance=request.user, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response({"message": "Photo updated", "profile_photo": ser.data.get("profile_photo")})
        return Response(ser.errors, status=400)

# Employee list (admin)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def employee_list(request):
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
    employees = User.objects.filter(role="employee")
    ser = UserProfileSerializer(employees, many=True, context={"request": request})
    return Response(ser.data)

# Offline employees (admin) - last_login threshold
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def offline_employees(request):
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
    
    # Get employees who DON'T have active tracking sessions
    active_employee_ids = LiveSession.objects.filter(is_active=True).values_list('employee_id', flat=True)
    offline = User.objects.filter(role="employee").exclude(id__in=active_employee_ids)
    
    ser = UserProfileSerializer(offline, many=True, context={"request": request})
    return Response(ser.data)



# Update or Delete Employee (admin only)
@api_view(["PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def manage_employee(request, pk):
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)

    employee = get_object_or_404(User, pk=pk, role="employee")

    if request.method == "PATCH":
        data = request.data.copy()
        # Allow updating password
        if "password" in data and data["password"]:
            employee.set_password(data["password"])
            employee.save()
            data.pop("password")
        ser = UserProfileSerializer(employee, data=data, partial=True, context={"request": request})
        if ser.is_valid():
            ser.save()
            return Response({"message": "Employee updated", "employee": ser.data})
        return Response(ser.errors, status=400)

    elif request.method == "DELETE":
        employee.delete()
        return Response({"message": "Employee removed successfully"}, status=204)
    


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def online_employees(request):
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
    
    # Get employees who have active tracking sessions
    active_sessions = LiveSession.objects.filter(is_active=True).select_related('employee')
    online_employees_data = []
    
    for session in active_sessions:
        # Get latest pinpoint for last activity time
        latest_pinpoint = session.pinpoints.order_by('-timestamp').first()
        last_activity = latest_pinpoint.timestamp if latest_pinpoint else session.start_time
        
        employee_data = UserProfileSerializer(session.employee, context={"request": request}).data
        employee_data['last_activity'] = last_activity
        employee_data['session_start'] = session.start_time
        online_employees_data.append(employee_data)
    
    return Response(online_employees_data)





#laserscreeding

class LaserScreedSubmissionListCreateView(generics.ListCreateAPIView):
    queryset = LaserScreedSubmission.objects.all()
    serializer_class = LaserScreedSubmissionSerializer
    
    def get_permissions(self):
        if self.request.method == 'POST':
            # Allow public access for form submissions
            return [AllowAny()]
        # Require authentication for viewing submissions (admin only)
        return [IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        # Handle the camelCase to snake_case conversion
        data = request.data.copy()
        
        if 'needTroweling' in data:
            data['need_troweling'] = data.pop('needTroweling')
        if 'trowelingColor' in data:
            data['troweling_color'] = data.pop('trowelingColor')
        if 'sqftRange' in data:
            data['sqft_range'] = data.pop('sqftRange')
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response({
            'message': 'Form submitted successfully!',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

class LaserScreedSubmissionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LaserScreedSubmission.objects.all()
    serializer_class = LaserScreedSubmissionSerializer
    permission_classes = [IsAuthenticated]
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response({
            'message': 'Status updated successfully!',
            'data': serializer.data
        })
    

    #dshinezDigital


@api_view(["POST"])
@permission_classes([AllowAny])
def submit_form(request):
    serializer = SubmissionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        
        # ✅ Use direct download endpoint instead of media URL
        scheme = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        pdf_url = f"{scheme}://{host}/api/download-pdf/"
        
        return Response({
            'message': 'Quote request submitted successfully!',
            'data': serializer.data,
            'pdf_url': pdf_url 
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




# ✅ Quote submissions list (restricted to admins)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def submissions_list(request):
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
    
    submissions = Submission.objects.all().order_by("-submitted_at")
    serializer = SubmissionSerializer(submissions, many=True)
    return Response(serializer.data)

# ✅ Delete quote submission
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_submission(request, pk):
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
        
    submission = get_object_or_404(Submission, pk=pk)
    submission.delete()
    return Response(
        {"message": "Quote submission deleted successfully"}, 
        status=status.HTTP_204_NO_CONTENT
    )

# ✅ Contact form submission (open to public)
@api_view(["POST"])
@permission_classes([AllowAny])
def submit_contact(request):
    serializer = ContactSubmissionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Contact form submitted successfully!',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ✅ Contact submissions list (restricted to admins)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def contact_submissions_list(request):
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
        
    contacts = ContactSubmission.objects.all().order_by("-submitted_at")
    serializer = ContactSubmissionSerializer(contacts, many=True)
    return Response(serializer.data)

# ✅ Delete contact submission
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_contact_submission(request, pk):
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
        
    contact = get_object_or_404(ContactSubmission, pk=pk)
    contact.delete()
    return Response(
        {"message": "Contact submission deleted successfully"},
        status=status.HTTP_204_NO_CONTENT,
    )