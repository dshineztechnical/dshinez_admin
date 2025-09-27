from rest_framework import serializers
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, LiveSession, Pinpoint, LocationPoint
from .models import LaserScreedSubmission
from .models import Submission, ContactSubmission






class LocationPointSerializer(serializers.ModelSerializer):
    class Meta:
        model = LocationPoint
        fields = "__all__"
        read_only_fields = ("id", "timestamp",)


class PinpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pinpoint
        fields = "__all__"
        read_only_fields = ("id", "timestamp",)


class LiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveSession
        fields = ["id", "employee", "start_time", "end_time", "is_active"]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(username=data.get("username"), password=data.get("password"))
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        refresh = RefreshToken.for_user(user)
        return {
            "token": str(refresh.access_token),
            "refresh": str(refresh),
            "role": user.role,
        }


class RegisterEmployeeSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    class Meta:
        model = User
        fields = ["username", "password", "full_name", "designation", "location", "date_of_birth"]

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            role="employee",
            full_name=validated_data.get("full_name",""),
            designation=validated_data.get("designation",""),
            location=validated_data.get("location",""),
            date_of_birth=validated_data.get("date_of_birth", None),
        )


class UserProfileSerializer(serializers.ModelSerializer):
    profile_photo = serializers.ImageField(use_url=True)
    class Meta:
        model = User
        fields = ["id", "username", "role", "full_name", "designation", "location", "date_of_birth", "profile_photo"]


class ProfilePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["profile_photo"]




#laserscreed


class LaserScreedSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LaserScreedSubmission
        fields = [
            'id', 
            'name', 
            'email', 
            'company', 
            'whatsapp', 
            'services', 
            'need_troweling', 
            'troweling_color', 
            'sqft_range', 
            'status', 
            'created_at', 
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Convert camelCase from frontend to snake_case for database
        if 'needTroweling' in validated_data:
            validated_data['need_troweling'] = validated_data.pop('needTroweling')
        if 'trowelingColor' in validated_data:
            validated_data['troweling_color'] = validated_data.pop('trowelingColor')
        if 'sqftRange' in validated_data:
            validated_data['sqft_range'] = validated_data.pop('sqftRange')
        
        return super().create(validated_data)
    


    #dshinez digital

class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = "__all__"
        read_only_fields = ['id', 'submitted_at']

class ContactSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactSubmission
        fields = "__all__"
        read_only_fields = ['id', 'submitted_at']