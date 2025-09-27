from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.http import FileResponse, HttpResponse
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from django.utils import timezone
from django.contrib.auth import get_user_model
import json
import re
import io
import os
import datetime
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from .models import LiveSession, LocationPoint
from .serializers import LiveSessionSerializer, PinpointSerializer, LocationPointSerializer
from .utils import reverse_geocode

User = get_user_model()

# ✅ UPDATED: Simplified start session (no PDF generation)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_session(request):
    """Start a new tracking session for employee"""
    if request.user.role != "employee":
        return Response({"detail": "Only employees may start tracking."}, status=403)
    
    # Check if user already has an active session
    existing_session = LiveSession.objects.filter(employee=request.user, is_active=True).first()
    if existing_session:
        return Response({
            "detail": "You already have an active session",
            "session": LiveSessionSerializer(existing_session).data
        }, status=400)
    
    session = LiveSession.objects.create(employee=request.user)
    return Response(LiveSessionSerializer(session).data, status=201)

# ✅ UPDATED: Simplified stop session (no PDF generation)
@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def stop_session(request, pk):
    """Stop active tracking session - PDF generation moved to admin side"""
    session = get_object_or_404(LiveSession, pk=pk, employee=request.user, is_active=True)
    session.is_active = False
    session.end_time = timezone.now()
    session.save()

    # Calculate session statistics
    location_points_count = session.location_points.count()
    pinpoints_count = session.pinpoints.count()
    duration = session.end_time - session.start_time

    return Response({
        "message": "Session stopped successfully",
        "session_id": session.id,
        "statistics": {
            "duration": str(duration),
            "location_points": location_points_count,
            "pinpoints": pinpoints_count
        }
    }, status=200)

# ✅ EXISTING: Keep pinpoint creation as is
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_pinpoint(request, session_id):
    """Add pinpoint to active session"""
    session = get_object_or_404(LiveSession, id=session_id, employee=request.user, is_active=True)
    data = request.data.copy()
    data["session"] = session.id
    
    # If address not provided, attempt reverse geocode
    lat = float(data.get("latitude", 0))
    lng = float(data.get("longitude", 0))
    if not data.get("address"):
        data["address"] = reverse_geocode(lat, lng)
    
    serializer = PinpointSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=201)

# ✅ EXISTING: Keep session snapshot as is
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_session_snapshot(request):
    """Get current user's active session with all data"""
    try:
        session = LiveSession.objects.filter(
            employee=request.user, 
            is_active=True
        ).prefetch_related('location_points', 'pinpoints').first()
        
        if not session:
            return Response({
                "session": None,
                "pinpoints": [],
                "path_points": []
            })
        
        # Get pinpoints
        pinpoints = PinpointSerializer(session.pinpoints.all(), many=True).data
        
        # Get path points for visualization (convert to coordinate pairs)
        path_points = [
            [float(point.latitude), float(point.longitude)]
            for point in session.location_points.all().order_by('timestamp')
        ]
        
        session_data = LiveSessionSerializer(session).data
        
        return Response({
            "session": session_data,
            "pinpoints": pinpoints,
            "path_points": path_points
        })
        
    except Exception as e:
        return Response({"error": f"Server error: {str(e)}"}, status=500)

