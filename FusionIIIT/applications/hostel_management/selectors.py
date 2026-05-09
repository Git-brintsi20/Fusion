import re
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

from django.db.models import QuerySet

from applications.academic_information.models import Student

from .models import (
    GuestRoom,
    GuestRoomBooking,
    Hall,
    HallCaretaker,
    HallRoom,
    HallWarden,
    HostelNoticeBoard,
    HostelStudentAttendence,
    StaffSchedule,
)


_HALL_NUMBER_RE = re.compile(r"\d+")


def _hall_number(hall_id: str) -> Optional[int]:
    match = _HALL_NUMBER_RE.search(str(hall_id or ""))
    if not match:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


def get_all_halls() -> QuerySet:
    return Hall.objects.all()


def get_hall_by_id(hall_id: str) -> Hall:
    return Hall.objects.get(hall_id=hall_id)


def get_staff_assignments() -> Tuple[QuerySet[HallCaretaker], QuerySet[HallWarden]]:
    caretakers = HallCaretaker.objects.select_related("hall", "staff__id__user")
    wardens = HallWarden.objects.select_related("hall", "faculty__id__user")
    return caretakers, wardens


def get_rooms_for_hall(hall: Hall) -> QuerySet[HallRoom]:
    return HallRoom.objects.filter(hall=hall)


def get_available_rooms_for_hall(hall: Hall) -> List[HallRoom]:
    rooms = get_rooms_for_hall(hall)
    return [room for room in rooms if room.room_cap > room.room_occupied]


def get_available_rooms_for_halls(halls: Iterable[Hall]) -> List[HallRoom]:
    hall_ids = [h.id for h in halls]
    rooms = HallRoom.objects.filter(hall_id__in=hall_ids).select_related("hall")
    return [room for room in rooms if room.room_cap > room.room_occupied]


def get_halls_students_map(halls: Iterable[Hall]) -> Dict[str, List[Student]]:
    hall_numbers: List[int] = []
    hall_by_number: Dict[int, str] = {}
    for hall in halls:
        number = _hall_number(hall.hall_id)
        if number is None:
            continue
        hall_numbers.append(number)
        hall_by_number[number] = hall.hall_id

    students = (
        Student.objects.filter(hall_no__in=hall_numbers)
        .select_related("id__user")
        .order_by("id_id")
    )

    grouped: Dict[str, List[Student]] = defaultdict(list)
    for student in students:
        hall_id = hall_by_number.get(int(student.hall_no))
        if hall_id:
            grouped[hall_id].append(student)

    # Ensure keys exist for all halls
    for hall in halls:
        grouped.setdefault(hall.hall_id, [])

    return dict(grouped)


def get_halls_staff_schedules_map(halls: Iterable[Hall]) -> Dict[str, List[StaffSchedule]]:
    hall_ids = [h.id for h in halls]
    schedules = (
        StaffSchedule.objects.filter(hall_id__in=hall_ids)
        .select_related("hall", "staff_id__id__user")
        .order_by("id")
    )

    grouped: Dict[str, List[StaffSchedule]] = defaultdict(list)
    hall_id_to_code = {h.id: h.hall_id for h in halls}
    for sched in schedules:
        hall_code = hall_id_to_code.get(sched.hall_id)
        if hall_code:
            grouped[hall_code].append(sched)

    for hall in halls:
        grouped.setdefault(hall.hall_id, [])

    return dict(grouped)


def get_halls_notices_map(halls: Iterable[Hall]) -> Dict[str, List[HostelNoticeBoard]]:
    hall_ids = [h.id for h in halls]
    notices = (
        HostelNoticeBoard.objects.filter(hall_id__in=hall_ids)
        .select_related("hall", "posted_by__user")
        .order_by("-id")
    )

    grouped: Dict[str, List[HostelNoticeBoard]] = defaultdict(list)
    hall_id_to_code = {h.id: h.hall_id for h in halls}
    for notice in notices:
        hall_code = hall_id_to_code.get(notice.hall_id)
        if hall_code:
            grouped[hall_code].append(notice)

    for hall in halls:
        grouped.setdefault(hall.hall_id, [])

    return dict(grouped)


def get_pending_guest_room_requests_map(halls: Iterable[Hall]) -> Dict[str, List[GuestRoomBooking]]:
    hall_ids = [h.id for h in halls]
    pending = (
        GuestRoomBooking.objects.filter(hall_id__in=hall_ids, status="Pending")
        .select_related("hall", "intender")
        .order_by("id")
    )

    grouped: Dict[str, List[GuestRoomBooking]] = defaultdict(list)
    hall_id_to_code = {h.id: h.hall_id for h in halls}
    for booking in pending:
        hall_code = hall_id_to_code.get(booking.hall_id)
        if hall_code:
            grouped[hall_code].append(booking)

    for hall in halls:
        grouped.setdefault(hall.hall_id, [])

    return dict(grouped)


def get_guest_rooms_map(halls: Iterable[Hall]) -> Dict[str, List[GuestRoom]]:
    hall_ids = [h.id for h in halls]
    rooms = (
        GuestRoom.objects.filter(hall_id__in=hall_ids, vacant=True)
        .select_related("hall")
        .order_by("id")
    )

    grouped: Dict[str, List[GuestRoom]] = defaultdict(list)
    hall_id_to_code = {h.id: h.hall_id for h in halls}
    for room in rooms:
        hall_code = hall_id_to_code.get(room.hall_id)
        if hall_code:
            grouped[hall_code].append(room)

    for hall in halls:
        grouped.setdefault(hall.hall_id, [])

    return dict(grouped)


def get_halls_attendance_map(halls: Iterable[Hall]) -> Dict[str, List[HostelStudentAttendence]]:
    hall_ids = [h.id for h in halls]
    attendance = (
        HostelStudentAttendence.objects.filter(hall_id__in=hall_ids)
        .select_related("hall", "student_id")
        .order_by("id")
    )

    grouped: Dict[str, List[HostelStudentAttendence]] = defaultdict(list)
    hall_id_to_code = {h.id: h.hall_id for h in halls}
    for record in attendance:
        hall_code = hall_id_to_code.get(record.hall_id)
        if hall_code:
            grouped[hall_code].append(record)

    for hall in halls:
        grouped.setdefault(hall.hall_id, [])

    return dict(grouped)


def get_hall_staff_assignments_map(
    halls: Iterable[Hall],
) -> Dict[str, Dict[str, Optional[object]]]:
    hall_ids = [h.id for h in halls]
    caretakers = (
        HallCaretaker.objects.filter(hall_id__in=hall_ids)
        .select_related("hall", "staff__id__user")
        .order_by("id")
    )
    wardens = (
        HallWarden.objects.filter(hall_id__in=hall_ids)
        .select_related("hall", "faculty__id__user")
        .order_by("id")
    )

    caretaker_by_hall: Dict[int, HallCaretaker] = {}
    for c in caretakers:
        caretaker_by_hall.setdefault(c.hall_id, c)

    warden_by_hall: Dict[int, HallWarden] = {}
    for w in wardens:
        warden_by_hall.setdefault(w.hall_id, w)

    result: Dict[str, Dict[str, Optional[object]]] = {}
    for hall in halls:
        result[hall.hall_id] = {
            "caretaker": caretaker_by_hall.get(hall.id),
            "warden": warden_by_hall.get(hall.id),
        }

    return result
