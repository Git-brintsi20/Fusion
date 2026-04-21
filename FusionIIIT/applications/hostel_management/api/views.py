from django.core.serializers import serialize
from django.http import HttpResponseBadRequest
from ..models import HostelLeave
from django.http import JsonResponse, HttpResponse, FileResponse
from django.db import IntegrityError
from django.db import models
from rest_framework.exceptions import NotFound
from django.shortcuts import redirect
from django.template import loader
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.shortcuts import render, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
from django.urls import reverse
from ..models import StudentDetails
from rest_framework.exceptions import APIException



from django.shortcuts import render, redirect

from ..models import HostelLeave
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes



from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
# from .models import HostelStudentAttendance
from django.http import JsonResponse
from applications.globals.models import (Designation, ExtraInfo,
                                         HoldsDesignation, DepartmentInfo)
from applications.academic_information.models import Student
from applications.academic_information.models import *
from django.db.models import Q
import datetime
from datetime import time, datetime, date
from time import mktime, time, localtime
from ..models import *
import xlrd
from ..forms import GuestRoomBookingForm, HostelNoticeBoardForm
import re
from django.http import HttpResponse
from django.template.loader import get_template
from django.views.generic import View
from django.db.models import Q
from django.contrib import messages
from ..services import (
    add_to_room,
    get_caretaker_hall,
    remove_from_room,
    render_to_pdf,
    save_worker_report_sheet,
)
from ..selectors import (
    get_all_halls,
    get_available_rooms_for_halls,
    get_guest_rooms_map,
    get_hall_staff_assignments_map,
    get_halls_attendance_map,
    get_halls_notices_map,
    get_halls_staff_schedules_map,
    get_halls_students_map,
    get_pending_guest_room_requests_map,
)
from ..services import (
    build_student_details_for_hall,
    get_staff_assigned_hall,
    is_user_faculty,
    is_user_staff,
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
import json

from decimal import Decimal, InvalidOperation
from rest_framework.permissions import AllowAny

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from Fusion.settings.common import LOGIN_URL
from django.shortcuts import get_object_or_404, redirect, render
from django.db import transaction
from ..forms import HallForm
from notification.views import hostel_notifications
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from django.conf import settings
from django.utils.text import get_valid_filename
import os
import uuid
import mimetypes
from django.db.utils import OperationalError, ProgrammingError
import calendar
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

def is_superuser(user):
    return user.is_authenticated and user.is_superuser


def _room_change_status_normalize(value):
    if value is None:
        return None
    return str(value).strip().lower() or None


def _room_change_roll_numbers_for_hall(hall):
    hall_id = str(getattr(hall, "hall_id", "") or "").strip().lower()
    match = re.search(r"(\d+)", hall_id)
    hall_no = int(match.group(1)) if match else None

    roll_nums = []
    if hall_id:
        roll_nums = list(
            StudentDetails.objects.filter(hall_id__iexact=hall_id).values_list("id", flat=True)
        )

    if hall_no is not None:
        roll_nums += list(
            StudentDetails.objects.filter(hall_no=str(hall_no)).values_list("id", flat=True)
        )
        roll_nums += list(
            Student.objects.filter(hall_no=hall_no).values_list("id__user__username", flat=True)
        )

    # De-duplicate while preserving order
    seen = set()
    unique_rolls = []
    for roll in roll_nums:
        if roll in seen:
            continue
        seen.add(roll)
        unique_rolls.append(roll)

    return unique_rolls


def _serialize_room_change_request(request_obj):
    return {
        "id": request_obj.id,
        "student_name": request_obj.student_name,
        "roll_num": request_obj.roll_num,
        "current_room": request_obj.current_room,
        "preferred_room": request_obj.preferred_room,
        "reason": request_obj.reason,
        "status": request_obj.status,
        "created_at": request_obj.created_at.isoformat() if request_obj.created_at else None,
    }


def _is_caretaker_or_warden(user):
    try:
        staff_id = user.extrainfo.id
    except Exception:
        staff_id = None

    if staff_id is None:
        return False

    if HallCaretaker.objects.filter(staff_id=staff_id).exists():
        return True

    if HallWarden.objects.filter(faculty_id=staff_id).exists():
        return True

    return False


def _is_warden(user):
    try:
        staff_id = user.extrainfo.id
    except Exception:
        staff_id = None

    if staff_id is None:
        return False

    return HallWarden.objects.filter(faculty_id=staff_id).exists()


def _clean_required_str(payload, key):
    value = payload.get(key, None)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _complaint_api_status_from_db(value):
    value_norm = str(value).strip().lower() if value is not None else ""
    if value_norm == "open":
        return "OPEN"
    if value_norm == "assigned":
        return "ASSIGNED"
    if value_norm == "in_progress":
        return "IN_PROGRESS"
    if value_norm == "resolved":
        return "RESOLVED"
    return _normalize_status(value) or "OPEN"


def _month_to_number(month_value):
    if month_value is None:
        return None

    value = str(month_value).strip()
    if not value:
        return None

    if value.isdigit():
        month_num = int(value)
        return month_num if 1 <= month_num <= 12 else None

    value_norm = value.lower()
    months = {
        "january": 1,
        "february": 2,
        "march": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }

    if value_norm in months:
        return months[value_norm]

    # Allow short forms like "Jan", "Feb".
    for name, num in months.items():
        if name.startswith(value_norm):
            return num

    return None


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_attendance_api(request):
    """Return a PDF attendance report for a month.

    Frontend usage (student):
      GET /hostelmanagement/view_attendance/?year=YYYY&month=MonthName

    Optional (staff/superuser):
      Provide student_id to view a particular student.
    """

    year_raw = request.query_params.get("year")
    month_raw = request.query_params.get("month")
    student_id_raw = (
        request.query_params.get("student_id")
        or request.query_params.get("roll_num")
        or request.query_params.get("student")
    )

    if not year_raw or not month_raw:
        return Response(
            {"detail": "year and month are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        year = int(str(year_raw).strip())
    except (TypeError, ValueError):
        return Response(
            {"detail": "Invalid year"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    month_num = _month_to_number(month_raw)
    if month_num is None:
        raise NotFound("Attendance record not found")

    # Resolve student
    assigned_hall = None
    if student_id_raw:
        if not is_superuser(request.user):
            assigned_hall = get_staff_assigned_hall(request.user)
            if not assigned_hall:
                return Response(
                    {"detail": "Not authorized to view other students"},
                    status=status.HTTP_403_FORBIDDEN,
                )

        student = get_object_or_404(Student, id=str(student_id_raw).strip())

        if not is_superuser(request.user) and assigned_hall:
            hall_match = re.search(r"(\d+)", str(getattr(assigned_hall, "hall_id", "")))
            assigned_hall_no = int(hall_match.group(1)) if hall_match else None
            if assigned_hall_no is None or int(student.hall_no or 0) != assigned_hall_no:
                return Response(
                    {"detail": "Not authorized to view this student's attendance"},
                    status=status.HTTP_403_FORBIDDEN,
                )
    else:
        student = Student.objects.filter(id=request.user.username).first()
        if student is None:
            student = Student.objects.filter(id__user=request.user).first()
        if student is None:
            raise NotFound("Student record not found")

    last_day = calendar.monthrange(year, month_num)[1]
    start_date = date(year, month_num, 1)
    end_date = date(year, month_num, last_day)

    records = (
        HostelStudentAttendence.objects.filter(student_id=student, date__range=(start_date, end_date))
        .select_related("hall")
        .order_by("date")
    )

    if not records.exists():
        raise NotFound("Attendance record not found")

    total_marked = records.count()
    present_count = records.filter(present=True).count()
    absent_count = total_marked - present_count

    styles = getSampleStyleSheet()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=30,
        rightMargin=30,
        topMargin=30,
        bottomMargin=30,
        title="Attendance Report",
    )

    student_label = getattr(student, "id", None)
    student_id = getattr(student_label, "id", None) if student_label else None
    month_name = calendar.month_name[month_num]

    elements = [
        Paragraph("Hostel Attendance Report", styles["Title"]),
        Spacer(1, 10),
        Paragraph(f"Student: <b>{student_id or request.user.username}</b>", styles["Normal"]),
        Paragraph(f"Month: <b>{month_name} {year}</b>", styles["Normal"]),
        Spacer(1, 10),
        Paragraph(
            f"Marked days: <b>{total_marked}</b> &nbsp;&nbsp; Present: <b>{present_count}</b> &nbsp;&nbsp; Absent: <b>{absent_count}</b>",
            styles["Normal"],
        ),
        Spacer(1, 14),
    ]

    table_data = [["Date", "Present", "Hall"]]
    for rec in records:
        table_data.append(
            [
                rec.date.isoformat(),
                "Yes" if rec.present else "No",
                getattr(rec.hall, "hall_id", "-"),
            ]
        )

    table = Table(table_data, colWidths=[120, 80, 80])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
            ]
        )
    )

    elements.append(table)
    doc.build(elements)

    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"Attendance_{student_id or request.user.username}_{year}_{month_num:02d}.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    return response


def _complaint_db_status_from_api(value):
    api_norm = _normalize_status(value)
    if api_norm == "OPEN":
        return "open"
    if api_norm == "ASSIGNED":
        return "assigned"
    if api_norm == "IN_PROGRESS":
        return "in_progress"
    if api_norm == "RESOLVED":
        return "resolved"
    return None


@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def complaints_collection_api(request):
    """Complaint Management REST API (no auth for now).

    - GET: list complaints (latest first)
    - POST: create complaint with validations
    """

    if request.method == "GET":
        try:
            complaints = HostelComplaint.objects.all().order_by("-id")
            data = []
            for c in complaints:
                image_url = None
                try:
                    if getattr(c, "image_upload", None):
                        image_url = c.image_upload.url
                except Exception:
                    image_url = None

                data.append(
                    {
                        "id": c.id,
                        "hall_name": c.hall_name,
                        "student_name": c.student_name,
                        "roll_number": c.roll_number,
                        "category": getattr(c, "category", "General"),
                        "description": c.description,
                        "contact_number": c.contact_number,
                        "image_upload": image_url,
                        "status": _complaint_api_status_from_db(getattr(c, "status", None)),
                        "created_at": getattr(c, "created_at", None).isoformat() if getattr(c, "created_at", None) else None,
                        "updated_at": getattr(c, "updated_at", None).isoformat() if getattr(c, "updated_at", None) else None,
                    }
                )
            return Response(data, status=status.HTTP_200_OK)
        except (ProgrammingError, OperationalError) as e:
            return Response(
                {
                    "message": "Complaints table is not available. Did you run migrations?",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    payload = request.data or {}

    hall_name = _clean_required_str(payload, "hall_name")
    student_name = _clean_required_str(payload, "student_name")
    roll_number = _clean_required_str(payload, "roll_number")
    category = _clean_required_str(payload, "category") or "General"
    description = _clean_required_str(payload, "description")
    contact_number = _clean_required_str(payload, "contact_number")

    image_upload = None
    try:
        image_upload = request.FILES.get("image_upload")
    except Exception:
        image_upload = None

    missing = []
    if not hall_name:
        missing.append("hall_name")
    if not student_name:
        missing.append("student_name")
    if not roll_number:
        missing.append("roll_number")
    if not description:
        missing.append("description")
    if not contact_number:
        missing.append("contact_number")

    if missing:
        return Response(
            {"message": f"Missing required fields: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if len(description) < 10:
        return Response(
            {"message": "description must be at least 10 characters"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not contact_number.isdigit():
        return Response(
            {"message": "contact_number must be numeric"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        complaint = HostelComplaint.objects.create(
            hall_name=hall_name,
            student_name=student_name,
            roll_number=roll_number,
            category=category,
            description=description,
            contact_number=contact_number,
            image_upload=image_upload,
            status="open",
        )
    except (ProgrammingError, OperationalError) as e:
        return Response(
            {
                "message": "Complaints table is not available. Did you run migrations?",
                "detail": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "message": "Complaint submitted successfully",
            "id": complaint.id,
            "status": _complaint_api_status_from_db(getattr(complaint, "status", None)),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET", "DELETE"])
@authentication_classes([])
@permission_classes([AllowAny])
def complaint_detail_api(request, id):
    """Complaint Management REST API (no auth for now).

    - GET: retrieve single complaint by id
    - DELETE: delete complaint by id
    """

    try:
        complaint_id = int(id)
    except (TypeError, ValueError):
        return Response({"message": "Invalid id"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        complaint = HostelComplaint.objects.filter(id=complaint_id).first()
    except (ProgrammingError, OperationalError) as e:
        return Response(
            {
                "message": "Complaints table is not available. Did you run migrations?",
                "detail": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    if not complaint:
        return Response({"message": "Complaint not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        image_url = None
        try:
            if getattr(complaint, "image_upload", None):
                image_url = complaint.image_upload.url
        except Exception:
            image_url = None

        data = {
            "id": complaint.id,
            "hall_name": complaint.hall_name,
            "student_name": complaint.student_name,
            "roll_number": complaint.roll_number,
            "category": getattr(complaint, "category", "General"),
            "description": complaint.description,
            "contact_number": complaint.contact_number,
            "image_upload": image_url,
            "status": _complaint_api_status_from_db(getattr(complaint, "status", None)),
            "created_at": getattr(complaint, "created_at", None).isoformat() if getattr(complaint, "created_at", None) else None,
            "updated_at": getattr(complaint, "updated_at", None).isoformat() if getattr(complaint, "updated_at", None) else None,
        }
        return Response(data, status=status.HTTP_200_OK)

    complaint.delete()
    return Response({"message": "Complaint removed successfully"}, status=status.HTTP_200_OK)


_COMPLAINT_ALLOWED_STATUSES = {"OPEN", "ASSIGNED", "IN_PROGRESS", "RESOLVED"}
_COMPLAINT_TRANSITIONS = {
    "OPEN": {"ASSIGNED"},
    "ASSIGNED": {"IN_PROGRESS"},
    "IN_PROGRESS": {"RESOLVED"},
    "RESOLVED": set(),
}


def _normalize_status(value):
    if value is None:
        return None
    return str(value).strip().upper() or None


def _extract_room_no(value: str):
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    # Accept formats like "101" or "A-101"; return digits part.
    digits = re.findall(r"\d+", value)
    return str(digits[0]) if digits else None


_FINE_ALLOWED_STATUSES = {"UNPAID", "PAID"}


def _normalize_fine_status(value):
    if value is None:
        return None
    value = str(value).strip().upper()
    return value or None


def _fine_db_status_to_api(value):
    # Existing UI uses: Pending/Paid
    # Fine Management API uses: UNPAID/PAID
    value_norm = str(value).strip().lower() if value is not None else ""
    if value_norm == "paid":
        return "PAID"
    return "UNPAID"


def _fine_api_status_to_db(value):
    value_norm = _normalize_fine_status(value)
    if value_norm == "PAID":
        return "Paid"
    if value_norm == "UNPAID":
        return "Pending"
    return None


def _fine_student_username(fine: "HostelFine"):
    try:
        return str(fine.student.id.user.username)
    except Exception:
        return None


def _serialize_fine(fine: "HostelFine"):
    return {
        "fine_id": fine.fine_id,
        "student_id": _fine_student_username(fine),
        "student_name": fine.student_name,
        "amount": str(fine.amount) if fine.amount is not None else None,
        "reason": fine.reason,
        "hall_id": fine.hall_id,
        "status": _fine_db_status_to_api(fine.status),
    }


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def allocate_room_api(request):
    """Room Allocation Engine: allocate a room to a student (transactional).

    Body: {"student_id": "ST001", "room_no": "101"}
    """

    payload = request.data or {}
    student_id = payload.get("student_id")
    room_no_raw = payload.get("room_no")

    student_id = str(student_id).strip() if student_id is not None else ""
    room_no = str(room_no_raw).strip() if room_no_raw is not None else ""

    if not student_id or not room_no:
        return Response(
            {"success": False, "message": "student_id and room_no are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        student = StudentDetails.objects.select_for_update().filter(id=student_id).first()
        if not student:
            return Response(
                {"success": False, "message": "Student not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if student.room_num:
            return Response(
                {"success": False, "message": "Student already allocated"},
                status=status.HTTP_409_CONFLICT,
            )

        hall_pk = None
        if getattr(student, "hall_id", None):
            try:
                hall_pk = int(str(student.hall_id).strip())
            except Exception:
                hall_pk = None

        rooms_qs = HallRoom.objects.select_for_update().filter(room_no=room_no)
        if hall_pk is not None:
            rooms_qs = rooms_qs.filter(hall_id=hall_pk)

        room = rooms_qs.order_by("block_no", "id").first()
        if not room:
            return Response(
                {"success": False, "message": "Room not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if room.room_occupied >= room.room_cap:
            return Response(
                {"success": False, "message": "Room is full"},
                status=status.HTTP_403_FORBIDDEN,
            )

        student.room_num = room_no
        student.save(update_fields=["room_num"])

        room.room_occupied = room.room_occupied + 1
        room.save(update_fields=["room_occupied"])

    return Response(
        {"success": True, "message": "Room allocated successfully"},
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def deallocate_room_api(request):
    """Room Allocation Engine: deallocate a student's current room (transactional).

    Body: {"student_id": "ST001"}
    """

    payload = request.data or {}
    student_id = payload.get("student_id")
    student_id = str(student_id).strip() if student_id is not None else ""

    if not student_id:
        return Response(
            {"success": False, "message": "student_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        student = StudentDetails.objects.select_for_update().filter(id=student_id).first()
        if not student:
            return Response(
                {"success": False, "message": "Student not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        current_room_no = _extract_room_no(student.room_num)
        if not current_room_no:
            return Response(
                {"success": False, "message": "Student has no room allocated"},
                status=status.HTTP_409_CONFLICT,
            )

        hall_pk = None
        if getattr(student, "hall_id", None):
            try:
                hall_pk = int(str(student.hall_id).strip())
            except Exception:
                hall_pk = None

        rooms_qs = HallRoom.objects.select_for_update().filter(room_no=current_room_no)
        if hall_pk is not None:
            rooms_qs = rooms_qs.filter(hall_id=hall_pk)
        room = rooms_qs.order_by("block_no", "id").first()
        if not room:
            return Response(
                {"success": False, "message": "Room not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        student.room_num = None
        student.save(update_fields=["room_num"])

        room.room_occupied = max(0, int(room.room_occupied) - 1)
        room.save(update_fields=["room_occupied"])

    return Response(
        {"success": True, "message": "Room deallocated successfully"},
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def change_room_api(request):
    """Room Change Engine: change a student's room (transactional).

    Body: {"student_id": "ST001", "new_room_no": "102"}

    Business rules:
    - Student must already have a room
    - New room must exist and have available capacity
    - Cannot change to the same room
    - Update occupancy counts for old and new rooms atomically
    """

    payload = request.data or {}
    student_id = payload.get("student_id")
    new_room_raw = payload.get("new_room_no")

    student_id = str(student_id).strip() if student_id is not None else ""
    new_room_no = _extract_room_no(new_room_raw)

    if not student_id or not new_room_no:
        return Response(
            {"message": "student_id and new_room_no are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        student = StudentDetails.objects.select_for_update().filter(id=student_id).first()
        if not student:
            return Response(
                {"message": "Student not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        old_room_no = _extract_room_no(student.room_num)
        if not old_room_no:
            return Response(
                {"message": "Student has no room allocated"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if str(old_room_no) == str(new_room_no):
            return Response(
                {"message": "Same room selected"},
                status=status.HTTP_409_CONFLICT,
            )

        hall_pk = None
        if getattr(student, "hall_id", None):
            try:
                hall_pk = int(str(student.hall_id).strip())
            except Exception:
                hall_pk = None

        old_room_qs = HallRoom.objects.select_for_update().filter(room_no=old_room_no)
        new_room_qs = HallRoom.objects.select_for_update().filter(room_no=new_room_no)
        if hall_pk is not None:
            old_room_qs = old_room_qs.filter(hall_id=hall_pk)
            new_room_qs = new_room_qs.filter(hall_id=hall_pk)

        old_room = old_room_qs.order_by("block_no", "id").first()
        if not old_room:
            return Response(
                {"message": "Old room not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        new_room = new_room_qs.order_by("block_no", "id").first()
        if not new_room:
            return Response(
                {"message": "New room not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if int(new_room.room_occupied) >= int(new_room.room_cap):
            return Response(
                {"message": "Room is full"},
                status=status.HTTP_403_FORBIDDEN,
            )

        student.room_num = str(new_room_no)
        student.save(update_fields=["room_num"])

        old_room.room_occupied = max(0, int(old_room.room_occupied) - 1)
        old_room.save(update_fields=["room_occupied"])

        new_room.room_occupied = int(new_room.room_occupied) + 1
        new_room.save(update_fields=["room_occupied"])

    return Response(
        {
            "message": "Room changed successfully",
            "old_room": str(old_room_no),
            "new_room": str(new_room_no),
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def room_occupancy_api(request, room_no):
    """Return occupancy details for a room number.

    Optional query param: hall_id (to disambiguate).
    """

    room_no_value = str(room_no).strip() if room_no is not None else ""
    if not room_no_value:
        return Response(
            {"success": False, "message": "room_no is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    hall_id_param = request.query_params.get("hall_id")
    hall_pk = None
    if hall_id_param is not None and str(hall_id_param).strip() != "":
        try:
            hall_pk = int(str(hall_id_param).strip())
        except Exception:
            return Response(
                {"success": False, "message": "Invalid hall_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    rooms_qs = HallRoom.objects.filter(room_no=room_no_value)
    if hall_pk is not None:
        rooms_qs = rooms_qs.filter(hall_id=hall_pk)

    if hall_pk is None and rooms_qs.count() > 1:
        return Response(
            {"success": False, "message": "Multiple rooms found; provide hall_id"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    room = rooms_qs.order_by("block_no", "id").first()
    if not room:
        return Response(
            {"success": False, "message": "Room not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    capacity = int(room.room_cap)
    occupied = int(room.room_occupied)
    available = max(0, capacity - occupied)

    return Response(
        {
            "room_no": room.room_no,
            "capacity": capacity,
            "occupied": occupied,
            "available": available,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def student_room_details_api(request, student_id):
    """Return student + room details (joined by student's room_num)."""

    student_id_value = str(student_id).strip() if student_id is not None else ""
    if not student_id_value:
        return Response(
            {"success": False, "message": "student_id is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    student = StudentDetails.objects.filter(id=student_id_value).first()
    if not student:
        return Response(
            {"success": False, "message": "Student not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    room_no_value = _extract_room_no(student.room_num)
    room_payload = None
    if room_no_value:
        hall_pk = None
        if getattr(student, "hall_id", None):
            try:
                hall_pk = int(str(student.hall_id).strip())
            except Exception:
                hall_pk = None

        rooms_qs = HallRoom.objects.filter(room_no=room_no_value)
        if hall_pk is not None:
            rooms_qs = rooms_qs.filter(hall_id=hall_pk)
        room = rooms_qs.order_by("block_no", "id").first()
        if room:
            room_payload = {
                "room_no": room.room_no,
                "block_no": room.block_no,
                "capacity": int(room.room_cap),
                "occupied": int(room.room_occupied),
                "hall_id": getattr(room.hall, "id", None),
            }

    student_payload = {
        "id": student.id,
        "first_name": student.first_name,
        "last_name": student.last_name,
        "programme": student.programme,
        "batch": student.batch,
        "room_num": student.room_num,
        "hall_no": student.hall_no,
        "hall_id": student.hall_id,
    }

    return Response(
        {"success": True, "student": student_payload, "room": room_payload},
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@authentication_classes([])
@permission_classes([AllowAny])
def update_complaint_status_api(request, id):
    """Complaint workflow: update complaint status with strict transition rules."""

    try:
        complaint_id = int(id)
    except (TypeError, ValueError):
        return Response({"message": "Invalid id"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        complaint = HostelComplaint.objects.filter(id=complaint_id).first()
    except (ProgrammingError, OperationalError) as e:
        return Response(
            {
                "message": "Complaints table is not available. Did you run migrations?",
                "detail": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    if not complaint:
        return Response({"message": "Complaint not found"}, status=status.HTTP_404_NOT_FOUND)

    payload = request.data or {}
    new_status_api = _normalize_status(payload.get("status"))
    if not new_status_api:
        return Response({"message": "status is required"}, status=status.HTTP_400_BAD_REQUEST)

    if new_status_api not in _COMPLAINT_ALLOWED_STATUSES:
        return Response(
            {"message": "Invalid status"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    current_status = _complaint_api_status_from_db(getattr(complaint, "status", None) or "open")
    allowed_next = _COMPLAINT_TRANSITIONS.get(current_status, set())
    if new_status_api not in allowed_next:
        return Response(
            {"message": "Invalid status transition"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    new_status_db = _complaint_db_status_from_api(new_status_api)
    if not new_status_db:
        return Response(
            {"message": "Invalid status"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    complaint.status = new_status_db
    complaint.updated_at = timezone.now()
    complaint.save(update_fields=["status", "updated_at"])

    return Response(
        {"message": "Status updated", "status": new_status_api},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_complaints_by_status_api(request, status_value):
    """Return all complaints matching the given status."""

    normalized = _normalize_status(status_value)
    if not normalized:
        return Response({"message": "status is required"}, status=status.HTTP_400_BAD_REQUEST)

    if normalized not in _COMPLAINT_ALLOWED_STATUSES:
        return Response({"message": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

    db_status = _complaint_db_status_from_api(normalized)
    if not db_status:
        return Response({"message": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        complaints = HostelComplaint.objects.filter(status=db_status).order_by("-id")
    except (ProgrammingError, OperationalError) as e:
        return Response(
            {
                "message": "Complaints table is not available. Did you run migrations?",
                "detail": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    data = []
    for c in complaints:
        data.append(
            {
                "id": c.id,
                "hall_name": c.hall_name,
                "student_name": c.student_name,
                "roll_number": c.roll_number,
                "description": c.description,
                "contact_number": c.contact_number,
                "status": _complaint_api_status_from_db(getattr(c, "status", None)),
                "created_at": getattr(c, "created_at", None).isoformat() if getattr(c, "created_at", None) else None,
                "updated_at": getattr(c, "updated_at", None).isoformat() if getattr(c, "updated_at", None) else None,
            }
        )
    return Response(data, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def get_complaint_workflow_api(request, id):
    """Return workflow fields for a single complaint."""

    try:
        complaint_id = int(id)
    except (TypeError, ValueError):
        return Response({"message": "Invalid id"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        complaint = HostelComplaint.objects.filter(id=complaint_id).first()
    except (ProgrammingError, OperationalError) as e:
        return Response(
            {
                "message": "Complaints table is not available. Did you run migrations?",
                "detail": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    if not complaint:
        return Response({"message": "Complaint not found"}, status=status.HTTP_404_NOT_FOUND)

    data = {
        "id": complaint.id,
        "status": _complaint_api_status_from_db(getattr(complaint, "status", None)),
        "created_at": getattr(complaint, "created_at", None).isoformat() if getattr(complaint, "created_at", None) else None,
        "updated_at": getattr(complaint, "updated_at", None).isoformat() if getattr(complaint, "updated_at", None) else None,
    }
    return Response(data, status=status.HTTP_200_OK)


_LEAVE_UPLOAD_ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
_LEAVE_UPLOAD_MAX_BYTES = 5 * 1024 * 1024


def _save_leave_upload_file(uploaded_file):
    if uploaded_file is None:
        raise ValueError("file is required")

    try:
        size = int(getattr(uploaded_file, "size", 0) or 0)
    except Exception:
        size = 0

    if size <= 0:
        raise ValueError("file is required")
    if size > _LEAVE_UPLOAD_MAX_BYTES:
        raise ValueError("File size exceeds 5 MB")

    original_name = get_valid_filename(os.path.basename(str(getattr(uploaded_file, "name", "upload"))))
    _, ext = os.path.splitext(original_name)
    ext = (ext or "").lower()
    if ext not in _LEAVE_UPLOAD_ALLOWED_EXTENSIONS:
        raise ValueError("Invalid file type")

    generated_name = f"{uuid.uuid4().hex}{ext}"

    # Save locally on the machine under ~/Desktop/files
    upload_dir = os.path.expanduser(os.path.join("~", "Desktop", "files"))
    os.makedirs(upload_dir, exist_ok=True)
    abs_path = os.path.join(upload_dir, generated_name)

    with open(abs_path, "wb") as out:
        for chunk in uploaded_file.chunks():
            out.write(chunk)

    # Store a path-like reference in DB
    return f"files/{generated_name}"


def _safe_filefield_ref(file_field):
    """Return a safe reference for a FileField (prefer URL, else name, else None)."""
    try:
        if not file_field:
            return None
        name = getattr(file_field, "name", None)
        if not name:
            return None
        if isinstance(name, str) and name.startswith("files/"):
            return name
        try:
            return file_field.url
        except Exception:
            return name
    except Exception:
        return None


def _serialize_leave_row(leave):
    return {
        "id": leave.id,
        "student_name": leave.student_name,
        "roll_num": leave.roll_num,
        "reason": leave.reason,
        "phone_number": leave.phone_number,
        "start_date": leave.start_date.isoformat() if leave.start_date else None,
        "end_date": leave.end_date.isoformat() if leave.end_date else None,
        "status": leave.status,
        "remark": leave.remark,
        "file_upload": _safe_filefield_ref(getattr(leave, "file_upload", None)),
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def students_get_students_info(request):
    """Return student info used by Hostel Management React screens."""
    students = Student.objects.select_related("id__user").all()
    data = list(
        students.values(
            "id__user__username",
            "programme",
            "batch",
            "cpi",
            "category",
            "hall_no",
            "room_no",
            "specialization",
            "curr_semester_no",
        )
    )
    for row in data:
        hall_no = row.get("hall_no")
        row["hall_id"] = f"hall{hall_no}" if hall_no else None
    return Response(data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def caretaker_get_students_info(request):
    """Return student info scoped to the caretaker's assigned hall (if any)."""
    assigned_hall = get_staff_assigned_hall(request.user)
    hall_no = None
    if assigned_hall and getattr(assigned_hall, "hall_id", None):
        match = re.search(r"(\d+)", str(assigned_hall.hall_id))
        if match:
            hall_no = int(match.group(1))

    students = Student.objects.select_related("id__user")
    if hall_no is not None:
        students = students.filter(hall_no=hall_no)

    data = list(
        students.values(
            "id__user__username",
            "programme",
            "batch",
            "cpi",
            "category",
            "hall_no",
            "room_no",
            "specialization",
            "curr_semester_no",
        )
    )
    for row in data:
        row["hall_id"] = f"hall{row.get('hall_no')}" if row.get("hall_no") else None
    return Response(data, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([TokenAuthentication, SessionAuthentication])
@permission_classes([IsAuthenticated])
def fetch_fine(request):
    """Caretaker view: list fines for the caretaker's hall."""
    assigned_hall = get_staff_assigned_hall(request.user)
    if not assigned_hall:
        return Response({"fines": []}, status=status.HTTP_200_OK)

    fines = HostelFine.objects.filter(hall=assigned_hall).order_by("-fine_id")
    data = []
    for fine in fines:
        data.append(
            {
                "fine_id": fine.fine_id,
                "student_id": str(fine.student_id),
                "amount": str(fine.amount),
                "reason": fine.reason,
                "status": fine.status,
            }
        )
    return Response({"fines": data}, status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def create_leave_request_api(request):
    """طلاب: Create a leave request in the existing `leave_requests` table.

    Business rules:
    - Required fields validation
    - start_date <= end_date
    - start_date >= today
    - No overlap for same roll_num where status in Pending/Approved
    """

    if request.method == "GET":
        if not is_superuser(request.user) and not _is_caretaker_or_warden(request.user):
            return Response(
                {
                    "success": False,
                    "message": "You are not authorized to view leave requests",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        status_param = request.query_params.get("status")
        roll_num_param = request.query_params.get("roll_num")
        from_date_param = request.query_params.get("from_date")
        to_date_param = request.query_params.get("to_date")

        if isinstance(status_param, str):
            status_param = status_param.strip() or None
        if isinstance(roll_num_param, str):
            roll_num_param = roll_num_param.strip() or None
        if isinstance(from_date_param, str):
            from_date_param = from_date_param.strip() or None
        if isinstance(to_date_param, str):
            to_date_param = to_date_param.strip() or None

        allowed_statuses = {"Pending", "Approved", "Rejected"}
        if status_param and status_param not in allowed_statuses:
            return Response(
                {
                    "success": False,
                    "message": "Invalid status. Allowed: Pending, Approved, Rejected",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (from_date_param and not to_date_param) or (to_date_param and not from_date_param):
            return Response(
                {
                    "success": False,
                    "message": "Both from_date and to_date must be provided together",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        from_date = None
        to_date = None
        if from_date_param and to_date_param:
            try:
                from_date = date.fromisoformat(from_date_param)
                to_date = date.fromisoformat(to_date_param)
            except ValueError:
                return Response(
                    {
                        "success": False,
                        "message": "Invalid date format. Use YYYY-MM-DD for from_date/to_date",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        leaves = HostelLeave.objects.all()
        if status_param:
            leaves = leaves.filter(status__iexact=status_param)
        if roll_num_param:
            leaves = leaves.filter(roll_num__iexact=roll_num_param)
        if from_date and to_date:
            leaves = leaves.filter(start_date__lte=to_date, end_date__gte=from_date)

        leaves = leaves.order_by("-start_date", "-id")

        data = [_serialize_leave_row(leave) for leave in leaves]

        return Response(
            {"success": True, "count": len(data), "data": data},
            status=status.HTTP_200_OK,
        )

    payload = request.data or {}

    required_fields = [
        "student_name",
        "roll_num",
        "reason",
        "phone_number",
        "start_date",
        "end_date",
    ]
    missing = [f for f in required_fields if not str(payload.get(f, "")).strip()]
    if missing:
        return Response(
            {
                "success": False,
                "message": f"Missing required fields: {', '.join(missing)}",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    student_name = str(payload.get("student_name")).strip()
    roll_num = str(payload.get("roll_num")).strip()
    reason = str(payload.get("reason")).strip()
    phone_number = str(payload.get("phone_number")).strip()
    start_date_raw = str(payload.get("start_date")).strip()
    end_date_raw = str(payload.get("end_date")).strip()
    file_upload_ref = None
    try:
        uploaded_file = request.FILES.get("file_upload")
    except Exception:
        uploaded_file = None

    if uploaded_file is not None:
        try:
            file_upload_ref = _save_leave_upload_file(uploaded_file)
        except ValueError as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        file_upload_value = payload.get("file_upload", None)
        if isinstance(file_upload_value, str):
            file_upload_value = file_upload_value.strip() or None
        if isinstance(file_upload_value, str) and file_upload_value.startswith("files/"):
            file_upload_ref = file_upload_value

    try:
        start_date = date.fromisoformat(start_date_raw)
        end_date = date.fromisoformat(end_date_raw)
    except ValueError:
        return Response(
            {"success": False, "message": "start_date and end_date must be YYYY-MM-DD"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    now_dt = timezone.now()
    today = timezone.localdate(now_dt) if timezone.is_aware(now_dt) else now_dt.date()
    if start_date > end_date:
        return Response(
            {"success": False, "message": "start_date must be less than or equal to end_date"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if start_date < today:
        return Response(
            {"success": False, "message": "start_date cannot be before today"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Overlap rule
    # (existing.start_date <= new_end_date) AND (existing.end_date >= new_start_date)
    overlap_exists = HostelLeave.objects.filter(
        roll_num__iexact=roll_num,
        start_date__lte=end_date,
        end_date__gte=start_date,
    ).filter(Q(status__iexact="pending") | Q(status__iexact="approved")).exists()

    if overlap_exists:
        return Response(
            {
                "success": False,
                "message": "Existing leave already applied for overlapping dates",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    HostelLeave.objects.create(
        student_name=student_name,
        roll_num=roll_num,
        reason=reason,
        phone_number=phone_number,
        start_date=start_date,
        end_date=end_date,
        status="Pending",
        remark=None,
        file_upload=file_upload_ref,
    )

    return Response(
        {"success": True, "message": "Leave request submitted successfully"},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_leave_by_id_api(request, id):
    """Caretaker dashboard: fetch a single leave request by id."""

    if not is_superuser(request.user) and not _is_caretaker_or_warden(request.user):
        return Response(
            {
                "success": False,
                "message": "You are not authorized to view leave requests",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        leave_id = int(id)
    except (TypeError, ValueError):
        return Response(
            {"success": False, "message": "Invalid id"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if leave_id <= 0:
        return Response(
            {"success": False, "message": "Invalid id"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    leave = HostelLeave.objects.filter(id=leave_id).first()
    if not leave:
        return Response(
            {"success": False, "message": "Leave request not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    data = _serialize_leave_row(leave)
    return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_leaves_by_student_api(request, roll_num):
    """Caretaker dashboard: fetch all leave requests for a roll number."""

    if not is_superuser(request.user) and not _is_caretaker_or_warden(request.user):
        return Response(
            {
                "success": False,
                "message": "You are not authorized to view leave requests",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    roll_num_value = str(roll_num).strip() if roll_num is not None else ""
    if not roll_num_value:
        return Response(
            {"success": False, "message": "roll_num is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    leaves = HostelLeave.objects.filter(roll_num__iexact=roll_num_value).order_by("-start_date", "-id")
    data = [_serialize_leave_row(leave) for leave in leaves]

    return Response(
        {"success": True, "count": len(data), "data": data},
        status=status.HTTP_200_OK,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_leave_request_status_api(request, id):
    """Caretaker action: approve/reject a leave request.

    Rules:
    - Only Pending can be updated
    - status must be Approved or Rejected
    - remark required if Rejected
    - Update only status and remark
    """

    if not is_superuser(request.user) and not _is_caretaker_or_warden(request.user):
        return Response(
            {
                "success": False,
                "message": "You are not authorized to update leave request status",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        leave_id = int(id)
    except (TypeError, ValueError):
        return Response(
            {"success": False, "message": "Invalid id"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    payload = request.data or {}
    new_status_raw = payload.get("status")
    remark = payload.get("remark", None)

    if isinstance(new_status_raw, str):
        new_status_raw = new_status_raw.strip()
    if isinstance(remark, str):
        remark = remark.strip()
        if remark == "":
            remark = None

    status_norm = str(new_status_raw or "").strip().lower()
    if status_norm in {"approved", "approve"}:
        new_status = "Approved"
    elif status_norm in {"rejected", "reject"}:
        new_status = "Rejected"
    else:
        return Response(
            {"success": False, "message": "Invalid status value"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if new_status == "Rejected" and not remark:
        return Response(
            {"success": False, "message": "remark is required when status is Rejected"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    leave = HostelLeave.objects.filter(id=leave_id).first()
    if not leave:
        return Response(
            {"success": False, "message": "Leave request not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if str(leave.status or "").strip().lower() in {"approved", "rejected"}:
        return Response(
            {"success": False, "message": "Leave already processed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if str(leave.status or "").strip().lower() != "pending":
        return Response(
            {"success": False, "message": "Only Pending leaves can be updated"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    leave.status = new_status
    leave.remark = remark
    leave.save(update_fields=["status", "remark"])

    return Response(
        {"success": True, "message": "Leave status updated successfully"},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def upload_leave_file_api(request):
    """Upload a document for leave requests.

    Expects multipart/form-data with key: file
    Stores file under ~/Desktop/files and returns filePath.

        NOTE FOR FUTURE USERS:
        - This API stores files on the local machine (Desktop) and returns a DB reference
            like `files/<filename>`.
        - Returning `filePath` does NOT make the file publicly accessible via HTTP.
    """

    try:
        uploaded_file = request.FILES.get("file")
        file_path = _save_leave_upload_file(uploaded_file)
        return Response({"success": True, "filePath": file_path}, status=status.HTTP_200_OK)
    except ValueError as e:
        message = str(e)
        return Response({"success": False, "message": message}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response(
            {"success": False, "message": "Upload failed"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_leave_upload_api(request, id):
    """Upload a file and update the file_upload column for a leave request id."""

    try:
        leave_id = int(id)
    except (TypeError, ValueError):
        return Response({"success": False, "message": "Invalid id"}, status=status.HTTP_400_BAD_REQUEST)

    if leave_id <= 0:
        return Response({"success": False, "message": "Invalid id"}, status=status.HTTP_400_BAD_REQUEST)

    leave = HostelLeave.objects.filter(id=leave_id).first()
    if not leave:
        return Response(
            {"success": False, "message": "Leave request not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        uploaded_file = request.FILES.get("file")
        file_path = _save_leave_upload_file(uploaded_file)
    except ValueError as e:
        return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception:
        return Response(
            {"success": False, "message": "Upload failed"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    try:
        leave.file_upload = file_path
        leave.save(update_fields=["file_upload"])
    except Exception:
        return Response(
            {"success": False, "message": "Database update failed"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response({"success": True, "filePath": file_path}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_leaves_api(request):
    """Student: fetch own leaves for the currently authenticated user."""

    user_id = str(request.user).strip()
    leaves = HostelLeave.objects.filter(roll_num__iexact=user_id).order_by("-start_date", "-id")

    data = [_serialize_leave_row(leave) for leave in leaves]
    return Response({"success": True, "leaves": data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def leave_document_api(request, id):
    """Return the supporting document uploaded for a leave request.

    Only the leave owner (student), caretaker/superuser can access.
    Files are stored under ~/Desktop/files and referenced as `files/<uuid>.<ext>`.
    """

    try:
        leave_id = int(id)
    except (TypeError, ValueError):
        return Response({"success": False, "message": "Invalid id"}, status=status.HTTP_400_BAD_REQUEST)

    leave = HostelLeave.objects.filter(id=leave_id).first()
    if not leave:
        return Response({"success": False, "message": "Leave request not found"}, status=status.HTTP_404_NOT_FOUND)

    # AuthZ: superuser/caretaker/warden can view, else only owner
    can_view = False
    if is_superuser(request.user):
        can_view = True
    else:
        try:
            staff_id = request.user.extrainfo.id
        except Exception:
            staff_id = None
        if staff_id is not None and HallCaretaker.objects.filter(staff_id=staff_id).exists():
            can_view = True
        if not can_view and staff_id is not None and HallWarden.objects.filter(faculty_id=staff_id).exists():
            can_view = True

    if not can_view:
        user_id = str(getattr(request.user, "username", request.user)).strip().lower()
        roll_num = str(getattr(leave, "roll_num", "") or "").strip().lower()
        can_view = bool(user_id and roll_num and user_id == roll_num)

    if not can_view:
        return Response({"success": False, "message": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)

    file_name = None
    try:
        file_name = getattr(leave.file_upload, "name", None)
    except Exception:
        file_name = None
    if not file_name:
        file_name = str(getattr(leave, "file_upload", "") or "").strip() or None

    if not file_name:
        return Response({"success": False, "message": "No document uploaded"}, status=status.HTTP_404_NOT_FOUND)

    abs_path = None
    if isinstance(file_name, str) and file_name.startswith("files/"):
        # Strict pattern to avoid path traversal
        if not re.fullmatch(r"files/[0-9a-fA-F]{32}\.(pdf|jpg|jpeg|png)", file_name):
            return Response({"success": False, "message": "Invalid document reference"}, status=status.HTTP_404_NOT_FOUND)
        abs_path = os.path.expanduser(os.path.join("~", "Desktop", file_name))
    elif isinstance(file_name, str) and file_name.startswith("/uploads/leaves/"):
        base_dir = getattr(settings, "BASE_DIR", None) or os.getcwd()
        abs_path = os.path.abspath(os.path.join(str(base_dir), "..", file_name.lstrip("/")))

    if not abs_path or not os.path.exists(abs_path) or not os.path.isfile(abs_path):
        return Response({"success": False, "message": "File not found"}, status=status.HTTP_404_NOT_FOUND)

    content_type, _ = mimetypes.guess_type(abs_path)
    response = FileResponse(open(abs_path, "rb"), content_type=content_type or "application/octet-stream")
    response["Content-Disposition"] = f'inline; filename="{os.path.basename(abs_path)}"'
    return response


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def impose_fine(request):
    """Caretaker view: impose a fine on a student."""
    student_username = request.data.get("studentId")
    fine_amount = request.data.get("fineAmount")
    fine_reason = request.data.get("fineReason")

    if not student_username or fine_amount is None or not fine_reason:
        return Response({"message": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

    assigned_hall = get_staff_assigned_hall(request.user)
    if not assigned_hall:
        return Response({"message": "No hall assigned to this user."}, status=status.HTTP_403_FORBIDDEN)

    try:
        student = Student.objects.select_related("id__user").get(id__user__username=student_username)
    except Student.DoesNotExist:
        return Response({"message": "Student not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        amount = Decimal(str(fine_amount))
    except (InvalidOperation, TypeError):
        return Response({"message": "Invalid fine amount."}, status=status.HTTP_400_BAD_REQUEST)

    fine = HostelFine.objects.create(
        student=student,
        hall=assigned_hall,
        student_name=student_username,
        amount=amount,
        status="Pending",
        reason=fine_reason,
    )

    return Response({"fine_id": fine.fine_id, "message": "Fine imposed."}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_fine_status(request, fine_id):
    """Caretaker view: update fine status (Paid/Pending)."""
    status_value = request.data.get("status")
    if status_value not in {"Paid", "Pending"}:
        return Response({"error": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)

    assigned_hall = get_staff_assigned_hall(request.user)
    if not assigned_hall:
        return Response({"error": "No hall assigned to this user."}, status=status.HTTP_403_FORBIDDEN)

    try:
        fine = HostelFine.objects.get(fine_id=fine_id, hall=assigned_hall)
    except HostelFine.DoesNotExist:
        return Response({"error": "Fine not found."}, status=status.HTTP_404_NOT_FOUND)

    fine.status = status_value
    fine.save(update_fields=["status"])
    return Response({"message": "Status updated."}, status=status.HTTP_200_OK)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def fines_collection_api(request):
    """Fine Management System.

    Endpoints:
    - POST /api/fines
    - GET  /api/fines

    Notes:
    - Existing hostel UI uses `HostelFine.status` as "Pending"/"Paid".
    - This API exposes status as "UNPAID"/"PAID" while persisting as "Pending"/"Paid".
    """

    if request.method == "GET":
        fines = HostelFine.objects.select_related("student", "hall").order_by("-fine_id")
        return Response(
            {"fines": [_serialize_fine(f) for f in fines]},
            status=status.HTTP_200_OK,
        )

    payload = request.data or {}
    student_id = str(payload.get("student_id") or "").strip()
    student_name = str(payload.get("student_name") or "").strip()
    amount_raw = payload.get("amount")
    reason = str(payload.get("reason") or "").strip()
    hall_id_raw = payload.get("hall_id")

    if not student_id or not student_name or amount_raw is None or not reason or hall_id_raw is None:
        return Response(
            {"message": "student_id, student_name, amount, reason, hall_id are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        amount = Decimal(str(amount_raw))
    except (InvalidOperation, TypeError):
        return Response({"message": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

    if amount <= 0:
        return Response({"message": "amount must be > 0"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        hall_pk = int(str(hall_id_raw).strip())
    except Exception:
        return Response({"message": "Invalid hall_id"}, status=status.HTTP_400_BAD_REQUEST)

    hall = Hall.objects.filter(id=hall_pk).first()
    if not hall:
        return Response({"message": "Hall not found"}, status=status.HTTP_404_NOT_FOUND)

    # Business rule: fine must be linked to a valid student_id.
    # In Fusion, the identifier used by hostel UI is the student's username/roll no.
    student = Student.objects.select_related("id__user").filter(id__user__username=student_id).first()
    if not student:
        return Response({"message": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

    fine = HostelFine.objects.create(
        student=student,
        hall=hall,
        student_name=student_name,
        amount=amount,
        status="Pending",
        reason=reason,
    )

    return Response(
        {
            "message": "Fine created successfully",
            "fine_id": fine.fine_id,
            "status": "UNPAID",
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def fine_status_api(request, fine_id):
    """PATCH /api/fines/:fine_id/status

    Body: {"status": "PAID"}
    Rules:
    - Fine must exist
    - Allowed status: UNPAID, PAID
    - If fine is already PAID, reject updates
    """

    try:
        fine_pk = int(fine_id)
    except (TypeError, ValueError):
        return Response({"message": "Invalid fine_id"}, status=status.HTTP_400_BAD_REQUEST)

    payload = request.data or {}
    new_status = _normalize_fine_status(payload.get("status"))
    if new_status not in _FINE_ALLOWED_STATUSES:
        return Response(
            {"message": "Invalid status. Allowed: UNPAID, PAID"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    fine = HostelFine.objects.filter(fine_id=fine_pk).first()
    if not fine:
        return Response({"message": "Fine not found"}, status=status.HTTP_404_NOT_FOUND)

    if str(fine.status).strip().lower() == "paid":
        return Response({"message": "Fine already PAID"}, status=status.HTTP_409_CONFLICT)

    db_status = _fine_api_status_to_db(new_status)
    if db_status is None:
        return Response(
            {"message": "Invalid status. Allowed: UNPAID, PAID"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    fine.status = db_status
    fine.save(update_fields=["status"])
    return Response({"message": "Status updated", "fine_id": fine_pk, "status": new_status}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fines_by_student_api(request, student_id):
    """GET /api/fines/student/:student_id"""

    student_id_value = str(student_id).strip() if student_id is not None else ""
    if not student_id_value:
        return Response({"message": "student_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    student = Student.objects.select_related("id__user").filter(id__user__username=student_id_value).first()
    if not student:
        return Response({"message": "Student not found"}, status=status.HTTP_404_NOT_FOUND)

    fines = HostelFine.objects.select_related("student", "hall").filter(student=student).order_by("-fine_id")
    return Response(
        {"student_id": student_id_value, "fines": [_serialize_fine(f) for f in fines]},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def fine_stats_api(request):
    """GET /api/fines/stats

    Returns summary counts and unpaid totals.
    """

    total_fines = HostelFine.objects.count()
    paid_fines = HostelFine.objects.filter(status__iexact="Paid").count()
    unpaid_fines = HostelFine.objects.exclude(status__iexact="Paid").count()
    total_unpaid_amount = (
        HostelFine.objects.exclude(status__iexact="Paid")
        .aggregate(total=models.Sum("amount"))
        .get("total")
    )
    if total_unpaid_amount is None:
        total_unpaid_amount = Decimal("0")

    return Response(
        {
            "total_fines": int(total_fines),
            "unpaid_fines": int(unpaid_fines),
            "paid_fines": int(paid_fines),
            "total_unpaid_amount": str(total_unpaid_amount),
        },
        status=status.HTTP_200_OK,
    )

# //! My change


@login_required
def hostel_view(request, context={}):
    """
    This is a general function which is used for all the views functions.
    This function renders all the contexts required in templates.
    @param:
        request - HttpRequest object containing metadata about the user request.
        context - stores any data passed during request,by default is empty.

    @variables:
        hall_1_student - stores all hall 1 students
        hall_3_student - stores all hall 3 students
        hall_4_student - stores all hall 4 students
        all_hall - stores all the hall of residence
        all_notice - stores all notices of hostels (latest first)
    """
    # Check if the user is a superuser
    is_superuser = request.user.is_superuser

    all_hall = list(get_all_halls())
    halls_student = get_halls_students_map(all_hall)
    hall_staffs = get_halls_staff_schedules_map(all_hall)

    all_notice = HostelNoticeBoard.objects.all().order_by("-id")
    hall_notices = get_halls_notices_map(all_hall)
    pending_guest_room_requests = get_pending_guest_room_requests_map(all_hall)
    guest_rooms = get_guest_rooms_map(all_hall)
    user_guest_room_requests = GuestRoomBooking.objects.filter(intender=request.user).order_by(
        "-arrival_date"
    )

    assignments = get_hall_staff_assignments_map(all_hall)

    # Create a list to store additional details
    hostel_details = []
    for hall in all_hall:
        caretaker = assignments.get(hall.hall_id, {}).get("caretaker")
        warden = assignments.get(hall.hall_id, {}).get("warden")

        vacant_seat = hall.max_accomodation - hall.number_students
        hostel_details.append(
            {
                'hall_id': hall.hall_id,
                'hall_name': hall.hall_name,
                'seater_type': hall.type_of_seater,
                'max_accomodation': hall.max_accomodation,
                'number_students': hall.number_students,
                'vacant_seat': vacant_seat,
                'assigned_batch': hall.assigned_batch,
                'assigned_caretaker': caretaker.staff.id.user.username if caretaker else None,
                'assigned_warden': warden.faculty.id.user.username if warden else None,
            }
        )

    Staff_obj = Staff.objects.all().select_related('id__user')
    hall1 = Hall.objects.get(hall_id='hall1')
    hall3 = Hall.objects.get(hall_id='hall3')
    hall4 = Hall.objects.get(hall_id='hall4')
    hall1_staff = StaffSchedule.objects.filter(hall=hall1)
    hall3_staff = StaffSchedule.objects.filter(hall=hall3)
    hall4_staff = StaffSchedule.objects.filter(hall=hall4)
    hall_caretakers = HallCaretaker.objects.select_related('hall', 'staff__id__user')
    hall_wardens = HallWarden.objects.select_related('hall', 'faculty__id__user')

    all_students = Student.objects.all().select_related('id__user')
    all_students_id = list(all_students.values_list('id_id', flat=True))
    # print(all_students)
    hall_student = ""
    current_hall = ""
    get_avail_room = get_available_rooms_for_halls(all_hall)

    assigned_hall = get_staff_assigned_hall(request.user)
    if assigned_hall:
        hall_student = halls_student.get(assigned_hall.hall_id, [])
        current_hall = assigned_hall.hall_id

    hall_caretaker_user = []
    for caretaker in hall_caretakers:
        hall_caretaker_user.append(caretaker.staff.id.user)

    hall_warden_user = []
    for warden in hall_wardens:
        hall_warden_user.append(warden.faculty.id.user)

    todays_date = date.today()
    current_year = todays_date.year
    current_month = todays_date.month

    if current_month != 1:
        worker_report = WorkerReport.objects.filter(Q(hall__hall_id=current_hall, year=current_year, month=current_month) | Q(
            hall__hall_id=current_hall, year=current_year, month=current_month-1))
    else:
        worker_report = WorkerReport.objects.filter(
            hall__hall_id=current_hall, year=current_year-1, month=12)

    halls_attendance = get_halls_attendance_map(all_hall)

    user_complaints = HostelComplaint.objects.filter(
        roll_number=request.user.username)
    user_leaves = HostelLeave.objects.filter(roll_num=request.user.username)
    my_leaves = []
    for leave in user_leaves:
        my_leaves.append(leave)
    my_complaints = []
    for complaint in user_complaints:
        my_complaints.append(complaint)

    all_leaves = HostelLeave.objects.all()
    all_complaints = HostelComplaint.objects.all()

    add_hostel_form = HallForm()
    warden_ids = Faculty.objects.all().select_related('id__user')

    # //! My change for imposing fines
    user_id = request.user
    try:
        staff_fine_caretaker = user_id.extrainfo.id
    except Exception:
        staff_fine_caretaker = None
    students = all_students

    fine_user = request.user

    if is_user_staff(request.user) and staff_fine_caretaker:
        caretaker_fine_id = HallCaretaker.objects.filter(staff_id=staff_fine_caretaker).first()
        if caretaker_fine_id:
            hall_fine_id = caretaker_fine_id.hall_id
            hostel_fines = HostelFine.objects.filter(hall_id=hall_fine_id).order_by('fine_id')
            context['hostel_fines'] = hostel_fines

    # caretaker_fine_id = HallCaretaker.objects.get(staff_id=staff_fine_caretaker)
    # hall_fine_id = caretaker_fine_id.hall_id
    # hostel_fines = HostelFine.objects.filter(hall_id=hall_fine_id).order_by('fine_id')

    if is_user_staff(request.user) and staff_fine_caretaker:
        caretaker_inventory_id = HallCaretaker.objects.filter(staff_id=staff_fine_caretaker).first()

        if caretaker_inventory_id:
            hall_inventory_id = caretaker_inventory_id.hall_id
            inventories = HostelInventory.objects.filter(
                hall_id=hall_inventory_id).order_by('inventory_id')

            # Serialize inventory data
            inventory_data = []
            for inventory in inventories:
                inventory_data.append({
                    'inventory_id': inventory.inventory_id,
                    'hall_id': inventory.hall_id,
                    'inventory_name': inventory.inventory_name,
                    # Convert DecimalField to string
                    'cost': str(inventory.cost),
                    'quantity': inventory.quantity,
                })

            inventory_data.sort(key=lambda x: x['inventory_id'])
            context['inventories'] = inventory_data

    # all students details for caretaker and warden
    if is_user_staff(request.user) and staff_fine_caretaker:
        caretaker_assignment = (
            HallCaretaker.objects.filter(staff_id=staff_fine_caretaker)
            .select_related('hall')
            .first()
        )
        if caretaker_assignment:
            payload = build_student_details_for_hall(
                caretaker_assignment.hall, include_available_rooms=True
            )
            context['hostel_students_details'] = payload['students']
            context['av_room'] = payload.get('available_rooms', [])

    if is_user_faculty(request.user) and staff_fine_caretaker:
        warden_assignment = (
            HallWarden.objects.filter(faculty_id=staff_fine_caretaker)
            .select_related('hall')
            .first()
        )
        if warden_assignment:
            payload = build_student_details_for_hall(warden_assignment.hall)
            context['hostel_students_details'] = payload['students']

            


    # print(request.user.username);
    if Student.objects.filter(id_id=request.user.username).exists():
        user_id = request.user.username
        student_fines = HostelFine.objects.filter(student_id=user_id)
        # print(student_fines)
        context['student_fines'] = student_fines

    hostel_transactions = HostelTransactionHistory.objects.order_by('-timestamp')

    # Retrieve all hostel history entries
    hostel_history = HostelHistory.objects.order_by('-timestamp')
    context = {

        'all_hall': all_hall,
        'all_notice': all_notice,
        'staff': Staff_obj,
        'hall1_staff': hall1_staff,
        'hall3_staff': hall3_staff,
        'hall4_staff': hall4_staff,
        'hall_caretaker': hall_caretaker_user,
        'hall_warden': hall_warden_user,
        'room_avail': get_avail_room,
        'hall_student': hall_student,
        'worker_report': worker_report,
        'halls_student': halls_student,
        'current_hall': current_hall,
        'hall_staffs': hall_staffs,
        'hall_notices': hall_notices,
        'attendance': halls_attendance,
        'guest_rooms': guest_rooms,
        'pending_guest_room_requests': pending_guest_room_requests,
        'user_guest_room_requests': user_guest_room_requests,
        'all_students_id': all_students_id,
        'is_superuser': is_superuser,
        'warden_ids': warden_ids,
        'add_hostel_form': add_hostel_form,
        'hostel_details': hostel_details,
        'all_students_id': all_students_id,
        'my_complaints': my_complaints,
        'my_leaves': my_leaves,
        'all_leaves': all_leaves,
        'all_complaints': all_complaints,
        'staff_fine_caretaker': staff_fine_caretaker,
        'students': students,
        'hostel_transactions':hostel_transactions,
        'hostel_history':hostel_history,
        **context
    }

    return render(request, 'hostelmanagement/hostel.html', context)
    
def staff_edit_schedule(request):
    """
    This function is responsible for creating a new or updating an existing staff schedule.
    @param:
       request - HttpRequest object containing metadata about the user request.

    @variables:
       start_time - stores start time of the schedule.
       end_time - stores endtime of the schedule.
       staff_name - stores name of staff.
       staff_type - stores type of staff.
       day - stores assigned day of the schedule.
       staff - stores Staff instance related to staff_name.
       staff_schedule - stores StaffSchedule instance related to 'staff'.
       hall_caretakers - stores all hall caretakers.
    """
    if request.method == 'POST':
        start_time = datetime.datetime.strptime(
            request.POST["start_time"], '%H:%M').time()
        end_time = datetime.datetime.strptime(
            request.POST["end_time"], '%H:%M').time()
        staff_name = request.POST["Staff_name"]
        staff_type = request.POST["staff_type"]
        day = request.POST["day"]

        staff = Staff.objects.get(pk=staff_name)
        try:
            staff_schedule = StaffSchedule.objects.get(staff_id=staff)
            staff_schedule.day = day
            staff_schedule.start_time = start_time
            staff_schedule.end_time = end_time
            staff_schedule.staff_type = staff_type
            staff_schedule.save()
            messages.success(request, 'Staff schedule updated successfully.')
        except:
            hall_caretakers = HallCaretaker.objects.all()
            get_hall = ""
            get_hall = get_caretaker_hall(hall_caretakers, request.user)
            StaffSchedule(hall=get_hall, staff_id=staff, day=day,
                          staff_type=staff_type, start_time=start_time, end_time=end_time).save()
            messages.success(request, 'Staff schedule created successfully.')
    return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


def staff_delete_schedule(request):
    """
    This function is responsible for deleting an existing staff schedule.
    @param:
      request - HttpRequest object containing metadata about the user request.

    @variables:
      staff_dlt_id - stores id of the staff whose schedule is to be deleted.
      staff - stores Staff object related to 'staff_name'
      staff_schedule - stores staff schedule related to 'staff'
    """
    if request.method == 'POST':
        staff_dlt_id = request.POST["dlt_schedule"]
        staff = Staff.objects.get(pk=staff_dlt_id)
        staff_schedule = StaffSchedule.objects.get(staff_id=staff)
        staff_schedule.delete()
    return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


@login_required
def notice_board(request):
    """
    This function is used to create a form to show the notice on the Notice Board.
    @param:
      request - HttpRequest object containing metadata about the user request.

    @variables:
      hall - stores hall of residence related to the notice.
      head_line - stores headline of the notice. 
      content - stores content of the notice uploaded as file.
      description - stores description of the notice.
    """
    if request.method == "POST":
        form = HostelNoticeBoardForm(request.POST, request.FILES)

        if form.is_valid():
            hall = form.cleaned_data['hall']
            head_line = form.cleaned_data['head_line']
            content = form.cleaned_data['content']
            description = form.cleaned_data['description']

            new_notice = HostelNoticeBoard.objects.create(hall=hall, posted_by=request.user.extrainfo, head_line=head_line, content=content,
                                                          description=description)

            new_notice.save()
            messages.success(request, 'Notice created successfully.')
        return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([TokenAuthentication])
def create_notice(request):
    """Create a hostel notice from frontend payload.

    Supported payload keys:
    - headline | head_line
    - content
    - description
    - hall | hall_id (optional)
    - scope (accepted but not persisted)
    """
    payload = request.data or {}

    headline = (payload.get('headline') or payload.get('head_line') or '').strip()
    content = payload.get('content') or ''
    description = payload.get('description') or ''

    if not headline:
        return JsonResponse({'message': 'headline is required'}, status=400)

    hall = None
    hall_value = payload.get('hall_id') or payload.get('hall')

    if hall_value not in (None, ''):
        hall = Hall.objects.filter(pk=hall_value).first()
        if hall is None:
            hall = Hall.objects.filter(hall_id=str(hall_value)).first()

    # If hall is not explicitly provided, infer from caretaker/warden assignment.
    if hall is None:
        user_extrainfo_id = getattr(getattr(request.user, 'extrainfo', None), 'id', None)

        if user_extrainfo_id:
            caretaker_assignment = (
                HallCaretaker.objects.filter(staff_id=user_extrainfo_id)
                .select_related('hall')
                .first()
            )
            if caretaker_assignment:
                hall = caretaker_assignment.hall

        if hall is None and user_extrainfo_id:
            warden_assignment = (
                HallWarden.objects.filter(faculty_id=user_extrainfo_id)
                .select_related('hall')
                .first()
            )
            if warden_assignment:
                hall = warden_assignment.hall

    # Last fallback for admin/global usage when no assignment exists.
    if hall is None:
        hall = Hall.objects.order_by('id').first()

    if hall is None:
        return JsonResponse({'message': 'No hall available to attach notice'}, status=400)

    new_notice = HostelNoticeBoard.objects.create(
        hall=hall,
        posted_by=request.user.extrainfo,
        head_line=headline,
        content=content,
        description=description,
    )

    return JsonResponse(
        {
            'id': new_notice.id,
            'head_line': new_notice.head_line,
            'content': new_notice.content.name if new_notice.content else '',
            'content_url': (
                request.build_absolute_uri(new_notice.content.url)
                if new_notice.content
                else ''
            ),
            'description': new_notice.description,
            'hall_id': new_notice.hall_id,
            'posted_by_id': new_notice.posted_by_id,
            'created_at': new_notice.created_at.isoformat() if new_notice.created_at else '',
            'updated_at': new_notice.updated_at.isoformat() if new_notice.updated_at else '',
            'message': 'Notice created successfully',
        },
        status=201,
    )


@login_required
def delete_notice(request):
    """
    This function is responsible for deleting ana existing notice from the notice board.
    @param:
      request - HttpRequest object containing metadata about the user request.

    @variables:
      notice_id - stores id of the notice.
      notice - stores HostelNoticeBoard object related to 'notice_id'
    """
    if request.method == 'POST':
        notice_id = request.POST["dlt_notice"]
        notice = HostelNoticeBoard.objects.get(pk=notice_id)
        notice.delete()
    return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


def edit_student_rooms_sheet(request):
    """
    This function is used to edit the room and hall of a multiple students.
    The user uploads a .xls file with Roll No, Hall No, and Room No to be updated.
    @param:
        request - HttpRequest object containing metadata about the user request.
    """
    if request.method == "POST":
        sheet = request.FILES["upload_rooms"]
        excel = xlrd.open_workbook(file_contents=sheet.read())
        all_rows = excel.sheets()[0]
        for row in all_rows:
            if row[0].value == "Roll No":
                continue
            roll_no = row[0].value
            hall_no = row[1].value
            if row[0].ctype == 2:
                roll_no = str(int(roll_no))
            if row[1].ctype == 2:
                hall_no = str(int(hall_no))

            room_no = row[2].value
            block = str(room_no[0])
            room = re.findall('[0-9]+', room_no)
            is_valid = True
            student = Student.objects.filter(id=roll_no.strip())
            hall = Hall.objects.filter(hall_id="hall"+hall_no[0])
            if student and hall.exists():
                Room = HallRoom.objects.filter(
                    hall=hall[0], block_no=block, room_no=str(room[0]))
                if Room.exists() and Room[0].room_occupied < Room[0].room_cap:
                    continue
                else:
                    is_valid = False
                    # print('Room  unavailable!')
                    messages.error(request, 'Room  unavailable!')
                    break
            else:
                is_valid = False
                # print("Wrong Credentials entered!")
                messages.error(request, 'Wrong credentials entered!')
                break

        if not is_valid:
            return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))

        for row in all_rows:
            if row[0].value == "Roll No":
                continue
            roll_no = row[0].value
            if row[0].ctype == 2:
                roll_no = str(int(roll_no))

            hall_no = str(int(row[1].value))
            room_no = row[2].value
            block = str(room_no[0])
            room = re.findall('[0-9]+', room_no)
            is_valid = True
            student = Student.objects.filter(id=roll_no.strip())
            remove_from_room(student[0])
            add_to_room(student[0], room_no, hall_no)
        messages.success(request, 'Hall Room change successfull !')

        return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


def edit_student_room(request):
    """
    This function is used to edit the room number of a student.
    @param:
      request - HttpRequest object containing metadata about the user request.

    @varibles:
      roll_no - stores roll number of the student.
      room_no - stores new room number. 
      batch - stores batch number of the student generated from 'roll_no'
      students - stores students related to 'batch'.
    """
    if request.method == "POST":
        roll_no = request.POST["roll_no"]
        hall_room_no = request.POST["hall_room_no"]
        index = hall_room_no.find('-')
        room_no = hall_room_no[index+1:]
        hall_no = hall_room_no[:index]
        student = Student.objects.get(id=roll_no)
        remove_from_room(student)
        add_to_room(student, new_room=room_no, new_hall=hall_no)
        messages.success(request, 'Student room changed successfully.')
        return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


def edit_attendance(request):
    """
    This function is used to edit the attendance of a student.
    @param:
      request - HttpRequest object containing metadata about the user request.

    @variables:
      student_id = The student whose attendance has to be updated.
      hall = The hall of the concerned student.
      date = The date on which attendance has to be marked.
    """
    if request.method == "POST":
        roll_no = request.POST["roll_no"]

        student = Student.objects.get(id=roll_no)
        hall = Hall.objects.get(hall_id='hall'+str(student.hall_no))
        date = datetime.datetime.today().strftime('%Y-%m-%d')

        if HostelStudentAttendence.objects.filter(student_id=student, date=date).exists() == True:
            messages.error(
                request, f'{student.id.id} is already marked present on {date}')
            return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))

        record = HostelStudentAttendence.objects.create(student_id=student,
                                                        hall=hall, date=date, present=True)
        record.save()

        messages.success(request, f'Attendance of {student.id.id} recorded.')

        return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


# @login_required
# def generate_worker_report(request):
#     """
#     This function is used to read uploaded worker report spreadsheet(.xls) and generate WorkerReport instance and save it in the database.
#     @param:
#       request - HttpRequest object containing metadata about the user request.

#     @variables:
#       files - stores uploaded worker report file 
#       excel - stores the opened spreadsheet file raedy for data extraction.
#       user_id - stores user id of the current user.
#       sheet - stores a sheet from the uploaded spreadsheet.
#     """
#     if request.method == "POST":
#         try:
#             files = request.FILES['upload_report']
#             excel = xlrd.open_workbook(file_contents=files.read())
#             user_id = request.user.extrainfo.id
#             if str(excel.sheets()[0].cell(0, 0).value)[:5].lower() == str(HallCaretaker.objects.get(staff__id=user_id).hall):
#                 for sheet in excel.sheets():
#                     save_worker_report_sheet(excel, sheet, user_id)
#                     return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))

#             return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))
#         except:
#             messages.error(
#                 request, "Please upload a file in valid format before submitting")
#             return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


# class GeneratePDF(View):
#     def get(self, request, *args, **kwargs):
#         """
#         This function is used to generate worker report in pdf format available for download.
#         @param:
#           request - HttpRequest object containing metadata about the user request.

#         @variables:
#           months - stores number of months for which the authorized user wants to generate worker report.
#           toadys_date - stores current date.
#           current_year - stores current year retrieved from 'todays_date'.
#           current_month - stores current month retrieved from 'todays_date'.
#           template - stores template returned by 'get_template' method.
#           hall_caretakers - stores all hall caretakers.
#           worker_report - stores 'WorkerReport' instances according to 'months'.

#         """
#         months = int(request.GET.get('months'))
#         todays_date = date.today()
#         current_year = todays_date.year
#         current_month = todays_date.month

#         template = get_template('hostelmanagement/view_report.html')

#         hall_caretakers = HallCaretaker.objects.all()
#         get_hall = ""
#         get_hall = get_caretaker_hall(hall_caretakers, request.user)
        
#         if months < current_month:
#             worker_report = WorkerReport.objects.filter(
#                 hall=get_hall, month__gte=current_month-months, year=current_year)
#         else:
#             worker_report = WorkerReport.objects.filter(Q(hall=get_hall, year=current_year, month__lte=current_month) | Q(
#                 hall=get_hall, year=current_year-1, month__gte=12-months+current_month))

#         worker = {
#             'worker_report': worker_report
#         }
#         html = template.render(worker)
#         pdf = render_to_pdf('hostelmanagement/view_report.html', worker)
#         if pdf:
#             response = HttpResponse(pdf, content_type='application/pdf')
#             filename = "Invoice_%s.pdf" % ("12341231")
#             content = "inline; filename='%s'" % (filename)
#             download = request.GET.get("download")
#             if download:
#                 content = "attachment; filename='%s'" % (filename)
#             response['Content-Disposition'] = content
#             return response
#         return HttpResponse("Not found")

@login_required
def generate_worker_report(request):
    if request.method == "POST":
        try:
            files = request.FILES.get('upload_report')
            if files:
                # Check if the file has a valid extension
                file_extension = files.name.split('.')[-1].lower()
                if file_extension not in ['xls', 'xlsx']:
                    messages.error(request, "Invalid file format. Please upload a .xls or .xlsx file.")
                    return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))
                
                excel = xlrd.open_workbook(file_contents=files.read())
                user_id = request.user.extrainfo.id
                for sheet in excel.sheets():
                    # print('111111111111111111111111111111111111',sheet[0])
                    save_worker_report_sheet(excel, sheet, user_id)
                return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))
            else:
                messages.error(request, "No file uploaded")
        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")
    return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


class GeneratePDF(View):
    def get(self, request, *args, **kwargs):
        """
        This function is used to generate worker report in pdf format available for download.
        @param:
          request - HttpRequest object containing metadata about the user request.

        @variables:
          months - stores number of months for which the authorized user wants to generate worker report.
          toadys_date - stores current date.
          current_year - stores current year retrieved from 'todays_date'.
          current_month - stores current month retrieved from 'todays_date'.
          template - stores template returned by 'get_template' method.
          hall_caretakers - stores all hall caretakers.
          worker_report - stores 'WorkerReport' instances according to 'months'.

        """
        months = int(request.GET.get('months'))
        # print('~~~~month',months)
        todays_date = date.today()
        current_year = todays_date.year
        current_month = todays_date.month

        template = get_template('hostelmanagement/view_report.html')

        hall_caretakers = HallCaretaker.objects.all()
        get_hall = ""
        get_hall = get_caretaker_hall(hall_caretakers, request.user)
        # print('~~~~~ get_hall' , get_hall)
        # print('month<curr_mn~~~~~~~',months,current_month)
        
        if months < current_month:
            worker_report = WorkerReport.objects.filter(
                hall=get_hall,)
        else:
            worker_report = WorkerReport.objects.filter(Q(hall=get_hall, year=current_year, month__lte=current_month) | Q(
                hall=get_hall, year=current_year-1, month__gte=12-months+current_month))

        worker = {
            'worker_report': worker_report
        }
        html = template.render(worker)
        pdf = render_to_pdf('hostelmanagement/view_report.html', worker)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            filename = "Invoice_%s.pdf" % ("12341231")
            content = "inline; filename='%s'" % (filename)
            download = request.GET.get("download")
            if download:
                content = "attachment; filename='%s'" % (filename)
            response['Content-Disposition'] = content
            return response
        return HttpResponse("Not found")


def hostel_notice_board(request):
    notices = HostelNoticeBoard.objects.all().select_related('hall', 'posted_by')
    data = []
    for notice in notices:
        content_name = notice.content.name if notice.content else ''
        content_url = (
            request.build_absolute_uri(notice.content.url)
            if notice.content
            else ''
        )
        data.append(
            {
                'id': notice.id,
                'hall': notice.hall_id,
                'posted_by': notice.posted_by_id,
                'head_line': notice.head_line,
                'content': content_name,
                'content_url': content_url,
                'description': notice.description,
                'created_at': notice.created_at.isoformat() if notice.created_at else '',
                'updated_at': notice.updated_at.isoformat() if notice.updated_at else '',
            }
        )
    return JsonResponse(data, safe=False)


@login_required
def all_leave_data(request):
    try:
        # Assuming the user's profile is stored in extrainfo
        staff = request.user.extrainfo.id
    except AttributeError:
        staff = None

    accepts = request.headers.get('Accept', '')
    wants_json = (
        'application/json' in accepts
        or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or bool(request.headers.get('Authorization'))
    )

    if staff is not None and HallCaretaker.objects.filter(staff_id=staff).exists():
        all_leave = HostelLeave.objects.all()
        if wants_json:
            leave_data = list(
                all_leave.values(
                    'id',
                    'student_name',
                    'roll_num',
                    'reason',
                    'phone_number',
                    'start_date',
                    'end_date',
                    'status',
                    'remark',
                )
            )
            return JsonResponse({'leaves': leave_data}, status=200)

        return render(request, 'hostelmanagement/all_leave_data.html', {'all_leave': all_leave})
    else:
        if wants_json:
            return JsonResponse({'message': 'You are not authorized to access leave requests.'}, status=403)

        return HttpResponse('<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/"</script>')


@csrf_exempt
def create_hostel_leave(request):
    wants_json = (
        "application/json" in (request.headers.get("Accept") or "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or bool(request.headers.get("Authorization"))
    )

    user = request.user if request.user.is_authenticated else None
    if user is None and request.headers.get("Authorization"):
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.lower().startswith("token "):
            token_key = auth_header.split(" ", 1)[1].strip()
            token = Token.objects.select_related("user").filter(key=token_key).first()
            if token:
                user = token.user

    if user is None:
        if wants_json:
            return JsonResponse({"message": "Authentication required."}, status=401)
        return HttpResponse('<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/";</script>')

    if request.method == "GET":
        return render(request, "hostelmanagement/create_leave.html")
    if request.method != "POST":
        return JsonResponse({"message": "Only POST requests are allowed."}, status=405)

    if request.content_type and "application/json" in request.content_type:
        data = request.data or {}
    else:
        data = request.POST

    student_name = data.get("student_name")
    roll_num = data.get("roll_num")
    phone_number = data.get("phone_number")
    reason = data.get("reason")
    start_date = data.get("start_date", timezone.now())
    end_date = data.get("end_date")

    leave = HostelLeave.objects.create(
        student_name=student_name,
        roll_num=roll_num,
        phone_number=phone_number,
        reason=reason,
        start_date=start_date,
        end_date=end_date,
    )

    caretakers = HallCaretaker.objects.all()
    sender = user
    type = "leave_request"
    for caretaker in caretakers:
        try:
            hostel_notifications(sender, caretaker.staff.id.user, type)
        except Exception as e:
            print(f"Error sending notification to caretaker {caretaker.staff.user.username}: {e}")

    return JsonResponse({"message": "HostelLeave created successfully"}, status=status.HTTP_201_CREATED)

# hostel_complaints_list caretaker can see all hostel complaints

@login_required
def hostel_complaint_list(request):
    user_id = request.user.id

    try:
        # Assuming the user's profile is stored in extrainfo
        staff = request.user.extrainfo.id
    except AttributeError:
        staff = None

    if staff is not None and HallCaretaker.objects.filter(staff_id=staff).exists():
        complaints = HostelComplaint.objects.all()
        return render(request, 'hostelmanagement/hostel_complaint.html', {'complaints': complaints})
    else:
        return HttpResponse('<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/"</script>')


@login_required
def get_students(request):
    try:
        staff = request.user.extrainfo.id
        print(staff)
    except AttributeError:
        staff = None

    if HallCaretaker.objects.filter(staff_id=staff).exists():
        hall_id = HallCaretaker.objects.get(staff_id=staff).hall_id
        print(hall_id)
        hall_no = Hall.objects.get(id=hall_id)
        print(hall_no)
        student_details = StudentDetails.objects.filter(hall_id=hall_no)

        return render(request, 'hostelmanagement/student_details.html', {'students': student_details})

    elif HallWarden.objects.filter(faculty_id=staff).exists():
        hall_id = HallWarden.objects.get(faculty_id=staff).hall_id
        student_details = StudentDetails.objects.filter(hall_id=hall_no)

        return render(request, 'hostelmanagement/student_details.html', {'students': student_details})
    else:
        return HttpResponse('<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/"</script>')

# Student can post complaints


class PostComplaint(APIView):
    # Assuming you are using session authentication
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    # Allow only authenticated users to access the view
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = request.user.username
        complaints = HostelComplaint.objects.filter(
            Q(roll_number__iexact=user_id) | Q(student_name__iexact=user_id)
        )
        complaint_data = list(
            complaints.values(
                'id',
                'hall_name',
                'student_name',
                'roll_number',
                'category',
                'description',
                'contact_number',
                'image_upload',
                'status',
                'created_at',
                'updated_at',
            )
        )
        return JsonResponse({'complaints': complaint_data}, status=200)

    def post(self, request):
        hall_name = request.data.get('hall_name', 'N/A')
        roll_number = request.data.get('roll_number') or request.user.username
        category = request.data.get('category', 'General')
        description = request.data.get('description')
        contact_number = request.data.get('contact_number', '')
        image_upload = request.FILES.get('image_upload')

        if not description:
            return JsonResponse({'message': 'Description is required.'}, status=400)

        complaint = HostelComplaint.objects.create(
            hall_name=hall_name,
            student_name=request.user.username,
            roll_number=roll_number,
            category=category,
            description=description,
            contact_number=contact_number,
            image_upload=image_upload,
        )

        return JsonResponse(
            {
                'message': 'Complaint submitted successfully.',
                'complaint_id': complaint.id,
                'status': complaint.status,
                'created_at': complaint.created_at,
            },
            status=201,
        )


class StudentRoomChangeRequestView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_id = str(request.user)
        room_change_requests = HostelRoomChangeRequest.objects.filter(
            roll_num__iexact=user_id,
        ).order_by('-created_at')

        request_data = list(
            room_change_requests.values(
                'id',
                'student_name',
                'roll_num',
                'current_room',
                'preferred_room',
                'reason',
                'status',
                'created_at',
            )
        )
        return JsonResponse({'requests': request_data}, status=200)

    def post(self, request):
        current_room = request.data.get('current_room')
        preferred_room = request.data.get('preferred_room')
        reason = request.data.get('reason')

        if not current_room or not preferred_room or not reason:
            return JsonResponse(
                {'message': 'current_room, preferred_room and reason are required.'},
                status=400,
            )

        student = Student.objects.filter(id__user__username=request.user.username).first()
        if not student or not student.hall_no:
            return JsonResponse({'message': 'Student hall not found.'}, status=400)

        hall_id = f"hall{student.hall_no}"
        hall = Hall.objects.filter(hall_id__iexact=hall_id).first()
        if not hall:
            hall = Hall.objects.filter(hall_id__iexact=str(student.hall_no)).first()
        if not hall:
            hall = Hall.objects.filter(id=student.hall_no).first()
        if not hall:
            return JsonResponse({'message': 'Hall not found.'}, status=400)

        preferred_value = str(preferred_room).strip()
        if "-" not in preferred_value:
            return JsonResponse({'message': 'Preferred room format is invalid.'}, status=400)

        block_no, room_no = (part.strip() for part in preferred_value.split("-", 1))
        if not block_no or not room_no:
            return JsonResponse({'message': 'Preferred room format is invalid.'}, status=400)

        preferred_room_obj = HallRoom.objects.filter(
            hall=hall,
            block_no=block_no,
            room_no=room_no,
            room_cap__gt=F("room_occupied"),
        ).first()
        if not preferred_room_obj:
            return JsonResponse({'message': 'Preferred room is not available.'}, status=400)

        request_obj = HostelRoomChangeRequest.objects.create(
            student_name=request.user.username,
            roll_num=str(request.user),
            current_room=current_room,
            preferred_room=preferred_room,
            reason=reason,
        )

        return JsonResponse(
            {
                'message': 'Room change request submitted successfully.',
                'request_id': request_obj.id,
                'status': request_obj.status,
            },
            status=201,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def available_rooms_for_student_api(request):
    student = Student.objects.filter(id__user__username=request.user.username).first()
    if not student or not student.hall_no:
        return Response({"rooms": [], "message": "Student hall not found."}, status=status.HTTP_200_OK)

    hall_id = f"hall{student.hall_no}"
    hall = Hall.objects.filter(hall_id__iexact=hall_id).first()
    if not hall:
        hall = Hall.objects.filter(hall_id__iexact=str(student.hall_no)).first()
    if not hall:
        hall = Hall.objects.filter(id=student.hall_no).first()
    if not hall:
        return Response({"rooms": [], "message": "Hall not found."}, status=status.HTTP_200_OK)

    rooms = (
        HallRoom.objects.filter(hall=hall, room_cap__gt=F("room_occupied"))
        .order_by("block_no", "room_no")
    )

    data = []
    for room in rooms:
        label = f"{room.block_no}-{room.room_no}"
        data.append(
            {
                "value": label,
                "label": label,
                "block_no": room.block_no,
                "room_no": room.room_no,
                "room_cap": room.room_cap,
                "room_occupied": room.room_occupied,
            }
        )

    return Response({"hall_id": hall_id, "rooms": data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def room_change_requests_staff_api(request):
    """Caretaker/Warden: list room change requests for their hall (or all if superuser)."""

    if is_superuser(request.user):
        requests_qs = HostelRoomChangeRequest.objects.all().order_by("-created_at", "-id")
        data = [_serialize_room_change_request(req) for req in requests_qs]
        return Response({"success": True, "data": data}, status=status.HTTP_200_OK)

    assigned_hall = get_staff_assigned_hall(request.user)
    if not assigned_hall:
        return Response(
            {"success": False, "message": "You are not authorized to view room change requests"},
            status=status.HTTP_403_FORBIDDEN,
        )

    roll_nums = _room_change_roll_numbers_for_hall(assigned_hall)
    requests_qs = HostelRoomChangeRequest.objects.filter(roll_num__in=roll_nums).order_by(
        "-created_at", "-id"
    )
    data = [_serialize_room_change_request(req) for req in requests_qs]
    return Response({"success": True, "data": data}, status=status.HTTP_200_OK)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def room_change_request_status_api(request, id):
    """Caretaker/Warden: approve/reject a room change request."""

    try:
        request_id = int(id)
    except (TypeError, ValueError):
        return Response({"success": False, "message": "Invalid id"}, status=status.HTTP_400_BAD_REQUEST)

    req_obj = HostelRoomChangeRequest.objects.filter(id=request_id).first()
    if not req_obj:
        return Response({"success": False, "message": "Request not found"}, status=status.HTTP_404_NOT_FOUND)

    if not is_superuser(request.user) and not _is_warden(request.user):
        return Response(
            {"success": False, "message": "You are not authorized to update room change requests"},
            status=status.HTTP_403_FORBIDDEN,
        )

    assigned_hall = get_staff_assigned_hall(request.user)
    if assigned_hall:
        roll_nums = _room_change_roll_numbers_for_hall(assigned_hall)
        if req_obj.roll_num not in roll_nums:
            return Response(
                {"success": False, "message": "You are not authorized to update this request"},
                status=status.HTTP_403_FORBIDDEN,
            )

    status_raw = _room_change_status_normalize((request.data or {}).get("status"))
    if status_raw in {"approve", "approved"}:
        new_status = "approved"
    elif status_raw in {"reject", "rejected"}:
        new_status = "rejected"
    else:
        return Response({"success": False, "message": "Invalid status value"}, status=status.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        req_obj.status = new_status
        req_obj.save(update_fields=["status"])

        if new_status == "approved":
            student = Student.objects.filter(id__user__username=req_obj.roll_num).first()
            if student and student.hall_no:
                hall_id = f"hall{student.hall_no}"
                hall = Hall.objects.filter(hall_id__iexact=hall_id).first()
                if not hall:
                    hall = Hall.objects.filter(hall_id__iexact=str(student.hall_no)).first()
                if not hall:
                    hall = Hall.objects.filter(id=student.hall_no).first()

                preferred_value = str(req_obj.preferred_room or "").strip()
                if hall and "-" in preferred_value:
                    block_no, room_no = (
                        part.strip() for part in preferred_value.split("-", 1)
                    )
                    if block_no and room_no:
                        updated = HallRoom.objects.filter(
                            hall=hall,
                            block_no=block_no,
                            room_no=room_no,
                        ).update(room_occupied=F("room_occupied") + 1)

                        if updated:
                            student.room_no = preferred_value
                            student.save(update_fields=["room_no"])

    return Response(
        {"success": True, "message": "Status updated", "status": new_status},
        status=status.HTTP_200_OK,
    )


# // student can see his leave status

class my_leaves(View):
    @method_decorator(login_required, name='dispatch')
    def get(self, request, *args, **kwargs):
        try:
            # Get the user ID from the request's user
            user_id = str(request.user)

            # Retrieve leaves registered by the current student based on their roll number
            my_leaves = HostelLeave.objects.filter(roll_num__iexact=user_id)
            # Construct the context to pass to the template
            context = {
                'leaves': my_leaves
            }

            accepts = request.headers.get('Accept', '')
            wants_json = (
                'application/json' in accepts
                or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                or bool(request.headers.get('Authorization'))
            )

            if wants_json:
                leave_data = list(
                    my_leaves.values(
                        'id',
                        'student_name',
                        'roll_num',
                        'reason',
                        'phone_number',
                        'start_date',
                        'end_date',
                        'status',
                        'remark',
                        'file_upload',
                    )
                )
                return JsonResponse({'leaves': leave_data}, status=200)

            # Render the template with the context data
            return render(request, 'hostelmanagement/my_leaves.html', context)

        except User.DoesNotExist:
            # Handle the case where the user with the given ID doesn't exist
            return HttpResponse(f"User with ID {user_id} does not exist.")


class HallIdView(APIView):
    authentication_classes = []  # Allow public access for testing
    permission_classes = []  # Allow any user to access the view

    def get(self, request, *args, **kwargs):
        hall_id = HostelAllotment.objects.values('hall_id')
        return Response(hall_id, status=status.HTTP_200_OK)


@login_required(login_url=LOGIN_URL)
def logout_view(request):
    logout(request)
    return redirect("/")


@method_decorator(user_passes_test(is_superuser), name='dispatch')
class AssignCaretakerView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    template_name = 'hostelmanagement/assign_caretaker.html'

    def get(self, request, *args, **kwargs):
        hall = Hall.objects.all()
        caretaker_usernames = Staff.objects.all()
        return render(request, self.template_name, {'halls': hall, 'caretaker_usernames': caretaker_usernames})

    def post(self, request, *args, **kwargs):
        hall_id = request.data.get('hall_id')
        caretaker_username = request.data.get('caretaker_username')

        try:
            hall = Hall.objects.get(hall_id=hall_id)
            caretaker_staff = Staff.objects.get(
                id__user__username=caretaker_username)

            # Retrieve the previous caretaker for the hall, if any
            prev_hall_caretaker = HallCaretaker.objects.filter(hall=hall).first()
            # print(prev_hall_caretaker.staff.id)
            # Delete any previous assignments of the caretaker in HallCaretaker table
            HallCaretaker.objects.filter(staff=caretaker_staff).delete()

            # Delete any previous assignments of the caretaker in HostelAllotment table
            HostelAllotment.objects.filter(
                assignedCaretaker=caretaker_staff).delete()

            # Delete any previously assigned caretaker to the same hall
            HallCaretaker.objects.filter(hall=hall).delete()

            # Assign the new caretaker to the hall in HallCaretaker table
            hall_caretaker = HallCaretaker.objects.create(
                hall=hall, staff=caretaker_staff)

            # # Update the assigned caretaker in Hostelallottment table
            hostel_allotments = HostelAllotment.objects.filter(hall=hall)
            for hostel_allotment in hostel_allotments:
                hostel_allotment.assignedCaretaker = caretaker_staff
                hostel_allotment.save()

            # Retrieve the current warden for the hall
            current_warden = HallWarden.objects.filter(hall=hall).first()

            try:
                history_entry = HostelTransactionHistory.objects.create(
                    hall=hall,
                    change_type='Caretaker',
                    previous_value= prev_hall_caretaker.staff.id if (prev_hall_caretaker and prev_hall_caretaker.staff) else 'None',
                    new_value=caretaker_username
                )
            except Exception as e:
                print("Error creating HostelTransactionHistory:", e)

            
            # Create hostel history
            try:
                HostelHistory.objects.create(
                    hall=hall,
                    caretaker=caretaker_staff,
                    batch=hall.assigned_batch,
                    warden=current_warden.faculty if( current_warden and current_warden.faculty) else None
                )
            except Exception as e:
                print ("Error creating history",e)
            return Response({'message': f'Caretaker {caretaker_username} assigned to Hall {hall_id} successfully'}, status=status.HTTP_201_CREATED)

        except Hall.DoesNotExist:
            return Response({'error': f'Hall with ID {hall_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        except Staff.DoesNotExist:
            return Response({'error': f'Caretaker with username {caretaker_username} not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)



@method_decorator(user_passes_test(is_superuser), name='dispatch')
class AssignBatchView(View):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    # Assuming the HTML file is directly in the 'templates' folder
    template_name = 'hostelmanagement/assign_batch.html'

    def get(self, request, *args, **kwargs):
        hall = Hall.objects.all()
        return render(request, self.template_name, {'halls': hall})

    def update_student_hall_allotment(self, hall, assigned_batch):
        hall_number = int(''.join(filter(str.isdigit, hall.hall_id)))
        students = Student.objects.filter(batch=int(assigned_batch))
       
        
        for student in students:
            student.hall_no = hall_number
            student.save()
            

    def post(self, request, *args, **kwargs):
        try:
            with transaction.atomic():  # Start a database transaction

                data = json.loads(request.body.decode('utf-8'))
                hall_id = data.get('hall_id')

                hall = Hall.objects.get(hall_id=hall_id)
                # previous_batch = hall.assigned_batch  # Get the previous batch
                previous_batch = hall.assigned_batch if hall.assigned_batch is not None else 0  # Get the previous batch
                hall.assigned_batch = data.get('batch')
                hall.save()

                

                
            
                # Update the assignedBatch field in HostelAllotment table for the corresponding hall
                room_allotments = HostelAllotment.objects.filter(hall=hall)
                for room_allotment in room_allotments:
                    room_allotment.assignedBatch = hall.assigned_batch
                    room_allotment.save()
                
                # retrieve the current caretaker and current warden for the hall
                current_caretaker =HallCaretaker.objects.filter(hall=hall).first()
                current_warden = HallWarden.objects.filter(hall=hall).first()

                # Record the transaction history
                HostelTransactionHistory.objects.create(
                    hall=hall,
                    change_type='Batch',
                    previous_value=previous_batch,
                    new_value=hall.assigned_batch
                )

                # Create hostel history
                try:
                    HostelHistory.objects.create(
                        hall=hall,
                        caretaker=current_caretaker.staff if (current_caretaker and current_caretaker.staff) else None,
                        
                        batch=hall.assigned_batch,
                        warden=current_warden.faculty if( current_warden and current_warden.faculty) else None

                    )
                except Exception as e:
                    print ("Error creating history",e)

                self.update_student_hall_allotment(hall, hall.assigned_batch)
                print("batch assigned successssssssssssssssssss")
                messages.success(request, 'batch assigned succesfully')
                
                return JsonResponse({'status': 'success', 'message': 'Batch assigned successfully'}, status=200)

        except Hall.DoesNotExist:
            return JsonResponse({'status': 'error', 'error': f'Hall with ID {hall_id} not found'}, status=404)

        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)

    def test_func(self):
        # Check if the user is a superuser
        return self.request.user.is_superuser


@method_decorator(user_passes_test(is_superuser), name='dispatch')
class AssignWardenView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    template_name = 'hostelmanagement/assign_warden.html'

    def post(self, request, *args, **kwargs):
        hall_id = request.data.get('hall_id')
        warden_id = request.data.get('warden_id')
        try:
            hall = Hall.objects.get(hall_id=hall_id)
            warden = Faculty.objects.get(id__user__username=warden_id)

            # Retrieve the previous caretaker for the hall, if any
            prev_hall_warden = HallWarden.objects.filter(hall=hall).first()
           
            # Delete any previous assignments of the warden in Hallwarden table
            HallWarden.objects.filter(faculty=warden).delete()

            # Delete any previous assignments of the warden in HostelAllotment table
            HostelAllotment.objects.filter(assignedWarden=warden).delete()

            # Delete any previously assigned warden to the same hall
            HallWarden.objects.filter(hall=hall).delete()

            # Assign the new warden to the hall in Hallwarden table
            hall_warden = HallWarden.objects.create(hall=hall, faculty=warden)

            #current caretker
            current_caretaker =HallCaretaker.objects.filter(hall=hall).first()
            print(current_caretaker)
            
            # Update the assigned warden in Hostelallottment table
            hostel_allotments = HostelAllotment.objects.filter(hall=hall)
            for hostel_allotment in hostel_allotments:
                hostel_allotment.assignedWarden = warden
                hostel_allotment.save()

            try:
                history_entry = HostelTransactionHistory.objects.create(
                    hall=hall,
                    change_type='Warden',
                    previous_value= prev_hall_warden.faculty.id if (prev_hall_warden and prev_hall_warden.faculty) else 'None',
                    new_value=warden
                )
            except Exception as e:
                print("Error creating HostelTransactionHistory:", e)


            # Create hostel history
            try:
                HostelHistory.objects.create(
                    hall=hall,
                    caretaker=current_caretaker.staff if (current_caretaker and current_caretaker.staff) else None,
                    
                    batch=hall.assigned_batch,
                    warden=warden
                )
            except Exception as e:
                print ("Error creating history",e)


            return Response({'message': f'Warden {warden_id} assigned to Hall {hall_id} successfully'}, status=status.HTTP_201_CREATED)

        except Hall.DoesNotExist:
            return Response({'error': f'Hall with ID {hall_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        except Faculty.DoesNotExist:
            return Response({'error': f'Warden with username {warden_id} not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return JsonResponse({'status': 'error', 'error': str(e)}, status=500)


@method_decorator(user_passes_test(is_superuser), name='dispatch')
class AddHostelView(View):
    template_name = 'hostelmanagement/add_hostel.html'

    def get(self, request, *args, **kwargs):
        form = HallForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        form = HallForm(request.POST)
        if form.is_valid():
            hall_id = form.cleaned_data['hall_id']

            # # Check if a hall with the given hall_id already exists
            # if Hall.objects.filter(hall_id=hall_id).exists():
            #     messages.error(request, f'Hall with ID {hall_id} already exists.')
            #     return redirect('hostelmanagement:add_hostel')

            # Check if a hall with the given hall_id already exists
            if Hall.objects.filter(hall_id=hall_id).exists():
                error_message = f'Hall with ID {hall_id} already exists.'

                return HttpResponse(error_message, status=400)

            # If not, create a new hall
            form.save()
            messages.success(request, 'Hall added successfully!')
            # Redirect to the view showing all hostels
            return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))
            # return render(request, 'hostelmanagement/admin_hostel_list.html')

        # If form is not valid, render the form with errors
        return render(request, self.template_name, {'form': form})


class CheckHallExistsView(View):

    def get(self, request, *args, **kwargs):

        hall_id = request.GET.get('hall_id')
        try:
            hall = Hall.objects.get(hall_id=hall_id)
            exists = True
        except Hall.DoesNotExist:
            exists = False
        messages.MessageFailure(request, f'Hall {hall_id} already exist.')
        return JsonResponse({'exists': exists})


@method_decorator(user_passes_test(is_superuser), name='dispatch')
class AdminHostelListView(View):
    template_name = 'hostelmanagement/admin_hostel_list.html'

    def get(self, request, *args, **kwargs):
        halls = Hall.objects.all()
        # Create a list to store additional details
        hostel_details = []

        # Loop through each hall and fetch assignedCaretaker and assignedWarden
        for hall in halls:
            try:
                caretaker = HallCaretaker.objects.filter(hall=hall).first()
                warden = HallWarden.objects.filter(hall=hall).first()
            except HostelAllotment.DoesNotExist:
                assigned_caretaker = None
                assigned_warden = None

            hostel_detail = {
                'hall_id': hall.hall_id,
                'hall_name': hall.hall_name,
                'max_accomodation': hall.max_accomodation,
                'number_students': hall.number_students,
                'assigned_batch': hall.assigned_batch,
                'assigned_caretaker': caretaker.staff.id.user.username if caretaker else None,
                'assigned_warden': warden.faculty.id.user.username if warden else None,
            }

            hostel_details.append(hostel_detail)

        return render(request, self.template_name, {'hostel_details': hostel_details})


@method_decorator(user_passes_test(is_superuser), name='dispatch')
class AdminRoomAllocationDataView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        students = Student.objects.select_related('id__user').order_by('id__user__username')
        available_rooms = HallRoom.objects.select_related('hall').filter(room_occupied__lt=F('room_cap')).order_by('hall__hall_id', 'block_no', 'room_no')

        student_data = [
            {
                'student_id': student.id.user.username,
                'name': f"{student.id.user.first_name} {student.id.user.last_name}".strip() or student.id.user.username,
                'hall_no': student.hall_no,
                'room_no': student.room_no,
            }
            for student in students
        ]

        room_data = [
            {
                'room_id': room.id,
                'hall_id': room.hall.hall_id,
                'hall_name': room.hall.hall_name,
                'block_no': room.block_no,
                'room_no': room.room_no,
                'room_cap': room.room_cap,
                'room_occupied': room.room_occupied,
                'available_slots': max(room.room_cap - room.room_occupied, 0),
            }
            for room in available_rooms
        ]

        return Response({'students': student_data, 'available_rooms': room_data}, status=status.HTTP_200_OK)


@method_decorator(user_passes_test(is_superuser), name='dispatch')
class AdminAssignRoomView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        student_id = request.data.get('student_id')
        room_id = request.data.get('room_id')

        if not student_id or not room_id:
            return Response({'message': 'student_id and room_id are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.select_related('id__user').get(id__user__username=student_id)
        except Student.DoesNotExist:
            return Response({'message': 'Student not found.'}, status=status.HTTP_404_NOT_FOUND)

        if student.hall_no not in [0, None] or student.room_no:
            return Response({'message': 'Student is already allocated to a room.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                room = HallRoom.objects.select_for_update().select_related('hall').get(id=room_id)

                if room.room_occupied >= room.room_cap:
                    return Response({'message': 'Selected room is already full. Please choose another room.'}, status=status.HTTP_400_BAD_REQUEST)

                room.room_occupied = room.room_occupied + 1
                room.save(update_fields=['room_occupied'])

                hall_digits = ''.join(filter(str.isdigit, room.hall.hall_id))
                student.hall_no = int(hall_digits) if hall_digits else 0
                student.room_no = f"{room.block_no}{room.room_no}"
                student.save(update_fields=['hall_no', 'room_no'])

            return Response(
                {
                    'message': 'Room assigned successfully.',
                    'student_id': student_id,
                    'room': {
                        'hall_id': room.hall.hall_id,
                        'block_no': room.block_no,
                        'room_no': room.room_no,
                    },
                },
                status=status.HTTP_200_OK,
            )
        except HallRoom.DoesNotExist:
            return Response({'message': 'Room not found.'}, status=status.HTTP_404_NOT_FOUND)


@method_decorator(user_passes_test(is_superuser), name='dispatch')
class DeleteHostelView(View):
    def get(self, request, hall_id, *args, **kwargs):
        # Get the hall instance
        hall = get_object_or_404(Hall, hall_id=hall_id)

        # Delete related entries in other tables
        hostelallotments = HostelAllotment.objects.filter(hall=hall)
        hostelallotments.delete()

        # Delete the hall
        hall.delete()
        messages.success(request, f'Hall {hall_id} deleted successfully.')

        return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


class HallIdView(APIView):
    authentication_classes = []  # Allow public access for testing
    permission_classes = []  # Allow any user to access the view

    def get(self, request, *args, **kwargs):
        hall_id = HostelAllotment.objects.values('hall_id')
        return Response(hall_id, status=status.HTTP_200_OK)


@login_required(login_url=LOGIN_URL)
def logout_view(request):
    logout(request)
    return redirect("/")


# //! alloted_rooms
def alloted_rooms(request, hall_id):
    """
    This function returns the allotted rooms in a particular hall.

    @param:
      request - HttpRequest object containing metadata about the user request.
      hall_id - Hall ID for which the allotted rooms need to be retrieved.

    @variables:
      allotted_rooms - stores all the rooms allotted in the given hall.
    """
    # Query the hall by hall_id
    hall = Hall.objects.get(hall_id=hall_id)
    # Query all rooms allotted in the given hall
    allotted_rooms = HallRoom.objects.filter(hall=hall, room_occupied__gt=0)
    # Prepare a list of room details to be returned
    room_details = []
    for room in allotted_rooms:
        room_details.append({
            'hall': room.hall.hall_id,
            'room_no': room.room_no,
            'block_no': room.block_no,
            'room_cap': room.room_cap,
            'room_occupied': room.room_occupied
        })
    return JsonResponse(room_details, safe=False)


def alloted_rooms_main(request):
    """
    This function returns the allotted rooms in all halls.

    @param:
      request - HttpRequest object containing metadata about the user request.

    @variables:
      all_halls - stores all the halls.
      all_rooms - stores all the rooms allotted in all halls.
    """
    # Query all halls
    all_halls = Hall.objects.all()

    # Query all rooms allotted in all halls
    all_rooms = []
    for hall in all_halls:
        all_rooms.append(HallRoom.objects.filter(
            hall=hall, room_occupied__gt=0))

    # Prepare a list of room details to be returned
    room_details = []
    for rooms in all_rooms:
        for room in rooms:
            room_details.append({
                'hall': room.hall.hall_name,
                'room_no': room.room_no,
                'block_no': room.block_no,
                'room_cap': room.room_cap,
                'room_occupied': room.room_occupied
            })

    # Return the room_details as JSON response
    return render(request, 'hostelmanagement/alloted_rooms_main.html', {'allotted_rooms': room_details, 'halls': all_halls})


# //! all_staff
def all_staff(request, hall_id):
    """
    This function returns all staff information for a specific hall.

    @param:
      request - HttpRequest object containing metadata about the user request.
      hall_id - The ID of the hall for which staff information is requested.


    @variables:
      all_staff - stores all staff information for the specified hall.
    """

    # Query all staff information for the specified hall
    all_staff = StaffSchedule.objects.filter(hall_id=hall_id)

    # Prepare a list of staff details to be returned
    staff_details = []
    for staff in all_staff:
        staff_details.append({
            'type': staff.staff_type,
            'staff_id': staff.staff_id_id,
            'hall_id': staff.hall_id,
            'day': staff.day,
            'start_time': staff.start_time,
            'end_time': staff.end_time
        })

    # Return the staff_details as JSON response
    return JsonResponse(staff_details, safe=False)


# //! Edit Stuff schedule
class StaffScheduleView(APIView):
    """
    API endpoint for creating or editing staff schedules.
    """

    authentication_classes = []  # Allow public access for testing
    permission_classes = []  # Allow any user to access the view

    def patch(self, request, staff_id):
        staff = get_object_or_404(Staff, pk=staff_id)
        staff_type = request.data.get('staff_type')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        day = request.data.get('day')


        if start_time and end_time and day and staff_type:
            # Check if staff schedule exists for the given day
            existing_schedule = StaffSchedule.objects.filter(
                staff_id=staff_id).first()
            if existing_schedule:
                existing_schedule.start_time = start_time
                existing_schedule.end_time = end_time
                existing_schedule.day = day
                existing_schedule.staff_type = staff_type
                existing_schedule.save()
                return Response({"message": "Staff schedule updated successfully."}, status=status.HTTP_200_OK)
            else:
                # If staff schedule doesn't exist for the given day, return 404
                return Response({"error": "Staff schedule does not exist for the given day."}, status=status.HTTP_404_NOT_FOUND)

        return Response({"error": "Please provide start_time, end_time, and day."}, status=status.HTTP_400_BAD_REQUEST)


# //! Hostel Inventory

@login_required
def get_inventory_form(request):
    user_id = request.user
    # print("user_id",user_id)
    staff = user_id.extrainfo.id
    # print("staff",staff)

    # Check if the user is present in the HallCaretaker table
    if HallCaretaker.objects.filter(staff_id=staff).exists():
        # If the user is a caretaker, allow access
        halls = Hall.objects.all()
        return render(request, 'hostelmanagement/inventory_form.html', {'halls': halls})
    else:
        # If the user is not a caretaker, redirect to the login page
        # return redirect('login')  # Adjust 'login' to your login URL name
        return HttpResponse(f'<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/"</script>')


@login_required
def edit_inventory(request, inventory_id):
    # Retrieve hostel inventory object
    inventory = get_object_or_404(HostelInventory, pk=inventory_id)

    # Check if the user is a caretaker
    user_id = request.user
    staff_id = user_id.extrainfo.id

    if HallCaretaker.objects.filter(staff_id=staff_id).exists():
        halls = Hall.objects.all()

        # Prepare inventory data for rendering
        inventory_data = {
            'inventory_id': inventory.inventory_id,
            'hall_id': inventory.hall_id,
            'inventory_name': inventory.inventory_name,
            'cost': str(inventory.cost),  # Convert DecimalField to string
            'quantity': inventory.quantity,
        }

        # Render the inventory update form with inventory data
        return render(request, 'hostelmanagement/inventory_update_form.html', {'inventory': inventory_data, 'halls': halls})
    else:
        # If the user is not a caretaker, show a message and redirect
        return HttpResponse('<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/"</script>')


class HostelInventoryUpdateView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, inventory_id):
        user_id = request.user
        staff_id = user_id.extrainfo.id

        if not HallCaretaker.objects.filter(staff_id=staff_id).exists():
            return Response({'error': 'You are not authorized to update this hostel inventory'}, status=status.HTTP_401_UNAUTHORIZED)

        hall_id = request.data.get('hall_id')
        inventory_name = request.data.get('inventory_name')
        cost = request.data.get('cost')
        quantity = request.data.get('quantity')

        # Validate required fields
        if not all([hall_id, inventory_name, cost, quantity]):
            return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve hostel inventory object
        hostel_inventory = get_object_or_404(HostelInventory, pk=inventory_id)

        # Update hostel inventory object
        hostel_inventory.hall_id = hall_id
        hostel_inventory.inventory_name = inventory_name
        hostel_inventory.cost = cost
        hostel_inventory.quantity = quantity
        hostel_inventory.save()

        # Return success response
        return Response({'message': 'Hostel inventory updated successfully'}, status=status.HTTP_200_OK)


class HostelInventoryView(APIView):
    """
    API endpoint for CRUD operations on hostel inventory.
    """
    # permission_classes = [IsAuthenticated]

    # authentication_classes = []  # Allow public access for testing
    # permission_classes = []  # Allow any user to access the view

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get(self, request, hall_id):
        user_id = request.user
        staff_id = user_id.extrainfo.id

        if not HallCaretaker.objects.filter(staff_id=staff_id).exists():
            return HttpResponse('<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/"</script>')

        # Retrieve hostel inventory objects for the given hall ID
        inventories = HostelInventory.objects.filter(hall_id=hall_id)

        # Get all hall IDs
        halls = Hall.objects.all()

        # Serialize inventory data
        inventory_data = []
        for inventory in inventories:
            inventory_data.append({
                'inventory_id': inventory.inventory_id,
                'hall_id': inventory.hall_id,
                'inventory_name': inventory.inventory_name,
                'cost': str(inventory.cost),  # Convert DecimalField to string
                'quantity': inventory.quantity,
            })

        inventory_data.sort(key=lambda x: x['inventory_id'])

        # Return inventory data as JSON response
        return render(request, 'hostelmanagement/inventory_list.html', {'halls': halls, 'inventories': inventory_data})

    def post(self, request):
        user_id = request.user
        staff_id = user_id.extrainfo.id

        if not HallCaretaker.objects.filter(staff_id=staff_id).exists():
            return Response({'error': 'You are not authorized to create a new hostel inventory'}, status=status.HTTP_401_UNAUTHORIZED)

        # Extract data from request
        hall_id = request.data.get('hall_id')
        inventory_name = request.data.get('inventory_name')
        cost = request.data.get('cost')
        quantity = request.data.get('quantity')

        # Validate required fields
        if not all([hall_id, inventory_name, cost, quantity]):
            return Response({'error': 'All fields are required'}, status=status.HTTP_400_BAD_REQUEST)

        # Create hostel inventory object
        try:
            hostel_inventory = HostelInventory.objects.create(
                hall_id=hall_id,
                inventory_name=inventory_name,
                cost=cost,
                quantity=quantity
            )
            return Response({'message': 'Hostel inventory created successfully', 'hall_id': hall_id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def delete(self, request, inventory_id):
        user_id = request.user
        staff_id = user_id.extrainfo.id

        if not HallCaretaker.objects.filter(staff_id=staff_id).exists():
            return Response({'error': 'You are not authorized to delete this hostel inventory'}, status=status.HTTP_401_UNAUTHORIZED)

        inventory = get_object_or_404(HostelInventory, pk=inventory_id)
        inventory.delete()
        return Response({'message': 'Hostel inventory deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


def update_allotment(request, pk):
    if request.method == 'POST':
        try:
            allotment = HostelAllotment.objects.get(pk=pk)
        except HostelAllotment.DoesNotExist:
            return JsonResponse({'error': 'HostelAllotment not found'}, status=404)

        try:
            allotment.assignedWarden = Faculty.objects.get(
                id=request.POST['warden_id'])
            allotment.assignedCaretaker = Staff.objects.get(
                id=request.POST['caretaker_id'])
            allotment.assignedBatch = request.POST.get(
                'student_batch', allotment.assignedBatch)
            allotment.save()
            return JsonResponse({'success': 'HostelAllotment updated successfully'})
        except (Faculty.DoesNotExist, Staff.DoesNotExist, IntegrityError):
            return JsonResponse({'error': 'Invalid data or integrity error'}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


@login_required
def request_guest_room(request):
    """
    This function is used by the student to book a guest room.
    @param:
      request - HttpRequest object containing metadata about the user request.
    """
    if request.method == "POST":
        form = GuestRoomBookingForm(request.POST)

        if form.is_valid():
            # print("Inside valid")
            hall = form.cleaned_data['hall']
            guest_name = form.cleaned_data['guest_name']
            guest_phone = form.cleaned_data['guest_phone']
            guest_email = form.cleaned_data['guest_email']
            guest_address = form.cleaned_data['guest_address']
            rooms_required = form.cleaned_data['rooms_required']
            total_guest = form.cleaned_data['total_guest']
            purpose = form.cleaned_data['purpose']
            arrival_date = form.cleaned_data['arrival_date']
            arrival_time = form.cleaned_data['arrival_time']
            departure_date = form.cleaned_data['departure_date']
            departure_time = form.cleaned_data['departure_time']
            nationality = form.cleaned_data['nationality']
            room_type = form.cleaned_data['room_type']  # Add room type


            max_guests = {
                'single': 1,
                'double': 2,
                'triple': 3,
            }
            # Fetch available room count based on room type and hall
            available_rooms_count = GuestRoom.objects.filter(
                hall=hall, room_type=room_type, vacant=True
            ).count()
            
             # Check if there are enough available rooms
            if available_rooms_count < rooms_required:
                messages.error(request, "Not enough available rooms.")
                return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))
            
            # Check if the number of guests exceeds the capacity of selected rooms
            if total_guest > rooms_required * max_guests.get(room_type, 1):
                messages.error(request, "Number of guests exceeds the capacity of selected rooms.")
                return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))
            

            newBooking = GuestRoomBooking.objects.create(hall=hall, intender=request.user, guest_name=guest_name, guest_address=guest_address,
                                                         guest_phone=guest_phone, guest_email=guest_email, rooms_required=rooms_required, total_guest=total_guest, purpose=purpose,
                                                         arrival_date=arrival_date, arrival_time=arrival_time, departure_date=departure_date, departure_time=departure_time, nationality=nationality,room_type=room_type)
            newBooking.save()
            messages.success(request, "Room request submitted successfully!")

            
            # Get the caretaker for the selected hall
            hall_caretaker = HallCaretaker.objects.get(hall=hall)
            caretaker = hall_caretaker.staff.id.user
            # Send notification to caretaker
            hostel_notifications(sender=request.user, recipient=caretaker, type='guestRoom_request')

            return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))
        else:
            messages.error(request, "Something went wrong")
            return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


@login_required
def update_guest_room(request):
    if request.method == "POST":
        if 'accept_request' in request.POST:
            status = request.POST['status']
            guest_room_request = GuestRoomBooking.objects.get(
                pk=request.POST['accept_request'])
            guest_room_instance = GuestRoom.objects.get(
                hall=guest_room_request.hall, room=request.POST['guest_room_id'])

            # Assign the guest room ID to guest_room_id field
            guest_room_request.guest_room_id = str(guest_room_instance.id)

            # Update the assigned guest room's occupancy details
            guest_room_instance.occupied_till = guest_room_request.departure_date
            guest_room_instance.vacant = False  # Mark the room as occupied
            guest_room_instance.save()

            # Update the occupied_till field of the room_booked
            room_booked = GuestRoom.objects.get(
                hall=guest_room_request.hall, room=request.POST['guest_room_id'])
            room_booked.occupied_till = guest_room_request.departure_date
            room_booked.save()

            # Save the guest room request after updating the fields
            guest_room_request.status = status
            guest_room_request.save()
            messages.success(request, "Request accepted successfully!")

            hostel_notifications(sender=request.user,recipient=guest_room_request.intender,type='guestRoom_accept')


        elif 'reject_request' in request.POST:
            guest_room_request = GuestRoomBooking.objects.get(
                pk=request.POST['reject_request'])
            guest_room_request.status = 'Rejected'
            guest_room_request.save()

            messages.success(request, "Request rejected successfully!")

            hostel_notifications(sender=request.user,recipient=guest_room_request.intender,type='guestRoom_reject')

        else:
            messages.error(request, "Invalid request!")
    return HttpResponseRedirect(reverse("hostelmanagement:hostel_view"))


def available_guestrooms_api(request):
    if request.method == 'GET':
        
        hall_id = request.GET.get('hall_id')
        room_type = request.GET.get('room_type')

        if hall_id and room_type:
            available_rooms_count = GuestRoom.objects.filter(hall_id=hall_id, room_type=room_type, vacant=True).count()
            return JsonResponse({'available_rooms_count': available_rooms_count})

    return JsonResponse({'error': 'Invalid request'}, status=400)


# //Caretaker can approve or reject leave applied by the student
@csrf_exempt
def update_leave_status(request):
    if request.method == 'POST':
        if request.content_type and 'application/json' in request.content_type:
            payload = json.loads(request.body.decode('utf-8') or '{}')
            leave_id = payload.get('leave_id')
            leave_status = payload.get('status')
            remark = payload.get('remark')
        else:
            leave_id = request.POST.get('leave_id')
            leave_status = request.POST.get('status')
            remark = request.POST.get('remark')

        if not leave_id or not leave_status:
            return JsonResponse({'status': 'error', 'message': 'leave_id and status are required.'}, status=400)

        normalized_status = str(leave_status).strip().lower()
        if normalized_status in ['approve', 'approved']:
            normalized_status = 'approved'
        elif normalized_status in ['reject', 'rejected']:
            normalized_status = 'rejected'
        elif normalized_status == 'pending':
            normalized_status = 'pending'
        else:
            return JsonResponse({'status': 'error', 'message': 'Invalid status value.'}, status=400)

        try:
            leave = HostelLeave.objects.get(id=leave_id)
            leave.status = normalized_status
            leave.remark = remark
            leave.save()

            # Send notification to the student
            sender = request.user  # Assuming request.user is the caretaker
            
            student_id = leave.roll_num  # Assuming student is a foreign key field in HostelLeave model
            recipient = User.objects.get(username=student_id)
            type = "leave_accept" if normalized_status == "approved" else "leave_reject"
            hostel_notifications(sender, recipient, type)

            return JsonResponse({'status': 'success', 'leave_status': leave.status, 'remarks': leave.remark, 'message': 'Leave status updated successfully.'})
        except HostelLeave.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Leave not found.'}, status=404)
    else:
        return JsonResponse({'status': 'error', 'message': 'Only POST requests are allowed.'}, status=405)


# //! Manage Fine
# //! Add Fine Functionality


@login_required
def show_fine_edit_form(request,fine_id):
    user_id = request.user
    staff = user_id.extrainfo.id
    caretaker = HallCaretaker.objects.get(staff_id=staff)
    hall_id = caretaker.hall_id

    fine = HostelFine.objects.filter(fine_id=fine_id)



    return render(request, 'hostelmanagement/impose_fine_edit.html', {'fines': fine[0]})

@login_required
def update_student_fine(request,fine_id):
    if request.method == 'POST':
        fine = HostelFine.objects.get(fine_id=fine_id)
        print("------------------------------------------------")
        print(request.POST)
        fine.amount = request.POST.get('amount')
        fine.status = request.POST.get('status')
        fine.reason = request.POST.get('reason')
        fine.save()
        
        return HttpResponse({'message': 'Fine has edited successfully'}, status=status.HTTP_200_OK)


@login_required
def impose_fine_view(request):
    user_id = request.user
    staff = user_id.extrainfo.id
    students = Student.objects.all()

    if HallCaretaker.objects.filter(staff_id=staff).exists():
        return render(request, 'hostelmanagement/impose_fine.html', {'students': students})

    return HttpResponse(f'<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/"</script>')


class HostelFineView(APIView):
    """
    API endpoint for imposing fines on students.
    """
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request):
        # Check if the user is a caretaker
        user_id = request.user
        staff = user_id.extrainfo.id

        try:
            caretaker = HallCaretaker.objects.get(staff_id=staff)
        except HallCaretaker.DoesNotExist:
            return HttpResponse(f'<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/"</script>')

        hall_id = caretaker.hall_id

        # Extract data from the request
        student_id = request.data.get('student_id')
        student_name = request.data.get('student_fine_name')
        amount = request.data.get('amount')
        reason = request.data.get('reason')

        # Validate the data
        if not all([student_id, student_name, amount, reason]):
            return HttpResponse({'error': 'Incomplete data provided.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create the HostelFine object
        try:
            fine = HostelFine.objects.create(
                student_id=student_id,
                student_name=student_name,
                amount=amount,
                reason=reason,
                hall_id=hall_id
            )
            # Sending notification to the student about the imposed fine
           
            
            
            recipient = User.objects.get(username=student_id)
            
            sender = request.user
            
            type = "fine_imposed"
            hostel_notifications(sender, recipient, type)

            return HttpResponse({'message': 'Fine imposed successfully.'}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required
def get_student_name(request, username):
    try:
        user = User.objects.get(username=username)
        full_name = f"{user.first_name} {user.last_name}" if user.first_name or user.last_name else ""
        return JsonResponse({"name": full_name})
    except User.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)


@login_required
def hostel_fine_list(request):
    user_id = request.user
    staff = user_id.extrainfo.id
    caretaker = HallCaretaker.objects.get(staff_id=staff)
    hall_id = caretaker.hall_id
    hostel_fines = HostelFine.objects.filter(
        hall_id=hall_id).order_by('fine_id')

    if HallCaretaker.objects.filter(staff_id=staff).exists():
        return render(request, 'hostelmanagement/hostel_fine_list.html', {'hostel_fines': hostel_fines})

    return HttpResponse(f'<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/"</script>')


def student_fine_details(request):
    wants_json = (
        "application/json" in (request.headers.get("Accept") or "")
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or bool(request.headers.get("Authorization"))
    )

    user = request.user if request.user.is_authenticated else None
    if user is None and request.headers.get("Authorization"):
        auth_header = request.headers.get("Authorization") or ""
        if auth_header.lower().startswith("token "):
            token_key = auth_header.split(" ", 1)[1].strip()
            token = Token.objects.select_related("user").filter(key=token_key).first()
            if token:
                user = token.user

    if user is None:
        if wants_json:
            return JsonResponse({"message": "Authentication required."}, status=401)
        return HttpResponse('<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/";</script>')

    user_id = user.username
    # print(user_id)
    # staff=user_id.extrainfo.id

    # Check if the user_id exists in the Student table
    # if HallCaretaker.objects.filter(staff_id=staff).exists():
    #     return HttpResponse('<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/";</script>')

    if not Student.objects.filter(id_id=user_id).exists():
        if wants_json:
            return JsonResponse({"message": "You are not authorized to access this page."}, status=403)
        return HttpResponse('<script>alert("You are not authorized to access this page"); window.location.href = "/hostelmanagement/";</script>')

    # # Check if the user_id exists in the HostelFine table
    if not HostelFine.objects.filter(student_id=user_id).exists():
        if wants_json:
            return JsonResponse({"message": "There is no fine imposed on you."}, status=200)
        return HttpResponse('<script>alert("You have no fines recorded"); window.location.href = "/hostelmanagement/";</script>')

    # # Retrieve the fines associated with the current student
    student_fines = HostelFine.objects.filter(student_id=user_id)

    if wants_json:
        fine_data = list(
            student_fines.values(
                "fine_id",
                "student_name",
                "amount",
                "status",
                "reason",
                "hall_id",
            )
        )
        return JsonResponse({"student_fines": fine_data}, status=200)

    return render(request, 'hostelmanagement/student_fine_details.html', {'student_fines': student_fines})

    # return JsonResponse({'message': 'Nice'}, status=status.HTTP_200_OK)


class HostelFineUpdateView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def _get_hall_id_for_staff(self, user):
        if not hasattr(user, "extrainfo"):
            return None

        staff_id = user.extrainfo.id
        caretaker = HallCaretaker.objects.filter(staff_id=staff_id).first()
        if caretaker:
            return caretaker.hall_id

        warden = HallWarden.objects.filter(faculty_id=staff_id).first()
        if warden:
            return warden.hall_id

        return None

    def post(self, request, fine_id):
        user_id = request.user

        data = request.data
        fine_idd = data.get('fine_id')
        status_ = data.get('status')
        # print("fine_idd",fine_idd)
        # print("status_",status_)

        hall_id = self._get_hall_id_for_staff(user_id)
        if hall_id is None and not user_id.is_superuser:
            return Response({'error': 'You are not authorized to access this page'}, status=status.HTTP_403_FORBIDDEN)

        # Convert fine_id to integer
        fine_id = int(fine_id)

        # Get hostel fine object
        try:
            if hall_id is None:
                hostel_fine = HostelFine.objects.get(fine_id=fine_id)
            else:
                hostel_fine = HostelFine.objects.get(
                    hall_id=hall_id, fine_id=fine_id)
        except HostelFine.DoesNotExist:
            raise NotFound(detail="Hostel fine not found")

        # Validate required fields
        if status_ not in ['Pending', 'Paid']:
            return Response({'error': 'Invalid status value'}, status=status.HTTP_400_BAD_REQUEST)

        # # Update status of the hostel fine
        hostel_fine.status = status_
        hostel_fine.save()

        # Return success response
        return Response({'message': 'Hostel fine status updated successfully!'}, status=status.HTTP_200_OK)

    def delete(self, request, fine_id):
        user_id = request.user
        hall_id = self._get_hall_id_for_staff(user_id)
        if hall_id is None and not user_id.is_superuser:
            return Response({'error': 'You are not authorized to access this page'}, status=status.HTTP_403_FORBIDDEN)

        # Convert fine_id to integer
        fine_id = int(fine_id)

        # Get hostel fine object
        try:
            if hall_id is None:
                hostel_fine = HostelFine.objects.get(fine_id=fine_id)
            else:
                hostel_fine = HostelFine.objects.get(
                    hall_id=hall_id, fine_id=fine_id)
            hostel_fine.delete()
        except HostelFine.DoesNotExist:
            raise NotFound(detail="Hostel fine not found")

        return Response({'message': 'Fine deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)




class EditStudentView(View):
    template_name = 'hostelmanagement/edit_student.html'
    
    def get(self, request, student_id):
        student = Student.objects.get(id=student_id)
        
        context = {'student': student}
        return render(request, self.template_name, context)

    def post(self, request, student_id):
        student = Student.objects.get(id=student_id)
       
        # Update student details
        student.id.user.first_name = request.POST.get('first_name')
        student.id.user.last_name = request.POST.get('last_name')
        student.programme = request.POST.get('programme')
        student.batch = request.POST.get('batch')
        student.hall_no = request.POST.get('hall_number')
        student.room_no = request.POST.get('room_number')
        student.specialization = request.POST.get('specialization')
        
        student.save()

        # Update phone number and address from ExtraInfo model
        student.id.phone_no = request.POST.get('phone_number')
        student.id.address = request.POST.get('address')
        student.id.save()
        student.save()
        messages.success(request, 'Student details updated successfully.')
        return redirect("hostelmanagement:hostel_view")
    
class RemoveStudentView(View):
    def post(self, request, student_id):
        try:
            student = Student.objects.get(id=student_id)
            student.hall_no = 0
            student.save()
            messages.success(request, 'Student removed successfully.')
            return redirect("hostelmanagement:hostel_view")
            return JsonResponse({'status': 'success', 'message': 'Student removed successfully'})
        except Student.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Student not found'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    def dispatch(self, request, *args, **kwargs):
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'Method Not Allowed'}, status=405)
        return super().dispatch(request, *args, **kwargs)
    