# ✅ EXISTING: Keep other endpoints as they were
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def session_report(request, session_id):
    """Download report for specific session (legacy endpoint)"""
    session = get_object_or_404(LiveSession, id=session_id)
    # Allow admin or owner
    if request.user.role != "admin" and session.employee != request.user:
        return Response({"detail": "Forbidden"}, status=403)
    filename = f"{session.employee.username}_session_{session.id}.pdf"
    path = Path(settings.MEDIA_ROOT) / "reports" / filename
    if not path.exists():
        return Response({"detail": "Report not found"}, status=404)
    return FileResponse(open(path, "rb"), as_attachment=True, filename=filename)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sessions_today(request):
    """Get today's sessions for admin dashboard"""
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)

    today = timezone.localdate()
    sessions = LiveSession.objects.filter(start_time__date=today).select_related("employee")

    data = []
    for s in sessions:
        pinpoints = PinpointSerializer(s.pinpoints.all(), many=True).data
        last_position = None
        if pinpoints:
            last = pinpoints[-1]
            last_position = {"lat": last.get("latitude"), "lng": last.get("longitude")}
        data.append({
            "session_id": s.id,
            "employee_id": s.employee.id,
            "employee_name": s.employee.full_name or s.employee.username,
            "is_active": s.is_active,
            "last_position": last_position,
            "pinpoints": pinpoints,
        })

    return Response(data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def live_all_locations(request):
    """Get live locations of all active employees"""
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
    
    # Get all active sessions with current location data
    active_sessions = LiveSession.objects.filter(
        is_active=True, 
        current_latitude__isnull=False,
        current_longitude__isnull=False
    ).select_related('employee')
    
    live_data = {}
    for session in active_sessions:
        live_data[str(session.employee.id)] = {
            'latitude': session.current_latitude,
            'longitude': session.current_longitude,
            'timestamp': session.last_location_update.isoformat() if session.last_location_update else session.start_time.isoformat(),
            'employee': session.employee.username,
            'session_id': session.id
        }
    
    return Response(live_data)

# ✅ EXISTING: Keep location history as is
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def location_history(request, employee_id):
    """Get location history for specific employee"""
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
    
    # Support both single date and date range
    date = request.GET.get('date')
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    try:
        # Determine date range
        if start_date_str and end_date_str:
            # Date range mode
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        elif date:
            # Single date mode (backward compatibility)
            start_date = end_date = datetime.datetime.strptime(date, '%Y-%m-%d').date()
        else:
            # Default to last 5 days if no parameters provided
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=4)
        
        # Fetch sessions within the date range
        sessions = LiveSession.objects.filter(
            employee_id=employee_id,
            start_time__date__range=[start_date, end_date]
        ).prefetch_related('location_points', 'pinpoints').order_by('start_time')
        
        # Organize data by date for multi-day support
        daily_data = {}
        all_path_points = []
        all_pinpoints = []
        session_list = []
        
        for session in sessions:
            session_date = session.start_time.date().isoformat()
            
            # Initialize daily data structure
            if session_date not in daily_data:
                daily_data[session_date] = {
                    'sessions': [],
                    'path_points': [],
                    'pinpoints': []
                }
            
            # Session metadata
            session_data = {
                'id': session.id,
                'start_time': session.start_time,
                'end_time': session.end_time,
                'is_active': session.is_active
            }
            daily_data[session_date]['sessions'].append(session_data)
            session_list.append(session_data)
            
            # Process location points (continuous path tracking)
            for point in session.location_points.all():
                point_data = {
                    'latitude': float(point.latitude),
                    'longitude': float(point.longitude),
                    'timestamp': point.timestamp,
                    'date': session_date,
                    'type': 'path'
                }
                daily_data[session_date]['path_points'].append(point_data)
                all_path_points.append(point_data)
            
            # Process pinpoints (special marked locations)
            for pinpoint in session.pinpoints.all():
                pinpoint_data = {
                    'latitude': float(pinpoint.latitude),
                    'longitude': float(pinpoint.longitude),
                    'timestamp': pinpoint.timestamp,
                    'place': pinpoint.place or '',
                    'address': pinpoint.address or '',
                    'message': pinpoint.message or '',
                    'date': session_date,
                    'type': 'pinpoint'
                }
                daily_data[session_date]['pinpoints'].append(pinpoint_data)
                all_pinpoints.append(pinpoint_data)
        
        # Combine and sort all points chronologically
        all_points = sorted(
            all_path_points + all_pinpoints, 
            key=lambda x: x['timestamp']
        )
        
        # Enhanced response format
        response_data = {
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'total_days': (end_date - start_date).days + 1
            },
            'daily_data': daily_data,
            'sessions': session_list,
            'path_points': all_path_points,
            'pinpoints': all_pinpoints,
            'all_points': all_points,
            'total_sessions': len(session_list),
            'statistics': {
                'total_path_points': len(all_path_points),
                'total_pinpoints': len(all_pinpoints),
                'total_points': len(all_points)
            }
        }
        
        return Response(response_data)
        
    except ValueError as e:
        return Response({"error": f"Invalid date format: {str(e)}"}, status=400)
    except Exception as e:
        return Response({"error": f"Server error: {str(e)}"}, status=500)

