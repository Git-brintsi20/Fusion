import re
import datetime
from io import BytesIO
from typing import Any, Dict, Optional, Union

from django.db import transaction
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa

from applications.academic_information.models import Student
from applications.globals.models import Faculty, Staff

from .models import Hall, HallCaretaker, HallRoom, HallWarden, WorkerReport
from .selectors import get_available_rooms_for_hall


_HALL_NUMBER_RE = re.compile(r"\d+")


def get_caretaker_hall(hall_caretakers, user):
    """Return hall corresponding to a caretaker user."""
    for caretaker in hall_caretakers:
        if caretaker.staff.id.user == user:
            return caretaker.hall


def _parse_room_identifier(room_identifier: str):
    """Parse room identifiers like 'A-101' or 'A101'.

    Returns (block, room_number) as strings.
    """
    if not room_identifier:
        return None, None

    value = str(room_identifier).strip()
    block = value[0] if value else None
    digits = re.findall(r"\d+", value)
    room_number = str(digits[0]) if digits else None
    return block, room_number


def remove_from_room(student):
    """Removes the student from his current room."""
    if (student is None) or student.room_no is None:
        return
    block, room_num = _parse_room_identifier(student.room_no)
    if not block or not room_num:
        return
    hall = Hall.objects.get(hall_id="hall" + str(student.hall_no))
    room = HallRoom.objects.get(hall=hall, block_no=block, room_no=room_num)
    room.room_occupied = room.room_occupied - 1
    room.save()
    student.room_no = None
    student.save()


def add_to_room(student, new_room, new_hall):
    """Adds the student to his new room."""
    if (student is None) or (new_room is None) or (new_hall is None):
        return
    block, room_num = _parse_room_identifier(new_room)
    if not block or not room_num:
        return
    student.room_no = str(block) + "-" + str(room_num)
    student.hall_no = int(new_hall[-1])
    student.save()
    hall = Hall.objects.get(hall_id="hall" + str(student.hall_no))
    room = HallRoom.objects.get(hall=hall, block_no=block, room_no=str(room_num))
    room.room_occupied = room.room_occupied + 1
    room.save()


def render_to_pdf(template_src, context_dict=None):
    """Render a Django template to PDF response."""
    context_dict = context_dict or {}
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("ISO-8859-1")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None


def save_worker_report_sheet(excel, sheet, user_id):
    """Save details of worker report sheet into the database."""
    try:
        for row in range(0, sheet.nrows):
            worker_id = str(sheet.cell_value(row, 0))
            worker_name = str(sheet.cell_value(row, 1))

            present = 0
            for col in range(2, sheet.ncols):
                if int(sheet.cell_value(row, col)) == 1:
                    present += 1

            working_days = sheet.ncols - 2
            absent = working_days - present

            today_date = datetime.datetime.today()
            month = today_date.month
            year = today_date.year

            hall_no = HallCaretaker.objects.get(staff__id=user_id).hall
            with transaction.atomic():
                WorkerReport.objects.create(
                    worker_id=worker_id,
                    hall=hall_no,
                    worker_name=worker_name,
                    month=month,
                    year=year,
                    absent=absent,
                    total_day=working_days,
                    remark="none",
                )
    except Exception as e:
        print("Error:", e)


def is_user_staff(user) -> bool:
    try:
        return Staff.objects.filter(id__user=user).exists()
    except Exception:
        return False


def is_user_faculty(user) -> bool:
    try:
        return Faculty.objects.filter(id__user=user).exists()
    except Exception:
        return False


def get_staff_assigned_hall(user) -> Optional[Hall]:
    """Return the hall assigned to this user (caretaker/warden), else None."""
    if not getattr(user, "is_authenticated", False):
        return None

    try:
        extrainfo_id = user.extrainfo.id
    except Exception:
        return None

    caretaker = HallCaretaker.objects.filter(staff_id=extrainfo_id).select_related("hall").first()
    if caretaker:
        return caretaker.hall

    warden = HallWarden.objects.filter(faculty_id=extrainfo_id).select_related("hall").first()
    if warden:
        return warden.hall

    return None


def build_student_details_for_hall(
    hall: Union[Hall, str], include_available_rooms: bool = False
) -> Dict[str, Any]:
    """Build the student-details payload used by the hostel dashboard.

    Returns a dict with at least:
      - students: list[dict]
    Optionally:
      - available_rooms: list[HallRoom]
    """

    if isinstance(hall, str):
        hall = Hall.objects.get(hall_id=hall)

    hall_number_match = _HALL_NUMBER_RE.search(str(hall.hall_id))
    hall_number = int(hall_number_match.group(0)) if hall_number_match else None

    students_qs = Student.objects.none() if hall_number is None else Student.objects.filter(hall_no=hall_number)
    students_qs = students_qs.select_related("id__user")

    details = []
    for student in students_qs:
        extra = student.id  # Student.id is ExtraInfo in this codebase
        details.append(
            {
                "student_id": student.id.id,
                "first_name": student.id.user.first_name,
                "programme": student.programme,
                "batch": student.batch,
                "hall_number": student.hall_no,
                "room_number": student.room_no,
                "specialization": student.specialization,
                "address": getattr(extra, "address", None),
                "phone_number": getattr(extra, "phone_no", None),
            }
        )

    details = sorted(details, key=lambda x: x["student_id"])

    payload: Dict[str, Any] = {"students": details}
    if include_available_rooms:
        payload["available_rooms"] = get_available_rooms_for_hall(hall)

    return payload
