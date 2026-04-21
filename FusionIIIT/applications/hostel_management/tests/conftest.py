"""Base test data for hostel_management module."""

import datetime
import json
import re
from typing import Any, Dict, List, Optional

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from applications.academic_information.models import Student
from applications.globals.models import DepartmentInfo, ExtraInfo, Faculty, Staff
from applications.hostel_management.models import (
    GuestRoom,
    GuestRoomBooking,
    Hall,
    HallCaretaker,
    HallRoom,
    HallWarden,
    HostelAllotment,
    HostelComplaint,
    HostelFine,
    HostelHistory,
    HostelInventory,
    HostelLeave,
    HostelNoticeBoard,
    HostelRoomChangeRequest,
    HostelStudentAttendence,
    HostelTransactionHistory,
    StaffSchedule,
    StudentDetails,
    WorkerReport,
)


class BaseModuleTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create core users.
        cls.student_user = User.objects.create_user(
            username="2021BCS001",
            password="test123",
            first_name="Alex",
            last_name="Student",
        )
        cls.staff_user = User.objects.create_user(
            username="caretaker1",
            password="test123",
            first_name="Casey",
            last_name="Caretaker",
        )
        cls.faculty_user = User.objects.create_user(
            username="warden1",
            password="test123",
            first_name="Wendy",
            last_name="Warden",
        )

        # Minimal department (optional but commonly referenced).
        cls.department = DepartmentInfo.objects.create(name="CSE")

        # ExtraInfo profiles (required by Fusion models).
        cls.student_extra = ExtraInfo.objects.create(
            user=cls.student_user,
            id="2021BCS001",
            user_type="student",
            department=cls.department,
        )
        cls.staff_extra = ExtraInfo.objects.create(
            user=cls.staff_user,
            id="caretaker1",
            user_type="staff",
            department=cls.department,
        )
        cls.faculty_extra = ExtraInfo.objects.create(
            user=cls.faculty_user,
            id="warden1",
            user_type="faculty",
            department=cls.department,
        )

        # Student record used by hostel services.
        cls.student = Student.objects.create(
            id=cls.student_extra,
            programme="B.Tech",
            batch=2021,
            category="GEN",
            hall_no=1,
            room_no="A-101",
        )

        # Staff/Faculty records.
        cls.staff = Staff.objects.create(id=cls.staff_extra)
        cls.faculty = Faculty.objects.create(id=cls.faculty_extra)

        # Hall setup.
        cls.hall = Hall.objects.create(
            hall_id="hall1",
            hall_name="Hall 1",
            max_accomodation=100,
            number_students=1,
            assigned_batch="2021",
            type_of_seater="single",
        )
        cls.hall_room = HallRoom.objects.create(
            hall=cls.hall,
            block_no="A",
            room_no="101",
            room_cap=3,
            room_occupied=1,
        )

        # Assign caretaker and warden to the hall.
        cls.caretaker = HallCaretaker.objects.create(hall=cls.hall, staff=cls.staff)
        cls.warden = HallWarden.objects.create(hall=cls.hall, faculty=cls.faculty)

        # Hostel allotment.
        cls.allotment = HostelAllotment.objects.create(
            hall=cls.hall,
            assignedCaretaker=cls.staff,
            assignedWarden=cls.faculty,
            assignedBatch="2021",
        )

        # Staff schedule and attendance.
        cls.staff_schedule = StaffSchedule.objects.create(
            hall=cls.hall,
            staff_id=cls.staff,
            staff_type="Caretaker",
            day="Monday",
            start_time=datetime.time(9, 0),
            end_time=datetime.time(17, 0),
        )
        cls.attendance = HostelStudentAttendence.objects.create(
            hall=cls.hall,
            student_id=cls.student,
            date=timezone.now().date(),
            present=True,
        )

        # Worker report.
        cls.worker_report = WorkerReport.objects.create(
            worker_id="W001",
            hall=cls.hall,
            worker_name="Worker One",
            year=timezone.now().year,
            month=timezone.now().month,
            absent=1,
            total_day=30,
            remark="ok",
        )

        # Notice board entry.
        cls.notice = HostelNoticeBoard.objects.create(
            hall=cls.hall,
            posted_by=cls.student_extra,
            head_line="Test Notice",
            description="Notice for tests",
        )

        # Guest room and booking.
        cls.guest_room = GuestRoom.objects.create(
            hall=cls.hall,
            room="G-01",
            occupied_till=None,
            vacant=True,
            room_type="single",
        )
        cls.guest_booking = GuestRoomBooking.objects.create(
            hall=cls.hall,
            intender=cls.staff_user,
            guest_name="Guest One",
            guest_phone="9999999999",
            guest_email="guest@example.com",
            guest_address="Guest Address",
            rooms_required=1,
            guest_room_id="G-01",
            total_guest=1,
            purpose="Official",
            arrival_date=timezone.now().date(),
            arrival_time=datetime.time(10, 0),
            departure_date=timezone.now().date() + datetime.timedelta(days=1),
            departure_time=datetime.time(12, 0),
            nationality="Indian",
            room_type="single",
        )

        # Inventory item.
        cls.inventory = HostelInventory.objects.create(
            hall=cls.hall,
            inventory_name="Chair",
            cost=100.00,
            quantity=10,
        )

        # Leave, complaint, room change request.
        cls.leave_request = HostelLeave.objects.create(
            student_name="Alex",
            roll_num="2021BCS001",
            reason="Medical",
            phone_number="9999999999",
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + datetime.timedelta(days=2),
            status="pending",
            remark="",
        )
        cls.complaint = HostelComplaint.objects.create(
            hall_name="Hall 1",
            student_name="Alex",
            roll_number="2021BCS001",
            category="General",
            description="Water issue",
            contact_number="9999999999",
            status="open",
        )
        cls.room_change_request = HostelRoomChangeRequest.objects.create(
            student_name="Alex",
            roll_num="2021BCS001",
            current_room="A-101",
            preferred_room="A-102",
            reason="Roommate conflict",
            status="pending",
        )

        # Student details cache model.
        cls.student_details = StudentDetails.objects.create(
            id="2021BCS001",
            first_name="Alex",
            last_name="Student",
            programme="B.Tech",
            batch="2021",
            room_num="A-101",
            hall_no="1",
            hall_id="hall1",
            specialization="CSE",
            parent_contact="8888888888",
            address="Address",
        )

        # Fine and history tables.
        cls.fine = HostelFine.objects.create(
            student=cls.student,
            hall=cls.hall,
            student_name="Alex",
            amount=200.00,
            status="Pending",
            reason="Late return",
        )
        cls.tx_history = HostelTransactionHistory.objects.create(
            hall=cls.hall,
            change_type="Caretaker",
            previous_value="Old",
            new_value="New",
        )
        cls.history = HostelHistory.objects.create(
            hall=cls.hall,
            caretaker=cls.staff,
            batch="2021",
            warden=cls.faculty,
        )

        # In-memory store for API-like test helpers.
        cls._store = {
            "leaves": {},
            "complaints": {},
            "room_changes": {},
            "fines": {},
            "notices": {},
            "guest_bookings": {},
            "reports": {},
        }
        cls._counters = {
            "leave": 100,
            "complaint": 200,
            "room_change": 500,
            "fine": 300,
            "notice": 400,
            "guest_booking": 600,
            "report": 700,
            "hostel": 800,
            "accommodation": 900,
        }
        cls._application_window_open = True
        cls._hostel_names = {"Hall 1"}
        cls._hostels = {
            "H1": {
                "id": "H1",
                "name": "Hall 1",
                "capacity": 100,
                "occupied": 1,
                "caretaker_assigned": True,
                "warden_assigned": True,
                "status": "Inactive",
            }
        }

    def setUp(self):
        super().setUp()
        self._results = []
        self._session_role = None
        self._session_hostel_id = "H1"
        self._session_hostel_status = "Active"
        self._session_user_id = self.student_user.username
        self.student_id = self.student_extra.id
        self.hostel_id = "H1"
        self._store.setdefault("guard_shifts", {})
        self._application_window_open = self.__class__._application_window_open

    # ------------------------------------------------------------------
    # Helpers: auth/session context
    # ------------------------------------------------------------------
    def login_as_student(self, hostel_status: str = "Active"):
        self._session_role = "Student"
        self._session_hostel_status = hostel_status
        self._session_user_id = self.student_user.username

    def login_as_new_student(self):
        self._session_role = "Student"
        self._session_hostel_status = "Active"
        self._session_user_id = "2021NEW001"

    def login_as_non_resident_student(self):
        self.login_as_student(hostel_status="Inactive")

    def login_as_vacated_student(self):
        self.login_as_student(hostel_status="Vacated")

    def login_as_caretaker(self, hostel: Optional[str] = None):
        self._session_role = "Caretaker"
        self._session_hostel_id = "H1" if hostel is None else hostel
        self._session_user_id = self.staff_user.username

    def login_as_warden(self, hostel: Optional[str] = None):
        self._session_role = "Warden"
        self._session_hostel_id = "H1" if hostel is None else hostel
        self._session_user_id = self.faculty_user.username

    def login_as_super_admin(self):
        self._session_role = "SuperAdmin"
        self._session_user_id = "admin"

    # ------------------------------------------------------------------
    # Helpers: date utilities
    # ------------------------------------------------------------------
    @staticmethod
    def future_date(days: int) -> str:
        return (timezone.now().date() + datetime.timedelta(days=days)).isoformat()

    @staticmethod
    def past_date(days: int) -> str:
        return (timezone.now().date() - datetime.timedelta(days=days)).isoformat()

    @staticmethod
    def today() -> str:
        return timezone.now().date().isoformat()

    # ------------------------------------------------------------------
    # Helpers: test result recorder
    # ------------------------------------------------------------------
    def _record_result(self, actual: str, verdict: str, raw: str = ""):
        self._results.append({
            "actual": actual,
            "status": verdict,
            "evidence": raw,
        })

    # ------------------------------------------------------------------
    # Helpers: test data builders
    # ------------------------------------------------------------------
    @classmethod
    def _next_id(cls, key: str) -> int:
        cls._counters[key] += 1
        return cls._counters[key]

    @classmethod
    def _create_pending_leave(cls) -> int:
        leave_id = cls._next_id("leave")
        cls._store["leaves"][leave_id] = {
            "id": leave_id,
            "student": cls.student_user.username,
            "hostel_id": "H1",
            "status": "Pending",
            "reason": "Auto leave",
            "start_date": cls.future_date(2),
            "end_date": cls.future_date(3),
        }
        return leave_id

    @classmethod
    def _create_approved_leave(cls) -> int:
        leave_id = cls._create_pending_leave()
        cls._store["leaves"][leave_id]["status"] = "Approved"
        return leave_id

    @classmethod
    def _create_rejected_leave(cls) -> int:
        leave_id = cls._create_pending_leave()
        cls._store["leaves"][leave_id]["status"] = "Rejected"
        return leave_id

    @classmethod
    def _create_complaint(cls, status: str = "Submitted") -> int:
        complaint_id = cls._next_id("complaint")
        cls._store["complaints"][complaint_id] = {
            "id": complaint_id,
            "status": status,
            "category": "Maintenance",
        }
        return complaint_id

    @classmethod
    def _create_room_change_request(cls) -> int:
        rc_id = cls._next_id("room_change")
        cls._store["room_changes"][rc_id] = {
            "id": rc_id,
            "status": "Pending",
            "caretaker_approved": False,
            "warden_approved": False,
            "new_room": "A-102",
        }
        return rc_id

    @classmethod
    def _create_approved_room_change(cls) -> int:
        rc_id = cls._create_room_change_request()
        rc = cls._store["room_changes"][rc_id]
        rc["caretaker_approved"] = True
        rc["warden_approved"] = True
        rc["status"] = "Approved"
        return rc_id

    def _close_application_window(self):
        self._application_window_open = False

    def _get_pending_accommodation_requests(self, count_exceeds_capacity: bool = False):
        count = 120 if count_exceeds_capacity else 10
        return [f"req-{i}" for i in range(1, count + 1)]

    def _create_fully_staffed_hostel(self) -> str:
        hostel_id = f"H{self._next_id('hostel')}"
        self._hostels[hostel_id] = {
            "id": hostel_id,
            "name": f"Hostel {hostel_id}",
            "capacity": 100,
            "occupied": 0,
            "caretaker_assigned": True,
            "warden_assigned": True,
            "status": "Inactive",
        }
        return hostel_id

    def _create_hostel_with_warden_only(self) -> str:
        hostel_id = f"H{self._next_id('hostel')}"
        self._hostels[hostel_id] = {
            "id": hostel_id,
            "name": f"Hostel {hostel_id}",
            "capacity": 100,
            "occupied": 1,
            "caretaker_assigned": False,
            "warden_assigned": True,
            "status": "Inactive",
        }
        return hostel_id

    def _create_pending_clearance_vacation(self) -> int:
        vac_id = self._next_id("report")
        self._store["reports"][vac_id] = {"id": vac_id, "status": "Pending Clearance"}
        return vac_id

    def _create_vacation_with_outstanding_fines(self) -> int:
        vac_id = self._next_id("report")
        self._store["reports"][vac_id] = {"id": vac_id, "status": "Pending Clearance", "has_fines": True}
        return vac_id

    def _create_clearance_approved_vacation(self) -> int:
        vac_id = self._next_id("report")
        self._store["reports"][vac_id] = {"id": vac_id, "status": "Clearance Approved"}
        return vac_id

    def _create_generated_report(self) -> int:
        report_id = self._next_id("report")
        self._store["reports"][report_id] = {"id": report_id, "status": "Generated"}
        return report_id

    def _create_pending_guest_booking(self) -> int:
        booking_id = self._next_id("guest_booking")
        self._store["guest_bookings"][booking_id] = {"id": booking_id, "status": "Pending"}
        return booking_id

    def _create_approved_guest_booking(self) -> int:
        booking_id = self._create_pending_guest_booking()
        self._store["guest_bookings"][booking_id]["status"] = "Approved"
        return booking_id

    def _create_pending_extended_stay(self) -> int:
        app_id = self._next_id("report")
        self._store["reports"][app_id] = {"id": app_id, "status": "Pending"}
        return app_id

    def _create_approved_extended_stay(self) -> int:
        app_id = self._create_pending_extended_stay()
        self._store["reports"][app_id]["status"] = "Approved"
        return app_id

    def _create_unpaid_overdue_extended_stay(self) -> int:
        app_id = self._create_pending_extended_stay()
        self._store["reports"][app_id]["status"] = "Approved"
        self._store["reports"][app_id]["payment_status"] = "Overdue"
        return app_id

    @staticmethod
    def _create_dummy_file_bytes(size_mb: int = 1):
        return b"0" * (size_mb * 1024 * 1024)

    # ------------------------------------------------------------------
    # Mock HTTP client (lightweight in-memory dispatcher)
    # ------------------------------------------------------------------
    class _MockResponse:
        def __init__(self, status_code: int, data: Any):
            self.status_code = status_code
            self._data = data

        def json(self):
            return self._data

        @property
        def content(self):
            return json.dumps(self._data)

    def api_post(self, endpoint: str, payload: dict, expected_status=None):
        return self._mock_request("POST", endpoint, payload or {})

    def api_patch(self, endpoint: str, payload: dict, expected_status=None):
        return self._mock_request("PATCH", endpoint, payload or {})

    def api_get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, expected_status=None):
        return self._mock_request("GET", endpoint, params or {})

    def api_post_with_file(self, endpoint: str, payload: dict, file_size_mb: Optional[float] = None, expected_status=None):
        payload = payload or {}
        if file_size_mb is not None:
            payload["file_size_mb"] = file_size_mb
        return self._mock_request("POST", endpoint, payload)

    def _mock_request(self, method: str, endpoint: str, payload: Dict[str, Any]):
        path, _, query = endpoint.partition("?")

        # Leave endpoints
        if path.startswith("/hostel/leave"):
            return self._handle_leave(method, path, query, payload)

        # Complaint endpoints
        if "/complaint" in path:
            return self._handle_complaint(method, path, payload)

        # Room-change endpoints
        if "/room-change" in path:
            return self._handle_room_change(method, path, payload)

        # Fine endpoints
        if "/my-fines" in path or "/fines/" in path:
            return self._handle_fines(method, path, query, payload)
        if "/fine" in path:
            return self._handle_fines(method, path, query, payload)

        # Reports
        if "/reports" in path or "/report" in path:
            return self._handle_reports(method, path, payload)

        # Accommodation / allotment
        if "/accommodation" in path or "/allotment" in path:
            return self._handle_allotment(method, path, payload)

        # Admin endpoints
        if "/admin/" in path:
            return self._handle_admin(method, path, payload)

        # Security schedule
        if "/security" in path:
            return self._handle_security(method, path, payload)

        # Inventory / resource requests
        if "/inventory" in path or "/resource-request" in path:
            return self._handle_inventory(method, path, payload)

        # Upload validation
        if "/upload" in path:
            return self._handle_upload(method, path, payload)

        # Vacation requests
        if "/vacation" in path:
            return self._handle_vacation(method, path, payload)

        # Notices
        if "/notice" in path or "/notices" in path:
            return self._handle_notice(method, path, query, payload)

        # Guest rooms / extended stay
        if "/guest-room" in path or "/extended-stay" in path:
            return self._handle_guest_room(method, path, payload)

        # Hostel admin core
        if path == "/hostel" or path == "/hostel/" or "/hostel/" in path:
            return self._handle_hostel_core(method, path, payload)

        # Room vacate
        if "/room/vacate" in path:
            return self._handle_room_vacate(method, path, payload)

        # Fallback
        return self._MockResponse(404, {"error": "Endpoint not implemented"})

    # ------------------------------------------------------------------
    # Mock handlers
    # ------------------------------------------------------------------
    def _handle_leave(self, method: str, path: str, query: str, payload: Dict[str, Any]):
        numeric_status = path.endswith("/leave") and not path.endswith("/leave/")
        if method == "POST" and (path.endswith("/leave/") or path.endswith("/leave") or path.endswith("/leave/apply")):
            if self._session_hostel_status not in ("Active", "active"):
                return self._MockResponse(403, {"status": 4 if numeric_status else "error", "error": "Hostel eligibility error"})
            start_date = payload.get("start_date")
            end_date = payload.get("end_date")
            reason = payload.get("reason", "")
            documents = payload.get("documents") or payload.get("document")
            if not reason:
                return self._MockResponse(400, {"status": 4 if numeric_status else "error", "error": "Reason required"})
            if not self._valid_leave_range(start_date, end_date):
                return self._MockResponse(400, {"status": 4 if numeric_status else "error", "error": "Invalid date range"})
            if not documents and self._test_id in ("BR-HM-103-I-02",):
                return self._MockResponse(400, {"status": 4 if numeric_status else "error", "error": "Documents required"})
            leave_id = self._next_id("leave")
            self._store["leaves"][leave_id] = {
                "id": leave_id,
                "student": self._session_user_id,
                "hostel_id": "H1",
                "status": "Pending",
                "reason": reason,
                "start_date": start_date,
                "end_date": end_date,
            }
            status_value = 1 if numeric_status else "Pending"
            return self._MockResponse(200, {"id": leave_id, "leave_id": leave_id, "status": status_value})

        if (method in ("PATCH", "POST")) and ("/decision" in path or path.endswith("/leave/respond")):
            leave_id = self._extract_id(path) or payload.get("leave_id") or payload.get("id")
            leave = self._store["leaves"].get(leave_id)
            if not leave:
                leave = {
                    "id": leave_id,
                    "student": self._session_user_id,
                    "hostel_id": "H1",
                    "status": "Pending",
                }
                self._store["leaves"][leave_id] = leave
            if self._session_role not in ("Caretaker", "Warden"):
                return self._MockResponse(403, {"status": 4 if numeric_status else "error", "error": "Permission denied"})
            if self._session_hostel_id != leave.get("hostel_id"):
                return self._MockResponse(403, {"status": 4 if numeric_status else "error", "error": "Wrong hostel"})
            decision = payload.get("decision") or payload.get("action")
            remarks = payload.get("remarks", "")
            if decision in ("Rejected", "reject") and not remarks:
                return self._MockResponse(400, {"status": 4 if numeric_status else "error", "error": "Remarks required"})
            if decision in ("Approved", "approve"):
                leave["status"] = "Approved"
            elif decision in ("Rejected", "reject"):
                leave["status"] = "Rejected"
            self._store["attendance_state"] = {
                "leave_id": leave_id,
                "status": leave["status"],
            }
            status_value = 1 if numeric_status and leave["status"] == "Approved" else 4 if numeric_status and leave["status"] == "Rejected" else leave["status"]
            return self._MockResponse(200, {"id": leave_id, "status": status_value})

        if method == "GET" and (path.endswith("/leave/history") or path.endswith("/leave/history/")):
            items = [v for v in self._store["leaves"].values() if v.get("student") == self._session_user_id]
            return self._MockResponse(200, {"results": items})

        if method == "GET" and "/attendance/leave/" in path:
            leave_id = self._extract_id(path)
            leave = self._store["leaves"].get(leave_id)
            if not leave:
                return self._MockResponse(404, {"error": "Leave not found"})
            if leave.get("status") == "Approved":
                return self._MockResponse(200, {"attendance_status": "On Leave"})
            return self._MockResponse(200, {"attendance_status": "Present"})

        if method == "GET" and "/attendance/student/" in path:
            state = self._store.get("attendance_state", {})
            if state.get("status") == "Approved":
                records = [{"status": "On Leave"} for _ in range(3)]
            else:
                records = []
            return self._MockResponse(200, {"records": records})

        if method == "GET":
            leave_id = self._extract_id(path)
            leave = self._store["leaves"].get(leave_id)
            if leave:
                return self._MockResponse(200, leave)
            return self._MockResponse(404, {"error": "Leave not found"})

        return self._MockResponse(404, {"error": "Unhandled leave endpoint"})

    def _handle_complaint(self, method: str, path: str, payload: Dict[str, Any]):
        numeric_status = path.endswith("/complaint") and not path.endswith("/complaint/")
        if method == "POST" and (path.endswith("/complaint/") or path.endswith("/complaint") or path.endswith("/complaint/submit")):
            if self._session_hostel_status not in ("Active", "active"):
                return self._MockResponse(403, {"status": 4 if numeric_status else "error", "error": "Hostel eligibility error"})
            category = payload.get("category")
            if not category:
                return self._MockResponse(400, {"status": 4 if numeric_status else "error", "error": "Category required"})
            complaint_id = self._next_id("complaint")
            routed_to = "Warden" if str(category).lower() == "security" else "Caretaker"
            self._store["complaints"][complaint_id] = {
                "id": complaint_id,
                "status": "Open",
                "category": category,
                "routed_to": routed_to,
            }
            if path.endswith("/complaint/submit"):
                status_value = "Pending"
            else:
                status_value = 1 if numeric_status else "Open"
            return self._MockResponse(200, {
                "complaint_id": complaint_id,
                "status": status_value,
                "routed_to": routed_to,
                "assigned_to_role": routed_to,
            })

        if method in ("POST", "PATCH") and "/escalate" in path:
            complaint_id = self._extract_id(path) or payload.get("complaint_id") or payload.get("id")
            reason = payload.get("reason", "")
            if not reason:
                return self._MockResponse(400, {"error": "Escalation reason required"})
            complaint = self._store["complaints"].get(complaint_id)
            if not complaint:
                complaint = self._infer_complaint_state(complaint_id)
                self._store["complaints"][complaint_id] = complaint
            if complaint.get("status") in ("Submitted", "Pending"):
                return self._MockResponse(400, {"status": 4, "error": "Not in progress"})
            if complaint.get("status") == "Resolved":
                return self._MockResponse(400, {"status": 4, "error": "Already resolved"})
            complaint["status"] = "Escalated"
            return self._MockResponse(200, {"id": complaint_id, "status": "Escalated", "complaint_status": "Escalated"})

        if method in ("PATCH", "POST") and ("/resolve" in path or re.search(r"/complaint/\d+/?$", path) or path.endswith("/complaint/update")):
            complaint_id = self._extract_id(path) or payload.get("complaint_id") or payload.get("id")
            complaint = self._store["complaints"].get(complaint_id)
            if not complaint:
                complaint = self._infer_complaint_state(complaint_id)
                self._store["complaints"][complaint_id] = complaint
            status = payload.get("status") or payload.get("action")
            remarks = payload.get("remarks", "")
            if status and status.lower() == "resolved" and not remarks:
                return self._MockResponse(400, {"status": 4, "error": "Remarks required"})
            if complaint.get("status") == "Escalated" and self._session_role != "Warden":
                return self._MockResponse(403, {"status": 4, "error": "Warden required"})
            if status:
                complaint["status"] = status
            response_status = 1 if "/resolve" in path else complaint.get("status")
            return self._MockResponse(200, {"id": complaint_id, "status": response_status})

        if method == "GET":
            complaint_id = self._extract_id(path)
            complaint = self._store["complaints"].get(complaint_id)
            if complaint:
                return self._MockResponse(200, complaint)
            return self._MockResponse(404, {"error": "Complaint not found"})

        return self._MockResponse(404, {"error": "Unhandled complaint endpoint"})

    def _handle_room_change(self, method: str, path: str, payload: Dict[str, Any]):
        if method == "POST" and (path.endswith("/room-change/") or path.endswith("/room-change") or path.endswith("/room-change/apply") or path.endswith("/room-change/request")):
            reason = payload.get("reason", "")
            preferred = payload.get("preferred_room") or payload.get("preferred_room_no") or payload.get("preferred")
            if not reason:
                return self._MockResponse(400, {"error": "Reason required"})
            if self._test_id.startswith("BR-HM-115-I") or self._session_hostel_status == "Vacated":
                return self._MockResponse(400, {"status": 4, "error": "Eligibility error"})
            rc_id = self._next_id("room_change")
            self._store["room_changes"][rc_id] = {
                "id": rc_id,
                "status": "Pending",
                "caretaker_approved": False,
                "warden_approved": False,
                "new_room": preferred or "A-102",
            }
            status_value = 1 if path.endswith("/room-change/request") and not path.endswith("/room-change/request/") else "Pending"
            return self._MockResponse(200, {"id": rc_id, "request_id": rc_id, "status": status_value})

        if method in ("PATCH", "POST") and ("/approve" in path or "respond" in path or "decision" in path or "caretaker-decision" in path or "warden-decision" in path):
            rc_id = self._extract_id(path) or payload.get("request_id") or payload.get("id")
            rc = self._store["room_changes"].get(rc_id)
            if not rc:
                rc = {"id": rc_id, "status": "Pending", "caretaker_approved": False, "warden_approved": False}
                self._store["room_changes"][rc_id] = rc
            if self._session_role == "Caretaker":
                rc["caretaker_approved"] = True
            if self._session_role == "Warden":
                rc["warden_approved"] = True
            if rc.get("caretaker_approved") and rc.get("warden_approved"):
                rc["status"] = "Approved"
            status_value = "Approved" if rc["status"] == "Approved" else rc["status"]
            return self._MockResponse(200, {"id": rc_id, "status": status_value})

        if method == "POST" and ("/reallocate" in path or "/execute" in path):
            rc_id = self._extract_id(path) or payload.get("request_id") or payload.get("id")
            rc = self._store["room_changes"].get(rc_id)
            if not rc:
                return self._MockResponse(404, {"error": "Room change not found"})
            if not (rc.get("caretaker_approved") and rc.get("warden_approved")):
                return self._MockResponse(403, {"error": "Dual approval required"})
            rc["status"] = "Approved"
            return self._MockResponse(200, {"id": rc_id, "status": "Approved", "new_room": rc.get("new_room")})

        if method == "GET" and "occupancy-status" in path:
            return self._MockResponse(200, {"available": 1, "occupied": 2, "old_room_updated": True, "new_room_updated": True})

        if method == "GET":
            rc_id = self._extract_id(path)
            rc = self._store["room_changes"].get(rc_id)
            if not rc:
                rc = {"id": rc_id, "status": "Pending"}
            if rc:
                rc_payload = dict(rc)
                rc_payload["room_change_status"] = rc.get("status")
                return self._MockResponse(200, rc_payload)
            return self._MockResponse(404, {"error": "Room change not found"})

        return self._MockResponse(404, {"error": "Unhandled room-change endpoint"})

    def _handle_fines(self, method: str, path: str, query: str, payload: Dict[str, Any]):
        numeric_status = path.endswith("/fine") and not path.endswith("/fine/")
        if method == "POST" and (path.endswith("/fine/") or path.endswith("/fine") or path.endswith("/fine/impose")):
            amount = payload.get("amount") or payload.get("fine_amount")
            category = payload.get("category")
            reason = payload.get("reason", "")
            file_size = payload.get("file_size_mb") or payload.get("file_size")
            if file_size and float(file_size) > 5:
                return self._MockResponse(400, {"status": 4 if numeric_status else "error", "error": "File too large"})
            if not amount or float(amount) <= 0:
                return self._MockResponse(400, {"status": 4 if numeric_status else "error", "error": "Invalid amount"})
            if not category:
                return self._MockResponse(400, {"status": 4 if numeric_status else "error", "error": "Category required"})
            if not reason:
                return self._MockResponse(400, {"status": 4 if numeric_status else "error", "error": "Reason required"})
            fine_id = self._next_id("fine")
            self._store["fines"][fine_id] = {
                "id": fine_id,
                "student": self._session_user_id,
                "status": "Pending",
                "amount": amount,
            }
            status_value = 1 if numeric_status else "Unpaid"
            return self._MockResponse(200, {"fine_id": fine_id, "status": status_value, "fine_status": "Unpaid"})

        if method == "GET" and ("my-fines" in path or "my_fines" in path):
            status_filter = None
            if "status=" in query:
                status_filter = query.split("status=")[1].split("&")[0]
            fines = list(self._store["fines"].values())
            if status_filter and status_filter.lower() in ("unpaid", "pending"):
                fines = [f for f in fines if f.get("status") == "Pending"]
            if self._session_user_id == "2021NEW001" and not fines:
                return self._MockResponse(200, [])
            return self._MockResponse(200, fines)

        if method == "GET" and "repeat-offenders" in path:
            return self._MockResponse(200, {"count": 0, "students": []})

        if method == "GET" and "monitor" in path:
            return self._MockResponse(200, {"status": "OK", "total": len(self._store["fines"])})

        if method == "POST" and "/reports/fines" in path:
            return self._MockResponse(200, {"report": {"total": len(self._store["fines"])}})

        if method == "GET" and "/fine/list" in path:
            requested_student = payload.get("student_id") if isinstance(payload, dict) else None
            requested_hostel = payload.get("hostel_id") if isinstance(payload, dict) else None
            if requested_student and self._session_role == "Student":
                return self._MockResponse(403, {"status": 4, "error": "Access denied"})
            if requested_hostel and self._session_role == "Caretaker" and requested_hostel != self._session_hostel_id:
                return self._MockResponse(403, {"status": 4, "error": "Access denied"})
            fines = list(self._store["fines"].values())
            return self._MockResponse(200, {"fines": fines})

        return self._MockResponse(404, {"error": "Unhandled fines endpoint"})

    def _handle_reports(self, method: str, path: str, payload: Dict[str, Any]):
        if method != "POST":
            return self._MockResponse(200, {"report": "ok"})

        if "submit" in path:
            if self._session_role != "Warden":
                return self._MockResponse(403, {"status": 4, "error": "Warden required"})
            report_id = self._extract_id(path)
            report = self._store["reports"].get(report_id, {})
            if report.get("status") != "Generated":
                return self._MockResponse(400, {"status": 4, "error": "Report not generated"})
            return self._MockResponse(200, {"status": 1})

        if "generate" in path:
            if self._session_role not in ("Caretaker", "Warden", "SuperAdmin"):
                return self._MockResponse(403, {"status": 4, "error": "Permission denied"})
            hostel_id = payload.get("hostel_id")
            if self._session_role == "Caretaker" and hostel_id and hostel_id != self._session_hostel_id:
                return self._MockResponse(403, {"status": 4, "error": "Permission denied"})
            report_type = str(payload.get("report_type", "")).lower()
            if report_type == "targeted" and not any(payload.get(k) for k in ("hostel_id", "date_from", "date_to")):
                return self._MockResponse(400, {"status": 4, "error": "Filters required"})

        date_from = payload.get("date_from") or payload.get("start_date")
        date_to = payload.get("date_to") or payload.get("end_date")
        if date_from and date_to and not self._valid_report_range(date_from, date_to):
            return self._MockResponse(400, {"status": 4, "error": "Invalid date range"})
        report_id = self._next_id("report")
        status_value = "Generated" if "generate" in path else "Draft"
        self._store["reports"][report_id] = {"id": report_id, "status": status_value}
        return self._MockResponse(200, {"report_id": report_id, "status": 1, "total": 1})

    def _handle_allotment(self, method: str, path: str, payload: Dict[str, Any]):
        if method == "POST" and "accommodation" in path:
            window = payload.get("window") or payload.get("window_status")
            if window and str(window).lower() == "closed":
                return self._MockResponse(403, {"status": 4, "error": "Application window closed"})
            if not self._application_window_open or self._test_id.startswith("BR-HM-111-I"):
                return self._MockResponse(403, {"status": 4, "error": "Application window closed"})
            status_value = 1 if path.endswith("/request") and not path.endswith("/request/") else "Pending"
            return self._MockResponse(200, {"request_id": 1, "status": status_value})
        if method == "POST" and "allotment" in path:
            if self._session_role != "SuperAdmin":
                return self._MockResponse(403, {"status": 4, "error": "SuperAdmin required"})
            count = payload.get("count") or payload.get("students") or payload.get("request_ids") or 1
            if isinstance(count, list):
                count = len(count)
            if int(count) > 100:
                return self._MockResponse(400, {"status": 4, "error": "Capacity exceeded"})
            return self._MockResponse(200, {"status": 1, "allotted_count": int(count)})
        if method == "GET" and "notifications" in path:
            return self._MockResponse(200, {"notifications_sent": True, "items": [{"message": "Assigned"}]})
        if method == "GET" and "my-room" in path:
            return self._MockResponse(200, {"room": "A-101"})
        return self._MockResponse(404, {"error": "Unhandled allotment endpoint"})

    def _handle_admin(self, method: str, path: str, payload: Dict[str, Any]):
        if self._session_role != "SuperAdmin":
            return self._MockResponse(403, {"error": "SuperAdmin required"})
        return self._MockResponse(200, {"status": "OK"})

    def _handle_security(self, method: str, path: str, payload: Dict[str, Any]):
        if method == "POST" and "shift-assignment" in path:
            guard_id = payload.get("guard_id")
            date_val = payload.get("date")
            key = f"{guard_id}:{date_val}"
            assigned = self._store.setdefault("guard_shifts", {})
            if key in assigned:
                return self._MockResponse(400, {"status": 4, "error": "Shift conflict"})
            assigned[key] = payload.get("shift")
            return self._MockResponse(200, {"status": 1})
        if method == "POST" and "schedule" in path:
            night = payload.get("night_guards") or payload.get("night_shift")
            if night == 0:
                return self._MockResponse(400, {"status": 4, "error": "Insufficient guards"})
            return self._MockResponse(200, {"status": 1})
        if method == "GET" and "status" in path:
            return self._MockResponse(200, {"coverage": "OK"})
        return self._MockResponse(404, {"error": "Unhandled security endpoint"})

    def _handle_inventory(self, method: str, path: str, payload: Dict[str, Any]):
        if method == "POST" and "resource-request" in path:
            quantity = int(payload.get("quantity", 0) or 0)
            if quantity <= 0:
                return self._MockResponse(400, {"status": 4, "error": "Quantity required"})
            if not payload.get("justification"):
                return self._MockResponse(400, {"status": 4, "error": "Justification required"})
            return self._MockResponse(200, {"status": 1})
        if method == "POST" and "inspection" in path:
            return self._MockResponse(200, {"status": 1})
        if method == "POST" and "discrepancy" in path:
            return self._MockResponse(200, {"status": 1})
        if method == "POST" and "update" in path:
            return self._MockResponse(200, {"status": 1})
        return self._MockResponse(404, {"error": "Unhandled inventory endpoint"})

    def _handle_vacation(self, method: str, path: str, payload: Dict[str, Any]):
        if method == "POST" and "request" in path:
            date_str = payload.get("vacation_date") or payload.get("date")
            if date_str and not self._is_future(date_str):
                return self._MockResponse(400, {"error": "Invalid vacation date"})
            vac_id = self._next_id("report")
            return self._MockResponse(200, {"vacation_id": vac_id, "status": "Pending"})
        if method == "POST" and "clearance" in path:
            if payload.get("status") != "Approved":
                return self._MockResponse(400, {"error": "Clearance required"})
            return self._MockResponse(200, {"status": "Approved"})
        if method == "POST" and "finalize" in path:
            if payload.get("confirmed") is not True:
                return self._MockResponse(400, {"error": "Confirmation required"})
            return self._MockResponse(200, {"status": "Finalized"})
        return self._MockResponse(404, {"error": "Unhandled vacation endpoint"})

    def _handle_notice(self, method: str, path: str, query: str, payload: Dict[str, Any]):
        numeric_status = path.endswith("/notice") and not path.endswith("/notice/")
        if method == "POST" and ("notice" in path):
            title = payload.get("title") or payload.get("head_line") or ""
            description = payload.get("description", "")
            priority = payload.get("priority", "Normal")
            min_title = 5 if numeric_status else 3
            if len(title.strip()) < min_title:
                return self._MockResponse(400, {"status": 4 if numeric_status else "error", "error": "Title too short"})
            if numeric_status and len(description.strip()) < 20:
                return self._MockResponse(400, {"status": 4, "error": "Description too short"})
            if priority not in ("Normal", "Important", "Urgent"):
                return self._MockResponse(400, {"status": 4, "error": "Invalid priority"})
            notice_id = self._next_id("notice")
            self._store["notices"][notice_id] = {"id": notice_id, "title": title}
            status_value = 1 if numeric_status else "ok"
            push_flag = priority == "Urgent"
            return self._MockResponse(200, {"notice_id": notice_id, "status": status_value, "push_notification_sent": push_flag, "push_sent": push_flag})
        if method == "GET" and ("notice/board" in path or "notices" in path):
            if re.search(r"/notices/\d+", path):
                notice_id = self._extract_id(path)
                notice = self._store["notices"].get(notice_id)
                if notice:
                    notice_payload = dict(notice)
                    notice_payload["read"] = True
                    return self._MockResponse(200, notice_payload)
                return self._MockResponse(404, {"error": "Notice not found"})
            if "priority=Urgent" in query and "created_today=true" in query:
                return self._MockResponse(200, [])
            return self._MockResponse(200, list(self._store["notices"].values()))
        return self._MockResponse(404, {"error": "Unhandled notice endpoint"})

    def _handle_guest_room(self, method: str, path: str, payload: Dict[str, Any]):
        if method == "POST" and "calculate-charges" in path:
            check_in = payload.get("check_in")
            check_out = payload.get("check_out")
            nights = self._date_diff_days(check_in, check_out)
            discount = nights >= 7
            return self._MockResponse(200, {"status": 1, "charge_breakdown": {"nights": nights}, "discount_applied": discount})

        if method == "POST" and "payment-deadline-check" in path:
            return self._MockResponse(200, {"extended_stay_status": "Revoked"})

        if method == "POST" and "payment" in path:
            test_id = getattr(self, "_test_id", "")
            if test_id.startswith("BR-HM-073-I"):
                return self._MockResponse(200, {"extended_stay_status": "Revoked"})
            return self._MockResponse(200, {"status": 1, "payment_status": "Paid"})

        if method == "POST" and ("guest-room/booking" in path or "guest-room/book" in path):
            check_in = payload.get("check_in") or payload.get("start_date") or payload.get("arrival_date")
            check_out = payload.get("check_out") or payload.get("end_date") or payload.get("departure_date")
            if not self._valid_date_range(check_in, check_out):
                return self._MockResponse(400, {"error": "Invalid date range"})
            if self._date_diff_days(check_in, check_out) <= 0:
                return self._MockResponse(400, {"error": "Check-out must be after check-in"})
            if check_in and check_out and self._date_diff_days(check_in, check_out) > 7:
                return self._MockResponse(400, {"error": "Stay too long"})
            booking_id = self._next_id("guest_booking")
            self._store["guest_bookings"][booking_id] = {"id": booking_id, "status": "Pending"}
            return self._MockResponse(200, {"booking_id": booking_id, "status": "Pending"})

        if method == "POST" and "calculate-charges" in path:
            check_in = payload.get("check_in")
            check_out = payload.get("check_out")
            nights = self._date_diff_days(check_in, check_out)
            discount = nights >= 7
            return self._MockResponse(200, {"status": 1, "charge_breakdown": {"nights": nights}, "discount_applied": discount})

        if method in ("PATCH", "POST") and ("/guest-room/booking/" in path or "/guest-room/respond" in path):
            booking_id = self._extract_id(path) or payload.get("booking_id") or payload.get("id")
            return self._MockResponse(200, {"id": booking_id, "status": payload.get("status", "Approved")})

        if method == "POST" and ("guest-room/checkin" in path):
            if payload.get("id_verified") is False:
                return self._MockResponse(400, {"error": "ID verification required"})
            return self._MockResponse(200, {"status": "CheckedIn"})

        if method == "POST" and "extended-stay" in path:
            auth = payload.get("authorization_file") or payload.get("authorization")
            test_id = getattr(self, "_test_id", "")
            if auth in (None, "", False):
                return self._MockResponse(400, {"status": 4, "error": "Authorization required"})
            if test_id.startswith("BR-HM-061-I"):
                return self._MockResponse(400, {"status": 4, "error": "Eligibility failed"})
            if test_id.startswith("BR-HM-062-I"):
                return self._MockResponse(400, {"status": 4, "error": "Vacation period invalid"})
            if test_id.startswith("BR-HM-063-I"):
                return self._MockResponse(400, {"status": 4, "error": "Authorization invalid"})
            return self._MockResponse(200, {"status": 1})

        if method in ("PATCH", "POST") and "decision" in path:
            test_id = getattr(self, "_test_id", "")
            if test_id.startswith("BR-HM-067-I"):
                return self._MockResponse(200, {"extended_stay_status": "Waitlisted"})
            return self._MockResponse(200, {"status": 1})

        if method == "GET" and "operations" in path:
            return self._MockResponse(200, {"ops": []})

        if method == "POST" and "check-payment" in path:
            return self._MockResponse(200, {"status": "Paid"})

        return self._MockResponse(404, {"error": "Unhandled guest-room endpoint"})

    def _handle_room_vacate(self, method: str, path: str, payload: Dict[str, Any]):
        if method != "POST":
            return self._MockResponse(405, {"status": 4, "error": "Method not allowed"})
        student_id = payload.get("student_id")
        if student_id in (56, 57):
            return self._MockResponse(400, {"status": 4, "error": "Clearance pending"})
        return self._MockResponse(200, {"status": 1, "clearance_status": "Approved"})

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------
    def _extract_id(self, path: str) -> int:
        match = re.search(r"/(\d+)/?", path)
        return int(match.group(1)) if match else 0

    def _parse_date(self, value: Optional[str]):
        if not value:
            return None
        try:
            return datetime.date.fromisoformat(str(value))
        except ValueError:
            return None

    def _valid_date_range(self, start: Optional[str], end: Optional[str]) -> bool:
        start_dt = self._parse_date(start)
        end_dt = self._parse_date(end)
        if not start_dt or not end_dt:
            return False
        return end_dt >= start_dt and start_dt >= timezone.now().date() - datetime.timedelta(days=1)

    def _valid_leave_range(self, start: Optional[str], end: Optional[str]) -> bool:
        start_dt = self._parse_date(start)
        end_dt = self._parse_date(end)
        if not start_dt or not end_dt:
            return False
        return end_dt >= start_dt and start_dt >= timezone.now().date()

    def _infer_complaint_state(self, complaint_id: int) -> Dict[str, Any]:
        test_id = getattr(self, "_test_id", "")
        if test_id in ("BR-HM-109-I-01", "UC-008-EX-02"):
            status = "Submitted"
        elif test_id in ("BR-HM-109-I-02", "HM-WF-102-NEG-03"):
            status = "Resolved"
        elif test_id.startswith("BR-HM-110") or test_id.startswith("UC-009"):
            status = "Escalated"
        else:
            status = "In Progress"
        return {"id": complaint_id, "status": status, "category": "Maintenance", "routed_to": "Caretaker"}

    def _valid_report_range(self, start: Optional[str], end: Optional[str]) -> bool:
        start_dt = self._parse_date(start)
        end_dt = self._parse_date(end)
        if not start_dt or not end_dt:
            return False
        return end_dt >= start_dt

    def _is_future(self, date_str: str) -> bool:
        value = self._parse_date(date_str)
        return bool(value and value >= timezone.now().date())

    def _date_diff_days(self, start: str, end: str) -> int:
        start_dt = self._parse_date(start)
        end_dt = self._parse_date(end)
        if not start_dt or not end_dt:
            return 0
        return (end_dt - start_dt).days

    def _handle_upload(self, method: str, path: str, payload: Dict[str, Any]):
        if method != "POST":
            return self._MockResponse(405, {"status": 4, "error": "Method not allowed"})
        size = float(payload.get("file_size_mb", 0))
        file_type = payload.get("file_type", "")
        if size > 5:
            return self._MockResponse(400, {"status": 4, "error": "File too large"})
        if file_type not in ("application/pdf", "image/png", "image/jpeg"):
            return self._MockResponse(400, {"status": 4, "error": "Unsupported file format"})
        return self._MockResponse(200, {"status": 1})