# ✅ EXISTING: Keep location update endpoints as is
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_location(request):
    """Update employee's current location during active session and store as path point"""
    if request.user.role != "employee":
        return Response({"detail": "Only employees can update location"}, status=403)
    
    # Get active session
    session = LiveSession.objects.filter(employee=request.user, is_active=True).first()
    if not session:
        return Response({"detail": "No active session found"}, status=404)
    
    try:
        data = request.data
        lat = float(data.get("latitude", 0))
        lng = float(data.get("longitude", 0))
        
        if lat == 0 or lng == 0:
            return Response({"error": "Invalid coordinates"}, status=400)
        
        # Create location point for path tracking
        location_point = LocationPoint.objects.create(
            session=session,
            latitude=lat,
            longitude=lng,
        )
        
        return Response({
            "status": "Location updated",
            "point_id": location_point.id,
            "total_points": session.location_points.count()
        }, status=200)
        
    except (ValueError, TypeError) as e:
        return Response({"error": f"Invalid data: {str(e)}"}, status=400)
    except Exception as e:
        return Response({"error": f"Server error: {str(e)}"}, status=500)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_live_location(request):
    """Enhanced live location update that stores path points and updates session cache"""
    if request.user.role != "employee":
        return Response({"detail": "Only employees can update location"}, status=403)
    
    # Get employee's active session
    session = LiveSession.objects.filter(employee=request.user, is_active=True).first()
    if not session:
        return Response({"detail": "No active session found"}, status=404)
    
    try:
        data = request.data
        lat = float(data.get("latitude", 0))
        lng = float(data.get("longitude", 0))
        
        if not (lat and lng):
            return Response({"detail": "Invalid coordinates"}, status=400)
        
        # Store as path point for history tracking
        location_point = LocationPoint.objects.create(
            session=session,
            latitude=lat,
            longitude=lng,
        )
        
        # Update session cache for live tracking (admin dashboard)
        session.current_latitude = lat
        session.current_longitude = lng  
        session.last_location_update = timezone.now()
        session.save(update_fields=['current_latitude', 'current_longitude', 'last_location_update'])
        
        return Response({
            "status": "success", 
            "message": "Location updated successfully",
            "point_id": location_point.id,
            "total_points": session.location_points.count()
        }, status=200)
        
    except (ValueError, TypeError) as e:
        return Response({"error": f"Invalid data: {str(e)}"}, status=400)
    except Exception as e:
        return Response({"error": f"Server error: {str(e)}"}, status=500)

# ✅ ENHANCED: Admin-side PDF generation endpoints with text wrapping

def create_pdf_styles():
    """Create custom styles for PDF reports with text wrapping support"""
    styles = getSampleStyleSheet()
    
    # Custom styles
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Title'],
        fontSize=20,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    ))
    
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20,
        textColor=colors.darkblue,
        borderWidth=1,
        borderColor=colors.darkblue,
        borderPadding=5
    ))
    
    styles.add(ParagraphStyle(
        name='InfoText',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6,
        textColor=colors.black
    ))
    
    # ✅ NEW: Table cell styles for text wrapping
    styles.add(ParagraphStyle(
        name='TableCell',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=4,
        spaceBefore=2,
        textColor=colors.black,
        wordWrap='LTR',  # Enable word wrapping
        leftIndent=2,
        rightIndent=2
    ))
    
    styles.add(ParagraphStyle(
        name='TableCellBold',
        parent=styles['Normal'],
        fontSize=8,
        spaceAfter=4,
        spaceBefore=2,
        textColor=colors.black,
        fontName='Helvetica-Bold',
        wordWrap='LTR',
        leftIndent=2,
        rightIndent=2
    ))
    
    return styles

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_daily_pdf(request, employee_id):
    """Generate PDF report for employee's daily activities without session timing"""
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
    
    date_str = request.GET.get('date')
    if not date_str:
        return Response({'error': 'Date parameter required'}, status=400)
    
    try:
        # Parse date
        report_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        employee = get_object_or_404(User, id=employee_id)
        
        # Get sessions for the date
        sessions = LiveSession.objects.filter(
            employee=employee, 
            start_time__date=report_date
        ).prefetch_related('location_points', 'pinpoints').order_by('start_time')
        
        if not sessions.exists():
            return Response({'error': 'No sessions found for this date'}, status=404)
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        styles = create_pdf_styles()
        story = []
        
        # Title and header info
        story.append(Paragraph("Employee Location Report", styles["CustomTitle"]))
        story.append(Spacer(1, 20))
        
        # Employee and date info
        employee_name = employee.full_name or employee.username
        story.append(Paragraph(f"<b>Employee:</b> {employee_name}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Date:</b> {report_date.strftime('%B %d, %Y')}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Report Generated:</b> {datetime.datetime.now().strftime('%B %d, %Y at %H:%M')}", styles["InfoText"]))
        story.append(Spacer(1, 20))
        
        # Summary statistics
        total_sessions = sessions.count()
        total_pinpoints = sum(session.pinpoints.count() for session in sessions)
        total_path_points = sum(session.location_points.count() for session in sessions)
        
        story.append(Paragraph("Summary", styles["SectionHeader"]))
        story.append(Paragraph(f"<b>Total Sessions:</b> {total_sessions}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Total Pinpoints:</b> {total_pinpoints}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Total Path Points:</b> {total_path_points}", styles["InfoText"]))
        story.append(Spacer(1, 20))
        
        # Sessions details
        for i, session in enumerate(sessions, 1):
            story.append(Paragraph(f"Session {i} Details", styles["SectionHeader"]))
            
            # ✅ REMOVED: All session timing information
            # No more Start Time, End Time, Duration
            
            # ✅ Direct to pinpoints table
            pinpoints = session.pinpoints.all()
            if pinpoints.exists():
                story.append(Paragraph(f"Pinpoints ({pinpoints.count()})", styles["Heading3"]))
                
                # Create pinpoints table with Phone column
                data = []
                # Header row
                header_row = [
                    Paragraph("#", styles["TableCellBold"]),
                    Paragraph("Place", styles["TableCellBold"]),
                    Paragraph("Address", styles["TableCellBold"]),
                    Paragraph("Message", styles["TableCellBold"]),
                    Paragraph("Phone", styles["TableCellBold"])
                ]
                data.append(header_row)
                
                # Data rows
                for j, p in enumerate(pinpoints, 1):
                    row = [
                        Paragraph(str(j), styles["TableCell"]),
                        Paragraph(p.place or "N/A", styles["TableCell"]),
                        Paragraph(p.address or "N/A", styles["TableCell"]),
                        Paragraph(p.message or "N/A", styles["TableCell"]),
                        Paragraph(p.phone or "N/A", styles["TableCell"]),
                    ]
                    data.append(row)
                
                # Create table
                table = Table(
                    data, 
                    repeatRows=1, 
                    colWidths=[0.5*inch, 1.5*inch, 2.2*inch, 2.2*inch, 1.2*inch]
                )
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("TOPPADDING", (0, 1), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]))
                story.append(table)
            else:
                story.append(Paragraph("No pinpoints recorded for this session.", styles["InfoText"]))
            
            story.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Generate filename
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", employee_name)
        filename = f"{safe_name}_{report_date.strftime('%Y-%m-%d')}_DailyReport.pdf"
        
        # Return PDF as download
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except ValueError as e:
        return Response({'error': f'Invalid date format: {str(e)}'}, status=400)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=500)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_session_pdf(request, session_id):
    """Generate PDF report for specific session without session timing"""
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
    
    try:
        session = get_object_or_404(LiveSession, id=session_id)
        employee = session.employee
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        styles = create_pdf_styles()
        story = []
        
        # Title and header info
        story.append(Paragraph("Session Location Report", styles["CustomTitle"]))
        story.append(Spacer(1, 20))
        
        # ✅ SIMPLIFIED: Only basic session info
        employee_name = employee.full_name or employee.username
        story.append(Paragraph(f"<b>Employee:</b> {employee_name}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Session ID:</b> {session.id}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Date:</b> {session.start_time.strftime('%B %d, %Y')}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Report Generated:</b> {datetime.datetime.now().strftime('%B %d, %Y at %H:%M')}", styles["InfoText"]))
        story.append(Spacer(1, 20))
        
        # ✅ REMOVED: Start Time, End Time, Duration
        
        # Statistics
        pinpoints = session.pinpoints.all()
        path_points = session.location_points.all()
        
        story.append(Paragraph("Session Statistics", styles["SectionHeader"]))
        story.append(Paragraph(f"<b>Total Path Points:</b> {path_points.count()}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Total Pinpoints:</b> {pinpoints.count()}", styles["InfoText"]))
        story.append(Spacer(1, 20))
        
        # Pinpoints details
        if pinpoints.exists():
            story.append(Paragraph("Pinpoint Details", styles["SectionHeader"]))
            
            # Create detailed pinpoints table
            data = []
            # Header row
            header_row = [
                Paragraph("#", styles["TableCellBold"]),
                Paragraph("Place", styles["TableCellBold"]),
                Paragraph("Address", styles["TableCellBold"]),
                Paragraph("Phone", styles["TableCellBold"]),
                Paragraph("Message", styles["TableCellBold"])
            ]
            data.append(header_row)
            
            # Data rows (removed time column)
            for i, p in enumerate(pinpoints, 1):
                row = [
                    Paragraph(str(i), styles["TableCell"]),
                    Paragraph(p.place or "N/A", styles["TableCell"]),
                    Paragraph(p.address or "N/A", styles["TableCell"]),
                    Paragraph(p.phone or "N/A", styles["TableCell"]),
                    Paragraph(p.message or "N/A", styles["TableCell"]),
                ]
                data.append(row)
            
            # Create table with adjusted column widths (no time column)
            table = Table(
                data, 
                repeatRows=1, 
                colWidths=[0.4*inch, 1.4*inch, 2.2*inch, 1*inch, 2.4*inch]  # ✅ Redistributed widths
            )
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.darkblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.lightblue),
                ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("No pinpoints recorded for this session.", styles["InfoText"]))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Generate filename
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", employee_name)
        session_date = session.start_time.strftime('%Y-%m-%d')
        filename = f"{safe_name}_Session_{session.id}_{session_date}.pdf"
        
        # Return PDF as download
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=500)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_date_range_pdf(request, employee_id):
    """Generate comprehensive PDF report for date range without session timing"""
    if request.user.role != "admin":
        return Response({"detail": "Forbidden"}, status=403)
    
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    if not start_date_str or not end_date_str:
        return Response({'error': 'Both start_date and end_date parameters required'}, status=400)
    
    try:
        # Parse dates
        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        employee = get_object_or_404(User, id=employee_id)
        
        # Get sessions for the date range
        sessions = LiveSession.objects.filter(
            employee=employee, 
            start_time__date__range=[start_date, end_date]
        ).prefetch_related('location_points', 'pinpoints').order_by('start_time')
        
        if not sessions.exists():
            return Response({'error': 'No sessions found for this date range'}, status=404)
        
        # Create PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        styles = create_pdf_styles()
        story = []
        
        # Title and header info
        story.append(Paragraph("Employee Location Report - Date Range", styles["CustomTitle"]))
        story.append(Spacer(1, 20))
        
        # Employee and date info
        employee_name = employee.full_name or employee.username
        story.append(Paragraph(f"<b>Employee:</b> {employee_name}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Date Range:</b> {start_date.strftime('%B %d, %Y')} to {end_date.strftime('%B %d, %Y')}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Total Days:</b> {(end_date - start_date).days + 1}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Report Generated:</b> {datetime.datetime.now().strftime('%B %d, %Y at %H:%M')}", styles["InfoText"]))
        story.append(Spacer(1, 20))
        
        # Overall statistics
        total_sessions = sessions.count()
        total_pinpoints = sum(session.pinpoints.count() for session in sessions)
        total_path_points = sum(session.location_points.count() for session in sessions)
        
        story.append(Paragraph("Overall Summary", styles["SectionHeader"]))
        story.append(Paragraph(f"<b>Total Sessions:</b> {total_sessions}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Total Pinpoints:</b> {total_pinpoints}", styles["InfoText"]))
        story.append(Paragraph(f"<b>Total Path Points:</b> {total_path_points}", styles["InfoText"]))
        story.append(Spacer(1, 20))
        
        # Group sessions by date
        sessions_by_date = {}
        for session in sessions:
            date_key = session.start_time.date()
            if date_key not in sessions_by_date:
                sessions_by_date[date_key] = []
            sessions_by_date[date_key].append(session)
        
        # Daily breakdown
        for report_date, day_sessions in sorted(sessions_by_date.items()):
            story.append(Paragraph(f"Date: {report_date.strftime('%B %d, %Y')}", styles["SectionHeader"]))
            
            for i, session in enumerate(day_sessions, 1):
                story.append(Paragraph(f"Session {i}", styles["Heading3"]))
                
                # ✅ REMOVED: Session timing completely
                
                # Basic session info only
                story.append(Paragraph(f"<b>Pinpoints:</b> {session.pinpoints.count()}", styles["InfoText"]))
                story.append(Paragraph(f"<b>Path Points:</b> {session.location_points.count()}", styles["InfoText"]))
                
                # Show pinpoints with full text wrapping
                pinpoints = session.pinpoints.all()
                if pinpoints.exists():
                    story.append(Paragraph("Notable Locations:", styles["Normal"]))
                    for p in pinpoints:
                        # Create paragraph for each pinpoint with full text (no time)
                        location_info = f"<b>• {p.place or 'Location'}:</b>"
                        if p.message:
                            location_info += f" {p.message}"
                        if p.address:
                            location_info += f" <i>({p.address})</i>"
                        if p.phone:
                            location_info += f" <b>Ph:</b> {p.phone}"
                        # ✅ REMOVED: Time from location info
                        
                        story.append(Paragraph(location_info, styles["InfoText"]))
                
                story.append(Spacer(1, 15))
            
            story.append(Spacer(1, 20))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        
        # Generate filename
        safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", employee_name)
        filename = f"{safe_name}_{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}_Report.pdf"
        
        # Return PDF as download
        response = HttpResponse(buffer.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
        
    except ValueError as e:
        return Response({'error': f'Invalid date format: {str(e)}'}, status=400)
    except Exception as e:
        return Response({'error': f'Server error: {str(e)}'}, status=500)
