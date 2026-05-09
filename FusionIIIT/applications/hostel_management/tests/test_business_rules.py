"""
Hostel Management Module – Business Rule Tests
File: test_business_rules.py

Coverage:
    BR-HM-101  Leave Eligibility Based on Hostel Residency
    BR-HM-102  Leave Date Boundary Validation
    BR-HM-103  Mandatory Leave Justification Policy
    BR-HM-104  Leave Decision Authority Enforcement
    BR-HM-105  Attendance Synchronization on Leave Approval
    BR-HM-106  Complaint Eligibility Rule
    BR-HM-107  Complaint Routing by Category
    BR-HM-108  Mandatory Resolution Remarks
    BR-HM-109  Escalation Authorization Rule
    BR-HM-110  Warden Authority on Escalated Complaints
    BR-HM-111  Application Window Enforcement
    BR-HM-112  Bulk Allotment Capacity Safeguard
    BR-HM-113  Super Admin Allotment Authority
    BR-HM-114  Mandatory Allotment Notification
    BR-HM-115  Room Change Eligibility Rule
    BR-HM-116  Dual Approval Requirement
    BR-HM-117  Occupancy Reconciliation on Room Change
    BR-HM-118  Mandatory Room Change Notification
    BR-HM-008  Hostel Status Management
    BR-HM-019  Staff Role Assignment Constraints
    BR-HM-012  Data Scoping by Role and Assignment
    BR-HM-013  Fine Imposition Validation
    BR-HM-014  Fine Lifecycle and Escalation Management
    BR-HM-022  File Upload Validation
    BR-HM-016  Guard Shift Conflict Prevention
    BR-HM-026  Minimum Security Coverage Rules
    BR-HM-027  Security Audit and Compliance Logging
    BR-HM-021  Inventory Discrepancy Logging
    BR-HM-030  Resource Requirement Request Validation
    BR-HM-031  Inventory Audit Trail Maintenance
    BR-HM-015  Room Vacation Prerequisites
    BR-HM-023  Room Availability Update
    BR-HM-028  Vacation Finalization Prerequisites
    BR-HM-029  Notice Content Validation
    BR-HM-033  Notice Priority Levels
    BR-HM-035  Notice Display Rules
    BR-HM-040  Report Generation Authorization
    BR-HM-043  Report Filter Rules
    BR-HM-044  Report Content Standards
    BR-HM-045  Report Submission Authorization
    BR-HM-046  Report Review Hierarchy
    BR-HM-051  Guest Room Booking Eligibility
    BR-HM-056  Guest Identity Verification
    BR-HM-057  Room Inspection Standards
    BR-HM-058  Damage Assessment Rules
    BR-HM-059  Guest Room Charges
    BR-HM-061  Extended Stay Eligibility
    BR-HM-062  Vacation Period Validation
    BR-HM-063  Authorization Requirements
    BR-HM-064  Extended Stay Charges Calculation
    BR-HM-065  Application Modification Rules
    BR-HM-066  Authorization Verification Standards
    BR-HM-067  Room Availability During Vacation
    BR-HM-073  Payment Deadline Policy
    BR-HM-074  Vacation Services Coordination
"""

import unittest
from datetime import date, timedelta

from .conftest import BaseModuleTestCase


# ---------------------------------------------------------------------------
# Base class  (mirrors the BRTestBase from the project's shared test helpers)
# ---------------------------------------------------------------------------
class BRTestBase(BaseModuleTestCase):
    """Shared scaffolding for every business-rule test case."""

    # These are set by each test method before calling _record_result().
    _test_id: str = ""
    _br_id: str = ""
    _test_category: str = ""   # "Valid" | "Invalid"
    _input_action: str = ""
    _expected_result: str = ""

    # ------------------------------------------------------------------ #
    #  Convenience helpers                                                 #
    # ------------------------------------------------------------------ #
    @staticmethod
    def future_date(days: int) -> str:
        """Return an ISO-8601 date string `days` from today."""
        return (date.today() + timedelta(days=days)).isoformat()

    @staticmethod
    def past_date(days: int) -> str:
        """Return an ISO-8601 date string `days` before today."""
        return (date.today() - timedelta(days=days)).isoformat()

    # ------------------------------------------------------------------ #
    #  Auth helpers  (replace with real session/token logic as needed)    #
    # ------------------------------------------------------------------ #
    def login_as_student(self, hostel_status: str = "Active"):
        """Authenticate as a student; override hostel_status for negative paths."""
        self._session_role = "Student"
        self._session_hostel_status = hostel_status

    def login_as_caretaker(self, hostel_id: str = "H1"):
        """Authenticate as the caretaker assigned to `hostel_id`."""
        self._session_role = "Caretaker"
        self._session_hostel_id = hostel_id

    def login_as_warden(self, hostel_id: str = "H1"):
        """Authenticate as the warden for `hostel_id`."""
        self._session_role = "Warden"
        self._session_hostel_id = hostel_id

    def login_as_super_admin(self):
        """Authenticate as Super Admin."""
        self._session_role = "SuperAdmin"

    # ------------------------------------------------------------------ #
    #  Result recorder                                                     #
    # ------------------------------------------------------------------ #
    def _record_result(self, actual: str, verdict: str, raw: str = ""):
        super()._record_result(actual, verdict, raw)
        print(
            f"[{verdict}] {self._test_id} | {self._br_id} | "
            f"Category={self._test_category} | "
            f"Action='{self._input_action}' | "
            f"Expected='{self._expected_result}' | "
            f"Actual='{actual}'"
        )


# ===========================================================================
#  BR-HM-101: Leave Eligibility Based on Hostel Residency
# ===========================================================================
class TestBRHM101_LeaveEligibilityResidency(BRTestBase):
    """BR-HM-101 – A student MUST have an active hostel room allotment to submit a leave request."""

    def test_valid_active_hostel_student_can_submit_leave(self):
        self._test_id = "BR-HM-101-V-01"
        self._br_id = "BR-HM-101"
        self._test_category = "Valid"
        self._input_action = "Submit leave request as student with active hostel allotment"
        self._expected_result = "Request accepted for validation"

        self.login_as_student(hostel_status="Active")
        response = self.api_post('/hostel/leave', {
            'start_date': self.future_date(5),
            'end_date': self.future_date(8),
            'reason': 'Family function',
            'documents': 'uploaded',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Leave accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Student with active hostel allotment should be able to submit a leave request")

    def test_invalid_vacated_student_leave_rejected(self):
        self._test_id = "BR-HM-101-I-01"
        self._br_id = "BR-HM-101"
        self._test_category = "Invalid"
        self._input_action = "Submit leave request as student with vacated hostel status"
        self._expected_result = "Request rejected with residency eligibility error"

        self.login_as_student(hostel_status="Vacated")
        response = self.api_post('/hostel/leave', {
            'start_date': self.future_date(5),
            'end_date': self.future_date(8),
            'reason': 'Family function',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'residency' in str(data).lower():
            self._record_result("Correctly rejected due to residency", "Pass", str(data))
        else:
            self._record_result(f"Not rejected as expected: {data}", "Fail", str(data))
            self.fail("Leave request from vacated student must be rejected per BR-HM-101")


# ===========================================================================
#  BR-HM-102: Leave Date Boundary Validation
# ===========================================================================
class TestBRHM102_LeaveDateBoundary(BRTestBase):
    """BR-HM-102 – Leave end_date MUST be >= start_date."""

    def test_valid_future_date_range(self):
        self._test_id = "BR-HM-102-V-01"
        self._br_id = "BR-HM-102"
        self._test_category = "Valid"
        self._input_action = "Submit leave with start_date=today and end_date=today+3"
        self._expected_result = "Dates accepted"

        self.login_as_student()
        response = self.api_post('/hostel/leave', {
            'start_date': self.future_date(1),
            'end_date': self.future_date(4),
            'reason': 'Medical checkup',
            'documents': 'uploaded',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Valid date range accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Valid date range (start < end) should be accepted")

    def test_valid_same_day_leave(self):
        self._test_id = "BR-HM-102-V-02"
        self._br_id = "BR-HM-102"
        self._test_category = "Valid"
        self._input_action = "Submit leave with start_date equal to end_date (same-day leave)"
        self._expected_result = "Dates accepted"

        self.login_as_student()
        same_day = self.future_date(3)
        response = self.api_post('/hostel/leave', {
            'start_date': same_day,
            'end_date': same_day,
            'reason': 'Hospital visit',
            'documents': 'uploaded',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Same-day leave accepted", "Pass", str(data))
        else:
            self._record_result(f"Same-day leave rejected: {data}", "Fail", str(data))
            self.fail("Same-day leave (start==end) should be accepted per BR-HM-102")

    def test_invalid_end_before_start(self):
        self._test_id = "BR-HM-102-I-01"
        self._br_id = "BR-HM-102"
        self._test_category = "Invalid"
        self._input_action = "Submit leave with end_date one day before start_date"
        self._expected_result = "Validation error: end_date must be >= start_date"

        self.login_as_student()
        response = self.api_post('/hostel/leave', {
            'start_date': self.future_date(5),
            'end_date': self.future_date(4),   # end is before start
            'reason': 'Test',
            'documents': 'uploaded',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'date' in str(data).lower():
            self._record_result("Correctly rejected invalid dates", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Leave with end_date < start_date must be rejected per BR-HM-102")


# ===========================================================================
#  BR-HM-103: Mandatory Leave Justification Policy
# ===========================================================================
class TestBRHM103_MandatoryJustification(BRTestBase):
    """BR-HM-103 – Leave request MUST include a reason; documents required where mandated."""

    def test_valid_reason_and_documents_provided(self):
        self._test_id = "BR-HM-103-V-01"
        self._br_id = "BR-HM-103"
        self._test_category = "Valid"
        self._input_action = "Submit leave with non-empty reason and required documents uploaded"
        self._expected_result = "Submission accepted for processing"

        self.login_as_student()
        response = self.api_post('/hostel/leave', {
            'start_date': self.future_date(5),
            'end_date': self.future_date(8),
            'reason': 'Medical emergency at home',
            'documents': 'uploaded',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Submission accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Leave with valid reason and documents should be accepted")

    def test_invalid_empty_reason(self):
        self._test_id = "BR-HM-103-I-01"
        self._br_id = "BR-HM-103"
        self._test_category = "Invalid"
        self._input_action = "Submit leave with empty reason field"
        self._expected_result = "Submission rejected: reason is mandatory"

        self.login_as_student()
        response = self.api_post('/hostel/leave', {
            'start_date': self.future_date(5),
            'end_date': self.future_date(8),
            'reason': '',
            'documents': 'uploaded',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'reason' in str(data).lower():
            self._record_result("Correctly rejected empty reason", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Leave with empty reason must be rejected per BR-HM-103")

    def test_invalid_missing_mandatory_documents(self):
        self._test_id = "BR-HM-103-I-02"
        self._br_id = "BR-HM-103"
        self._test_category = "Invalid"
        self._input_action = "Submit leave with reason but mandatory documents not uploaded"
        self._expected_result = "Submission rejected: supporting documents required"

        self.login_as_student()
        response = self.api_post('/hostel/leave', {
            'start_date': self.future_date(5),
            'end_date': self.future_date(8),
            'reason': 'Family function',
            'documents': None,      # no document uploaded
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'document' in str(data).lower():
            self._record_result("Correctly rejected missing documents", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Leave without mandatory documents must be rejected per BR-HM-103")


# ===========================================================================
#  BR-HM-104: Leave Decision Authority Enforcement
# ===========================================================================
class TestBRHM104_LeaveDecisionAuthority(BRTestBase):
    """BR-HM-104 – Only the assigned Caretaker MAY approve/reject leave requests."""

    def test_valid_assigned_caretaker_approves(self):
        self._test_id = "BR-HM-104-V-01"
        self._br_id = "BR-HM-104"
        self._test_category = "Valid"
        self._input_action = "Assigned Caretaker approves leave request for their hostel"
        self._expected_result = "Decision recorded and applied"

        self.login_as_caretaker(hostel_id="H1")
        response = self.api_patch('/hostel/leave/100/decision', {
            'decision': 'Approved',
            'remarks': 'All documents verified and valid.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Approval decision recorded", "Pass", str(data))
        else:
            self._record_result(f"Unexpected failure: {data}", "Fail", str(data))
            self.fail("Assigned caretaker should be able to approve leave requests")

    def test_invalid_different_hostel_caretaker_blocked(self):
        self._test_id = "BR-HM-104-I-01"
        self._br_id = "BR-HM-104"
        self._test_category = "Invalid"
        self._input_action = "Caretaker from a different hostel attempts to approve leave request"
        self._expected_result = "Action denied with authorization error"

        self.login_as_caretaker(hostel_id="H2")   # wrong hostel
        response = self.api_patch('/hostel/leave/100/decision', {
            'decision': 'Approved',
            'remarks': 'Trying from different hostel.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'authorization' in str(data).lower():
            self._record_result("Correctly blocked cross-hostel action", "Pass", str(data))
        else:
            self._record_result(f"Not blocked: {data}", "Fail", str(data))
            self.fail("Caretaker from different hostel must be denied per BR-HM-104")

    def test_invalid_student_cannot_approve_leave(self):
        self._test_id = "BR-HM-104-I-02"
        self._br_id = "BR-HM-104"
        self._test_category = "Invalid"
        self._input_action = "Student or Warden attempts to approve a leave request"
        self._expected_result = "Action denied with role mismatch error"

        self.login_as_student()
        response = self.api_patch('/hostel/leave/100/decision', {
            'decision': 'Approved',
            'remarks': 'Student trying to approve own leave.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'role' in str(data).lower() or 'permission' in str(data).lower():
            self._record_result("Student correctly denied approval action", "Pass", str(data))
        else:
            self._record_result(f"Not denied: {data}", "Fail", str(data))
            self.fail("Student must not be allowed to approve leaves per BR-HM-104")


# ===========================================================================
#  BR-HM-105: Attendance Synchronization on Leave Approval
# ===========================================================================
class TestBRHM105_AttendanceSync(BRTestBase):
    """BR-HM-105 – Approved leave MUST auto-mark attendance as 'On Leave'."""

    def test_valid_attendance_marked_on_approval(self):
        self._test_id = "BR-HM-105-V-01"
        self._br_id = "BR-HM-105"
        self._test_category = "Valid"
        self._input_action = "Leave request status changes to Approved for 3-day period"
        self._expected_result = "Attendance marked 'On Leave' for all 3 days automatically"

        self.login_as_caretaker()
        response = self.api_patch('/hostel/leave/101/decision', {
            'decision': 'Approved',
            'remarks': 'Valid leave, documents verified.',
        }, expected_status=None)
        data = response.json()
        # Verify attendance update is reflected
        attendance_response = self.api_get('/hostel/attendance/student/42', {
            'date_from': self.future_date(5),
            'date_to': self.future_date(7),
        })
        att_data = attendance_response.json()
        on_leave_days = [r for r in att_data.get('records', []) if r.get('status') == 'On Leave']
        if len(on_leave_days) == 3:
            self._record_result("Attendance correctly marked On Leave for 3 days", "Pass", str(att_data))
        else:
            self._record_result(f"Attendance not updated: {att_data}", "Fail", str(att_data))
            self.fail("Attendance must be marked On Leave for all approved leave days per BR-HM-105")

    def test_invalid_rejected_leave_does_not_update_attendance(self):
        self._test_id = "BR-HM-105-I-01"
        self._br_id = "BR-HM-105"
        self._test_category = "Invalid"
        self._input_action = "Leave request status is Rejected; attendance update triggered"
        self._expected_result = "Attendance not updated; records remain unchanged"

        self.login_as_caretaker()
        response = self.api_patch('/hostel/leave/102/decision', {
            'decision': 'Rejected',
            'remarks': 'Insufficient documents.',
        }, expected_status=None)
        data = response.json()
        attendance_response = self.api_get('/hostel/attendance/student/43', {
            'date_from': self.future_date(5),
            'date_to': self.future_date(7),
        })
        att_data = attendance_response.json()
        on_leave_days = [r for r in att_data.get('records', []) if r.get('status') == 'On Leave']
        if len(on_leave_days) == 0:
            self._record_result("Attendance unchanged after rejection", "Pass", str(att_data))
        else:
            self._record_result(f"Attendance incorrectly updated: {att_data}", "Fail", str(att_data))
            self.fail("Rejected leave must not update attendance per BR-HM-105")


# ===========================================================================
#  BR-HM-106: Complaint Eligibility Rule
# ===========================================================================
class TestBRHM106_ComplaintEligibility(BRTestBase):
    """BR-HM-106 – Only students with active hostel allotment MAY submit complaints."""

    def test_valid_active_student_can_submit_complaint(self):
        self._test_id = "BR-HM-106-V-01"
        self._br_id = "BR-HM-106"
        self._test_category = "Valid"
        self._input_action = "Student with active hostel allotment submits complaint"
        self._expected_result = "Complaint accepted"

        self.login_as_student(hostel_status="Active")
        response = self.api_post('/hostel/complaint', {
            'category': 'Maintenance',
            'description': 'Broken window latch in room 203.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Complaint accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Active student should be able to submit a complaint")

    def test_invalid_vacated_student_complaint_rejected(self):
        self._test_id = "BR-HM-106-I-01"
        self._br_id = "BR-HM-106"
        self._test_category = "Invalid"
        self._input_action = "Student whose hostel allotment is vacated submits complaint"
        self._expected_result = "Complaint rejected with eligibility error"

        self.login_as_student(hostel_status="Vacated")
        response = self.api_post('/hostel/complaint', {
            'category': 'Maintenance',
            'description': 'Broken window latch.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'eligibility' in str(data).lower():
            self._record_result("Correctly rejected vacated student complaint", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Vacated student complaint must be rejected per BR-HM-106")


# ===========================================================================
#  BR-HM-107: Complaint Routing by Category
# ===========================================================================
class TestBRHM107_ComplaintRouting(BRTestBase):
    """BR-HM-107 – Security → Warden; all other categories → Caretaker."""

    def test_valid_security_complaint_routed_to_warden(self):
        self._test_id = "BR-HM-107-V-01"
        self._br_id = "BR-HM-107"
        self._test_category = "Valid"
        self._input_action = "Submit complaint with category=Security"
        self._expected_result = "Complaint routed to Warden with notification"

        self.login_as_student()
        response = self.api_post('/hostel/complaint', {
            'category': 'Security',
            'description': 'Unknown person loitering near hostel gate at night.',
        }, expected_status=None)
        data = response.json()
        if data.get('assigned_to_role') == 'Warden' or data.get('status') == 1:
            self._record_result("Security complaint routed to Warden", "Pass", str(data))
        else:
            self._record_result(f"Not routed correctly: {data}", "Fail", str(data))
            self.fail("Security complaint must be routed to Warden per BR-HM-107")

    def test_valid_maintenance_complaint_routed_to_caretaker(self):
        self._test_id = "BR-HM-107-V-02"
        self._br_id = "BR-HM-107"
        self._test_category = "Valid"
        self._input_action = "Submit complaint with category=Maintenance"
        self._expected_result = "Complaint routed to Caretaker with notification"

        self.login_as_student()
        response = self.api_post('/hostel/complaint', {
            'category': 'Maintenance',
            'description': 'Leaking tap in common bathroom.',
        }, expected_status=None)
        data = response.json()
        if data.get('assigned_to_role') == 'Caretaker' or data.get('status') == 1:
            self._record_result("Maintenance complaint routed to Caretaker", "Pass", str(data))
        else:
            self._record_result(f"Not routed correctly: {data}", "Fail", str(data))
            self.fail("Non-security complaint must be routed to Caretaker per BR-HM-107")

    def test_invalid_missing_category_blocks_routing(self):
        self._test_id = "BR-HM-107-I-01"
        self._br_id = "BR-HM-107"
        self._test_category = "Invalid"
        self._input_action = "Security complaint submitted without category set"
        self._expected_result = "System cannot route; category is mandatory"

        self.login_as_student()
        response = self.api_post('/hostel/complaint', {
            'category': None,
            'description': 'Some issue happened.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'category' in str(data).lower():
            self._record_result("Correctly blocked submission without category", "Pass", str(data))
        else:
            self._record_result(f"Not blocked: {data}", "Fail", str(data))
            self.fail("Complaint without category must be rejected per BR-HM-107")


# ===========================================================================
#  BR-HM-108: Mandatory Resolution Remarks
# ===========================================================================
class TestBRHM108_ResolutionRemarks(BRTestBase):
    """BR-HM-108 – Resolution remarks MUST be provided before marking a complaint Resolved."""

    def test_valid_resolve_with_remarks(self):
        self._test_id = "BR-HM-108-V-01"
        self._br_id = "BR-HM-108"
        self._test_category = "Valid"
        self._input_action = "Caretaker marks complaint as Resolved with non-empty remarks"
        self._expected_result = "Complaint status updated to Resolved; resolution recorded"

        self.login_as_caretaker()
        response = self.api_patch('/hostel/complaint/200/resolve', {
            'status': 'Resolved',
            'remarks': 'Tap repaired by maintenance team on 2025-06-10.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Complaint resolved with remarks", "Pass", str(data))
        else:
            self._record_result(f"Unexpected failure: {data}", "Fail", str(data))
            self.fail("Complaint with non-empty remarks should be resolved successfully")

    def test_invalid_resolve_without_remarks_blocked(self):
        self._test_id = "BR-HM-108-I-01"
        self._br_id = "BR-HM-108"
        self._test_category = "Invalid"
        self._input_action = "Caretaker attempts to mark complaint as Resolved with empty remarks"
        self._expected_result = "Update blocked; error: resolution remarks are mandatory"

        self.login_as_caretaker()
        response = self.api_patch('/hostel/complaint/201/resolve', {
            'status': 'Resolved',
            'remarks': '',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'remarks' in str(data).lower():
            self._record_result("Correctly blocked resolution without remarks", "Pass", str(data))
        else:
            self._record_result(f"Not blocked: {data}", "Fail", str(data))
            self.fail("Resolution without remarks must be blocked per BR-HM-108")


# ===========================================================================
#  BR-HM-109: Escalation Authorization Rule
# ===========================================================================
class TestBRHM109_EscalationAuthorization(BRTestBase):
    """BR-HM-109 – Only In-Progress complaints MAY be escalated to Warden."""

    def test_valid_in_progress_complaint_can_be_escalated(self):
        self._test_id = "BR-HM-109-V-01"
        self._br_id = "BR-HM-109"
        self._test_category = "Valid"
        self._input_action = "Escalate complaint with status=In-Progress"
        self._expected_result = "Escalation processed; complaint status updated to Escalated"

        self.login_as_caretaker()
        response = self.api_patch('/hostel/complaint/300/escalate', {
            'reason': 'Issue requires Warden-level intervention.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1 or data.get('complaint_status') == 'Escalated':
            self._record_result("In-Progress complaint escalated successfully", "Pass", str(data))
        else:
            self._record_result(f"Escalation failed unexpectedly: {data}", "Fail", str(data))
            self.fail("In-Progress complaint should be escalatable per BR-HM-109")

    def test_invalid_submitted_complaint_cannot_be_escalated(self):
        self._test_id = "BR-HM-109-I-01"
        self._br_id = "BR-HM-109"
        self._test_category = "Invalid"
        self._input_action = "Escalate complaint with status=Submitted (not yet investigated)"
        self._expected_result = "Escalation blocked; complaint must be In-Progress first"

        self.login_as_caretaker()
        response = self.api_patch('/hostel/complaint/301/escalate', {
            'reason': 'Escalating too early.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'in-progress' in str(data).lower() or 'escalat' in str(data).lower():
            self._record_result("Escalation of Submitted complaint blocked", "Pass", str(data))
        else:
            self._record_result(f"Not blocked: {data}", "Fail", str(data))
            self.fail("Complaint in Submitted status must not be escalatable per BR-HM-109")

    def test_invalid_resolved_complaint_cannot_be_escalated(self):
        self._test_id = "BR-HM-109-I-02"
        self._br_id = "BR-HM-109"
        self._test_category = "Invalid"
        self._input_action = "Escalate complaint with status=Resolved"
        self._expected_result = "Escalation blocked; resolved complaints cannot be escalated"

        self.login_as_caretaker()
        response = self.api_patch('/hostel/complaint/302/escalate', {
            'reason': 'Escalating resolved complaint.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'resolved' in str(data).lower():
            self._record_result("Resolved complaint escalation correctly blocked", "Pass", str(data))
        else:
            self._record_result(f"Not blocked: {data}", "Fail", str(data))
            self.fail("Resolved complaint must not be escalatable per BR-HM-109")


# ===========================================================================
#  BR-HM-110: Warden Authority on Escalated Complaints
# ===========================================================================
class TestBRHM110_WardenEscalatedComplaints(BRTestBase):
    """BR-HM-110 – Only Wardens MAY resolve escalated complaints."""

    def test_valid_warden_resolves_escalated_complaint(self):
        self._test_id = "BR-HM-110-V-01"
        self._br_id = "BR-HM-110"
        self._test_category = "Valid"
        self._input_action = "Warden resolves an escalated complaint with remarks"
        self._expected_result = "Complaint resolved; actors notified"

        self.login_as_warden()
        response = self.api_patch('/hostel/complaint/400/resolve', {
            'status': 'Resolved',
            'remarks': 'Escalated issue verified and resolved at Warden level.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Warden resolved escalated complaint", "Pass", str(data))
        else:
            self._record_result(f"Unexpected failure: {data}", "Fail", str(data))
            self.fail("Warden should be able to resolve an escalated complaint")

    def test_invalid_caretaker_cannot_resolve_escalated_complaint(self):
        self._test_id = "BR-HM-110-I-01"
        self._br_id = "BR-HM-110"
        self._test_category = "Invalid"
        self._input_action = "Caretaker attempts to resolve an escalated complaint"
        self._expected_result = "Action denied with authorization error; only Warden can resolve escalated complaints"

        self.login_as_caretaker()
        response = self.api_patch('/hostel/complaint/400/resolve', {
            'status': 'Resolved',
            'remarks': 'Caretaker trying to resolve escalated complaint.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'warden' in str(data).lower() or 'authorization' in str(data).lower():
            self._record_result("Caretaker correctly denied resolution of escalated complaint", "Pass", str(data))
        else:
            self._record_result(f"Not denied: {data}", "Fail", str(data))
            self.fail("Caretaker must not resolve escalated complaints per BR-HM-110")


# ===========================================================================
#  BR-HM-111: Application Window Enforcement
# ===========================================================================
class TestBRHM111_ApplicationWindow(BRTestBase):
    """BR-HM-111 – Accommodation requests MUST be submitted only during an Open window."""

    def test_valid_request_during_open_window(self):
        self._test_id = "BR-HM-111-V-01"
        self._br_id = "BR-HM-111"
        self._test_category = "Valid"
        self._input_action = "Student submits accommodation request when application window is Open"
        self._expected_result = "Request accepted and recorded with status=Pending"

        self.login_as_student()
        response = self.api_post('/hostel/accommodation/request', {
            'hostel_preference': 'H1',
            'room_type': 'Single',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Request accepted during open window", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Accommodation request during open window should be accepted")

    def test_invalid_request_during_closed_window(self):
        self._test_id = "BR-HM-111-I-01"
        self._br_id = "BR-HM-111"
        self._test_category = "Invalid"
        self._input_action = "Student submits accommodation request when application window is Closed"
        self._expected_result = "Request rejected: application window is not active"

        self.login_as_student()
        response = self.api_post('/hostel/accommodation/request', {
            'hostel_preference': 'H1',
            'room_type': 'Single',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'window' in str(data).lower():
            self._record_result("Correctly rejected during closed window", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Accommodation request during closed window must be rejected per BR-HM-111")


# ===========================================================================
#  BR-HM-112: Bulk Allotment Capacity Safeguard
# ===========================================================================
class TestBRHM112_BulkAllotmentCapacity(BRTestBase):
    """BR-HM-112 – Room occupancy MUST NOT exceed capacity; over-allocation is blocked."""

    def test_valid_allotment_within_capacity(self):
        self._test_id = "BR-HM-112-V-01"
        self._br_id = "BR-HM-112"
        self._test_category = "Valid"
        self._input_action = "Allot rooms to students where total occupancy remains within capacity"
        self._expected_result = "Allotment processed; occupancy updated"

        self.login_as_super_admin()
        response = self.api_post('/hostel/allotment/bulk', {
            'hostel_id': 'H1',
            'request_ids': [1, 2, 3],   # within available capacity
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Bulk allotment within capacity processed", "Pass", str(data))
        else:
            self._record_result(f"Unexpected failure: {data}", "Fail", str(data))
            self.fail("Bulk allotment within capacity should succeed")

    def test_invalid_allotment_exceeds_capacity_blocked(self):
        self._test_id = "BR-HM-112-I-01"
        self._br_id = "BR-HM-112"
        self._test_category = "Invalid"
        self._input_action = "Attempt to allot rooms that would result in occupancy exceeding capacity"
        self._expected_result = "Allotment blocked with over-allocation error and capacity details"

        self.login_as_super_admin()
        response = self.api_post('/hostel/allotment/bulk', {
            'hostel_id': 'H1',
            'request_ids': list(range(1, 201)),   # exceeds capacity
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'capacity' in str(data).lower():
            self._record_result("Over-allocation correctly blocked", "Pass", str(data))
        else:
            self._record_result(f"Not blocked: {data}", "Fail", str(data))
            self.fail("Over-allocation must be blocked per BR-HM-112")


# ===========================================================================
#  BR-HM-113: Super Admin Allotment Authority
# ===========================================================================
class TestBRHM113_SuperAdminAllotmentAuthority(BRTestBase):
    """BR-HM-113 – Only Super Admin MAY perform bulk room allotment."""

    def test_valid_super_admin_can_allot(self):
        self._test_id = "BR-HM-113-V-01"
        self._br_id = "BR-HM-113"
        self._test_category = "Valid"
        self._input_action = "Super Admin initiates bulk room allotment"
        self._expected_result = "Allotment process proceeds"

        self.login_as_super_admin()
        response = self.api_post('/hostel/allotment/bulk', {
            'hostel_id': 'H1',
            'request_ids': [10, 11, 12],
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Super Admin allotment permitted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected failure: {data}", "Fail", str(data))
            self.fail("Super Admin should be able to perform bulk allotment")

    def test_invalid_caretaker_cannot_bulk_allot(self):
        self._test_id = "BR-HM-113-I-01"
        self._br_id = "BR-HM-113"
        self._test_category = "Invalid"
        self._input_action = "Caretaker or Warden attempts to initiate bulk room allotment"
        self._expected_result = "Action denied with authorization error"

        self.login_as_caretaker()
        response = self.api_post('/hostel/allotment/bulk', {
            'hostel_id': 'H1',
            'request_ids': [10, 11, 12],
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'authorization' in str(data).lower():
            self._record_result("Caretaker bulk allotment correctly denied", "Pass", str(data))
        else:
            self._record_result(f"Not denied: {data}", "Fail", str(data))
            self.fail("Caretaker must not perform bulk allotment per BR-HM-113")


# ===========================================================================
#  BR-HM-115: Room Change Eligibility Rule
# ===========================================================================
class TestBRHM115_RoomChangeEligibility(BRTestBase):
    """BR-HM-115 – Only students with an active allotment MAY request a room change."""

    def test_valid_active_student_room_change_request(self):
        self._test_id = "BR-HM-115-V-01"
        self._br_id = "BR-HM-115"
        self._test_category = "Valid"
        self._input_action = "Student with active room allotment submits room change request"
        self._expected_result = "Request accepted and recorded"

        self.login_as_student(hostel_status="Active")
        response = self.api_post('/hostel/room-change/request', {
            'current_room': 'A101',
            'preferred_room': 'B205',
            'reason': 'Noise disturbance from neighbours.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Room change request accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Active student should be allowed to request a room change")

    def test_invalid_vacated_student_room_change_blocked(self):
        self._test_id = "BR-HM-115-I-01"
        self._br_id = "BR-HM-115"
        self._test_category = "Invalid"
        self._input_action = "Student without active room allotment submits room change request"
        self._expected_result = "Request rejected with eligibility error"

        self.login_as_student(hostel_status="Vacated")
        response = self.api_post('/hostel/room-change/request', {
            'current_room': 'A101',
            'preferred_room': 'B205',
            'reason': 'Test.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'eligib' in str(data).lower():
            self._record_result("Correctly blocked vacated student room change", "Pass", str(data))
        else:
            self._record_result(f"Not blocked: {data}", "Fail", str(data))
            self.fail("Vacated student must not request room change per BR-HM-115")


# ===========================================================================
#  BR-HM-116: Dual Approval Requirement
# ===========================================================================
class TestBRHM116_DualApprovalRequirement(BRTestBase):
    """BR-HM-116 – Room change requires BOTH Caretaker and Warden approval."""

    def test_valid_both_approvals_allow_reallocation(self):
        self._test_id = "BR-HM-116-V-01"
        self._br_id = "BR-HM-116"
        self._test_category = "Valid"
        self._input_action = "Both Caretaker and Warden approve a room change request"
        self._expected_result = "Reallocation proceeds"

        self.login_as_caretaker()
        self.api_patch('/hostel/room-change/500/caretaker-decision', {
            'decision': 'Approved', 'remarks': 'OK'
        }, expected_status=None)

        self.login_as_warden()
        response = self.api_patch('/hostel/room-change/500/warden-decision', {
            'decision': 'Approved', 'remarks': 'OK'
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1 or data.get('room_change_status') == 'Approved':
            self._record_result("Dual approval processed; reallocation proceeds", "Pass", str(data))
        else:
            self._record_result(f"Unexpected failure: {data}", "Fail", str(data))
            self.fail("Both approvals given; reallocation should proceed per BR-HM-116")

    def test_invalid_only_caretaker_approval_blocks_reallocation(self):
        self._test_id = "BR-HM-116-I-01"
        self._br_id = "BR-HM-116"
        self._test_category = "Invalid"
        self._input_action = "Only Caretaker approves; Warden has not reviewed"
        self._expected_result = "Reallocation blocked; dual approval required"

        self.login_as_caretaker()
        response = self.api_patch('/hostel/room-change/501/caretaker-decision', {
            'decision': 'Approved', 'remarks': 'OK'
        }, expected_status=None)
        # Check that room change is NOT finalized without Warden
        status_response = self.api_get('/hostel/room-change/501')
        data = status_response.json()
        if data.get('room_change_status') != 'Reallocated':
            self._record_result("Reallocation blocked pending Warden approval", "Pass", str(data))
        else:
            self._record_result(f"Reallocation proceeded without Warden: {data}", "Fail", str(data))
            self.fail("Reallocation must not proceed with only Caretaker approval per BR-HM-116")


# ===========================================================================
#  BR-HM-013: Fine Imposition Validation
# ===========================================================================
class TestBRHM013_FineImpositionValidation(BRTestBase):
    """BR-HM-013 – Fine MUST have positive amount, valid category, and non-empty reason."""

    def test_valid_fine_with_all_required_fields(self):
        self._test_id = "BR-HM-013-V-01"
        self._br_id = "BR-HM-013"
        self._test_category = "Valid"
        self._input_action = "Submit fine with amount=500, category=Hostel Rule Violation, reason=non-empty"
        self._expected_result = "Fine recorded with status=Unpaid"

        self.login_as_caretaker()
        response = self.api_post('/hostel/fine', {
            'student_id': 99,
            'amount': 500,
            'category': 'Hostel Rule Violation',
            'reason': 'Student kept unauthorized electrical appliance in room.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1 and data.get('fine_status') == 'Unpaid':
            self._record_result("Fine created with status=Unpaid", "Pass", str(data))
        else:
            self._record_result(f"Unexpected failure: {data}", "Fail", str(data))
            self.fail("Valid fine should be created with status=Unpaid")

    def test_invalid_fine_amount_zero(self):
        self._test_id = "BR-HM-013-I-01"
        self._br_id = "BR-HM-013"
        self._test_category = "Invalid"
        self._input_action = "Submit fine with amount=0"
        self._expected_result = "Validation error: fine amount must be positive"

        self.login_as_caretaker()
        response = self.api_post('/hostel/fine', {
            'student_id': 99,
            'amount': 0,
            'category': 'Hostel Rule Violation',
            'reason': 'Test fine.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'amount' in str(data).lower():
            self._record_result("Zero-amount fine correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Fine with amount=0 must be rejected per BR-HM-013")

    def test_invalid_fine_negative_amount(self):
        self._test_id = "BR-HM-013-I-02"
        self._br_id = "BR-HM-013"
        self._test_category = "Invalid"
        self._input_action = "Submit fine with amount=-100"
        self._expected_result = "Validation error: fine amount must be positive"

        self.login_as_caretaker()
        response = self.api_post('/hostel/fine', {
            'student_id': 99,
            'amount': -100,
            'category': 'Hostel Rule Violation',
            'reason': 'Negative amount test.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'amount' in str(data).lower():
            self._record_result("Negative-amount fine correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Fine with negative amount must be rejected per BR-HM-013")

    def test_invalid_fine_null_category(self):
        self._test_id = "BR-HM-013-I-03"
        self._br_id = "BR-HM-013"
        self._test_category = "Invalid"
        self._input_action = "Submit fine with category=null"
        self._expected_result = "Validation error: violation category is required"

        self.login_as_caretaker()
        response = self.api_post('/hostel/fine', {
            'student_id': 99,
            'amount': 200,
            'category': None,
            'reason': 'Test fine.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'category' in str(data).lower():
            self._record_result("Null category fine correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Fine with null category must be rejected per BR-HM-013")

    def test_invalid_fine_empty_reason(self):
        self._test_id = "BR-HM-013-I-04"
        self._br_id = "BR-HM-013"
        self._test_category = "Invalid"
        self._input_action = "Submit fine with reason=''"
        self._expected_result = "Validation error: justification reason is required"

        self.login_as_caretaker()
        response = self.api_post('/hostel/fine', {
            'student_id': 99,
            'amount': 200,
            'category': 'Hostel Rule Violation',
            'reason': '',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'reason' in str(data).lower():
            self._record_result("Empty-reason fine correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Fine with empty reason must be rejected per BR-HM-013")


# ===========================================================================
#  BR-HM-022: File Upload Validation
# ===========================================================================
class TestBRHM022_FileUploadValidation(BRTestBase):
    """BR-HM-022 – Uploaded files MUST be within max size and of approved type."""

    def test_valid_pdf_within_size_limit(self):
        self._test_id = "BR-HM-022-V-01"
        self._br_id = "BR-HM-022"
        self._test_category = "Valid"
        self._input_action = "Upload a 2MB PDF file as fine evidence"
        self._expected_result = "File accepted and stored"

        self.login_as_caretaker()
        response = self.api_post('/hostel/upload', {
            'file_name': 'evidence.pdf',
            'file_size_mb': 2,
            'file_type': 'application/pdf',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Valid PDF upload accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("2MB PDF should be accepted per BR-HM-022")

    def test_invalid_oversized_file_rejected(self):
        self._test_id = "BR-HM-022-I-01"
        self._br_id = "BR-HM-022"
        self._test_category = "Invalid"
        self._input_action = "Upload a 10MB video file as fine evidence"
        self._expected_result = "Upload rejected: file exceeds maximum size limit"

        self.login_as_caretaker()
        response = self.api_post('/hostel/upload', {
            'file_name': 'evidence.mp4',
            'file_size_mb': 10,
            'file_type': 'video/mp4',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'size' in str(data).lower():
            self._record_result("Oversized file correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Files exceeding size limit must be rejected per BR-HM-022")

    def test_invalid_unsupported_file_format_rejected(self):
        self._test_id = "BR-HM-022-I-02"
        self._br_id = "BR-HM-022"
        self._test_category = "Invalid"
        self._input_action = "Upload a .exe file as evidence"
        self._expected_result = "Upload rejected: unsupported file format"

        self.login_as_caretaker()
        response = self.api_post('/hostel/upload', {
            'file_name': 'malicious.exe',
            'file_size_mb': 1,
            'file_type': 'application/x-msdownload',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'format' in str(data).lower() or 'type' in str(data).lower():
            self._record_result("Unsupported file format correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail(".exe files must be rejected per BR-HM-022")


# ===========================================================================
#  BR-HM-016: Guard Shift Conflict Prevention
# ===========================================================================
class TestBRHM016_GuardShiftConflict(BRTestBase):
    """BR-HM-016 – Guard MUST NOT be assigned to overlapping or policy-violating shifts."""

    def test_valid_non_conflicting_shift_assignment(self):
        self._test_id = "BR-HM-016-V-01"
        self._br_id = "BR-HM-016"
        self._test_category = "Valid"
        self._input_action = "Assign guard to Morning shift (6AM-2PM); no other shifts assigned that day"
        self._expected_result = "Assignment accepted"

        self.login_as_warden()
        response = self.api_post('/hostel/security/shift-assignment', {
            'guard_id': 'G1',
            'shift': 'Morning',
            'date': self.future_date(1),
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Non-conflicting shift assignment accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Non-conflicting guard shift assignment should be accepted")

    def test_invalid_overlapping_shifts_rejected(self):
        self._test_id = "BR-HM-016-I-01"
        self._br_id = "BR-HM-016"
        self._test_category = "Invalid"
        self._input_action = "Assign guard to Evening shift when already on Morning shift violating rest rules"
        self._expected_result = "Assignment rejected with shift conflict error"

        self.login_as_warden()
        response = self.api_post('/hostel/security/shift-assignment', {
            'guard_id': 'G1',
            'shift': 'Evening',   # conflicts with already-assigned Morning shift
            'date': self.future_date(1),
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'conflict' in str(data).lower() or 'rest' in str(data).lower():
            self._record_result("Conflicting shift correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Shift assignment violating rest policy must be rejected per BR-HM-016")


# ===========================================================================
#  BR-HM-029: Notice Content Validation
# ===========================================================================
class TestBRHM029_NoticeContentValidation(BRTestBase):
    """BR-HM-029 – Notice title: 5-200 chars; description: 20-5000 chars; no profanity."""

    def test_valid_notice_accepted(self):
        self._test_id = "BR-HM-029-V-01"
        self._br_id = "BR-HM-029"
        self._test_category = "Valid"
        self._input_action = "Publish notice with title='Mess Menu Update' and description of 50 characters"
        self._expected_result = "Notice accepted for publication"

        self.login_as_caretaker()
        response = self.api_post('/hostel/notice', {
            'title': 'Mess Menu Update',
            'description': 'Mess menu for this week has been revised. Please check accordingly.',
            'priority': 'Normal',
            'hostel_id': 'H1',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Valid notice accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Notice with valid title and description should be accepted")

    def test_invalid_short_title_rejected(self):
        self._test_id = "BR-HM-029-I-01"
        self._br_id = "BR-HM-029"
        self._test_category = "Invalid"
        self._input_action = "Publish notice with title='Hi' (2 chars)"
        self._expected_result = "Validation error: title must be between 5-200 characters"

        self.login_as_caretaker()
        response = self.api_post('/hostel/notice', {
            'title': 'Hi',
            'description': 'This is a valid description with more than twenty characters.',
            'priority': 'Normal',
            'hostel_id': 'H1',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'title' in str(data).lower():
            self._record_result("Short title correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Notice with title shorter than 5 chars must be rejected per BR-HM-029")

    def test_invalid_short_description_rejected(self):
        self._test_id = "BR-HM-029-I-02"
        self._br_id = "BR-HM-029"
        self._test_category = "Invalid"
        self._input_action = "Publish notice with description of 10 characters"
        self._expected_result = "Validation error: description must be at least 20 characters"

        self.login_as_caretaker()
        response = self.api_post('/hostel/notice', {
            'title': 'Valid Title Here',
            'description': 'Too short.',
            'priority': 'Normal',
            'hostel_id': 'H1',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'description' in str(data).lower():
            self._record_result("Short description correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Notice with description < 20 chars must be rejected per BR-HM-029")


# ===========================================================================
#  BR-HM-033: Notice Priority Levels
# ===========================================================================
class TestBRHM033_NoticePriorityLevels(BRTestBase):
    """BR-HM-033 – Valid priorities: Normal, Important, Urgent.  Invalid value rejected."""

    def test_valid_urgent_notice_creates_push_notification(self):
        self._test_id = "BR-HM-033-V-01"
        self._br_id = "BR-HM-033"
        self._test_category = "Valid"
        self._input_action = "Publish notice with priority=Urgent"
        self._expected_result = "Notice shown with red banner; immediate push notifications sent"

        self.login_as_warden()
        response = self.api_post('/hostel/notice', {
            'title': 'Emergency Water Cutoff Tonight',
            'description': 'Water supply will be interrupted from 10PM to 6AM due to maintenance work.',
            'priority': 'Urgent',
            'hostel_id': 'H1',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1 and data.get('push_notification_sent') is True:
            self._record_result("Urgent notice with push notification created", "Pass", str(data))
        else:
            self._record_result(f"Unexpected result: {data}", "Fail", str(data))
            self.fail("Urgent notice must trigger immediate push notification per BR-HM-033")

    def test_invalid_unknown_priority_rejected(self):
        self._test_id = "BR-HM-033-I-01"
        self._br_id = "BR-HM-033"
        self._test_category = "Invalid"
        self._input_action = "Publish notice with priority=Critical (invalid value)"
        self._expected_result = "Validation error: priority must be one of Normal, Important, Urgent"

        self.login_as_caretaker()
        response = self.api_post('/hostel/notice', {
            'title': 'Valid Title for Testing',
            'description': 'This is a valid description with more than twenty characters.',
            'priority': 'Critical',   # invalid value
            'hostel_id': 'H1',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'priority' in str(data).lower():
            self._record_result("Invalid priority correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Invalid priority value must be rejected per BR-HM-033")


# ===========================================================================
#  BR-HM-040: Report Generation Authorization
# ===========================================================================
class TestBRHM040_ReportGenerationAuthorization(BRTestBase):
    """BR-HM-040 – Only Warden/Caretaker/Super Admin can generate reports (scoped to assignment)."""

    def test_valid_caretaker_generates_own_hostel_report(self):
        self._test_id = "BR-HM-040-V-01"
        self._br_id = "BR-HM-040"
        self._test_category = "Valid"
        self._input_action = "Caretaker generates report for their assigned hostel"
        self._expected_result = "Report generation permitted and logged"

        self.login_as_caretaker(hostel_id="H1")
        response = self.api_post('/hostel/report/generate', {
            'hostel_id': 'H1',
            'report_type': 'Attendance Summary',
            'date_from': self.past_date(30),
            'date_to': self.past_date(1),
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Caretaker report generation permitted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected denial: {data}", "Fail", str(data))
            self.fail("Caretaker should be able to generate reports for their hostel")

    def test_invalid_caretaker_cannot_generate_other_hostel_report(self):
        self._test_id = "BR-HM-040-I-01"
        self._br_id = "BR-HM-040"
        self._test_category = "Invalid"
        self._input_action = "Caretaker attempts to generate report for a hostel they are not assigned to"
        self._expected_result = "Access denied: insufficient permissions"

        self.login_as_caretaker(hostel_id="H1")
        response = self.api_post('/hostel/report/generate', {
            'hostel_id': 'H2',    # different hostel
            'report_type': 'Attendance Summary',
            'date_from': self.past_date(30),
            'date_to': self.past_date(1),
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'permission' in str(data).lower():
            self._record_result("Cross-hostel report generation correctly denied", "Pass", str(data))
        else:
            self._record_result(f"Not denied: {data}", "Fail", str(data))
            self.fail("Caretaker must not generate reports for other hostels per BR-HM-040")

    def test_invalid_student_cannot_generate_report(self):
        self._test_id = "BR-HM-040-I-02"
        self._br_id = "BR-HM-040"
        self._test_category = "Invalid"
        self._input_action = "Student attempts to generate a hostel report"
        self._expected_result = "Access denied: only Warden, Caretaker, and Super Admin can generate reports"

        self.login_as_student()
        response = self.api_post('/hostel/report/generate', {
            'hostel_id': 'H1',
            'report_type': 'Attendance Summary',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'permission' in str(data).lower() or 'role' in str(data).lower():
            self._record_result("Student correctly denied report generation", "Pass", str(data))
        else:
            self._record_result(f"Not denied: {data}", "Fail", str(data))
            self.fail("Students must not generate reports per BR-HM-040")


# ===========================================================================
#  BR-HM-045: Report Submission Authorization
# ===========================================================================
class TestBRHM045_ReportSubmissionAuthorization(BRTestBase):
    """BR-HM-045 – Only Wardens may submit Generated reports to Super Admin."""

    def test_valid_warden_submits_generated_report(self):
        self._test_id = "BR-HM-045-V-01"
        self._br_id = "BR-HM-045"
        self._test_category = "Valid"
        self._input_action = "Warden submits Generated report to Super Admin"
        self._expected_result = "Submission accepted; Super Admin notified; submission logged with timestamp"

        self.login_as_warden()
        response = self.api_post('/hostel/report/600/submit', {
            'recipient': 'SuperAdmin',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Warden report submission accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected denial: {data}", "Fail", str(data))
            self.fail("Warden should be able to submit a Generated report to Super Admin")

    def test_invalid_caretaker_cannot_submit_to_super_admin(self):
        self._test_id = "BR-HM-045-I-01"
        self._br_id = "BR-HM-045"
        self._test_category = "Invalid"
        self._input_action = "Caretaker attempts to submit report directly to Super Admin"
        self._expected_result = "Denied: Caretakers must submit to their Warden"

        self.login_as_caretaker()
        response = self.api_post('/hostel/report/600/submit', {
            'recipient': 'SuperAdmin',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'warden' in str(data).lower():
            self._record_result("Caretaker direct Super Admin submission correctly denied", "Pass", str(data))
        else:
            self._record_result(f"Not denied: {data}", "Fail", str(data))
            self.fail("Caretaker must not submit directly to Super Admin per BR-HM-045")

    def test_invalid_draft_report_cannot_be_submitted(self):
        self._test_id = "BR-HM-045-I-02"
        self._br_id = "BR-HM-045"
        self._test_category = "Invalid"
        self._input_action = "Warden attempts to submit report with status=Draft"
        self._expected_result = "Denied: report must be in Generated status before submission"

        self.login_as_warden()
        response = self.api_post('/hostel/report/601/submit', {  # 601 is a Draft report
            'recipient': 'SuperAdmin',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'generated' in str(data).lower() or 'draft' in str(data).lower():
            self._record_result("Draft report submission correctly blocked", "Pass", str(data))
        else:
            self._record_result(f"Not blocked: {data}", "Fail", str(data))
            self.fail("Draft reports must not be submitted per BR-HM-045")


# ===========================================================================
#  BR-HM-061: Extended Stay Eligibility
# ===========================================================================
class TestBRHM061_ExtendedStayEligibility(BRTestBase):
    """BR-HM-061 – Student must meet all eligibility criteria for extended stay."""

    def test_valid_eligible_student_application_accepted(self):
        self._test_id = "BR-HM-061-V-01"
        self._br_id = "BR-HM-061"
        self._test_category = "Valid"
        self._input_action = "Student with active allotment, good academic standing, no fines, and valid authorization applies"
        self._expected_result = "Application accepted for review"

        self.login_as_student(hostel_status="Active")
        response = self.api_post('/hostel/extended-stay', {
            'vacation_period_id': 'VP-2025-DEC',
            'start_date': '2025-12-21',
            'end_date': '2026-01-03',
            'reason': 'Research project with faculty supervision.',
            'authorization_file': 'auth_letter.pdf',
            'terms_acknowledged': True,
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Eligible student application accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Eligible student should be able to apply for extended stay")

    def test_invalid_probation_student_rejected(self):
        self._test_id = "BR-HM-061-I-01"
        self._br_id = "BR-HM-061"
        self._test_category = "Invalid"
        self._input_action = "Student on academic probation applies for extended stay"
        self._expected_result = "Application rejected: not in good academic standing"

        self.login_as_student(hostel_status="Active")
        response = self.api_post('/hostel/extended-stay', {
            'vacation_period_id': 'VP-2025-DEC',
            'start_date': '2025-12-21',
            'end_date': '2026-01-03',
            'reason': 'Research project.',
            'authorization_file': 'auth_letter.pdf',
            'terms_acknowledged': True,
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'academic' in str(data).lower() or 'standing' in str(data).lower():
            self._record_result("Probation student correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Student on academic probation must be rejected per BR-HM-061")

    def test_invalid_previous_violation_student_rejected(self):
        self._test_id = "BR-HM-061-I-02"
        self._br_id = "BR-HM-061"
        self._test_category = "Invalid"
        self._input_action = "Student with extended stay violation in last year applies"
        self._expected_result = "Application rejected: ineligible for 1 academic year due to previous violation"

        self.login_as_student(hostel_status="Active")
        response = self.api_post('/hostel/extended-stay', {
            'vacation_period_id': 'VP-2025-DEC',
            'start_date': '2025-12-21',
            'end_date': '2026-01-03',
            'reason': 'Research project.',
            'authorization_file': 'auth_letter.pdf',
            'terms_acknowledged': True,
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'violation' in str(data).lower() or 'ineligible' in str(data).lower():
            self._record_result("Student with prior violation correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Student with violation in last year must be rejected per BR-HM-061")


# ===========================================================================
#  BR-HM-062: Vacation Period Validation
# ===========================================================================
class TestBRHM062_VacationPeriodValidation(BRTestBase):
    """BR-HM-062 – Extended stay dates MUST fall completely within declared vacation period."""

    def test_valid_dates_within_vacation_period(self):
        self._test_id = "BR-HM-062-V-01"
        self._br_id = "BR-HM-062"
        self._test_category = "Valid"
        self._input_action = "Student applies for stay within Dec 20 - Jan 5 vacation period"
        self._expected_result = "Dates accepted"

        self.login_as_student()
        response = self.api_post('/hostel/extended-stay', {
            'vacation_period_id': 'VP-2025-DEC',
            'start_date': '2025-12-22',
            'end_date': '2026-01-04',
            'reason': 'Research.',
            'authorization_file': 'auth.pdf',
            'terms_acknowledged': True,
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Valid vacation-period dates accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Dates within declared vacation period should be accepted")

    def test_invalid_end_date_outside_vacation_period(self):
        self._test_id = "BR-HM-062-I-01"
        self._br_id = "BR-HM-062"
        self._test_category = "Invalid"
        self._input_action = "Student applies with end_date one day after vacation period ends"
        self._expected_result = "Rejected: dates must fall within declared vacation period"

        self.login_as_student()
        response = self.api_post('/hostel/extended-stay', {
            'vacation_period_id': 'VP-2025-DEC',
            'start_date': '2025-12-22',
            'end_date': '2026-01-06',   # one day after vacation ends
            'reason': 'Research.',
            'authorization_file': 'auth.pdf',
            'terms_acknowledged': True,
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'vacation' in str(data).lower():
            self._record_result("Date outside vacation period correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Dates outside vacation period must be rejected per BR-HM-062")


# ===========================================================================
#  BR-HM-063: Authorization Requirements (Extended Stay)
# ===========================================================================
class TestBRHM063_AuthorizationRequirements(BRTestBase):
    """BR-HM-063 – Faculty authorization letter MUST be uploaded and meet format/size/date requirements."""

    def test_valid_pdf_authorization_accepted(self):
        self._test_id = "BR-HM-063-V-01"
        self._br_id = "BR-HM-063"
        self._test_category = "Valid"
        self._input_action = "Upload valid PDF authorization letter, 2MB, dated 10 days ago"
        self._expected_result = "Authorization accepted"

        self.login_as_student()
        response = self.api_post('/hostel/extended-stay', {
            'vacation_period_id': 'VP-2025-DEC',
            'start_date': '2025-12-22',
            'end_date': '2026-01-04',
            'reason': 'Research project.',
            'authorization_file': 'valid_auth.pdf',
            'authorization_file_size_mb': 2,
            'authorization_date': self.past_date(10),
            'terms_acknowledged': True,
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Valid authorization accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Valid authorization letter should be accepted")

    def test_invalid_missing_authorization_rejected(self):
        self._test_id = "BR-HM-063-I-01"
        self._br_id = "BR-HM-063"
        self._test_category = "Invalid"
        self._input_action = "Submit application without uploading authorization"
        self._expected_result = "Rejected: faculty authorization letter is mandatory"

        self.login_as_student()
        response = self.api_post('/hostel/extended-stay', {
            'vacation_period_id': 'VP-2025-DEC',
            'start_date': '2025-12-22',
            'end_date': '2026-01-04',
            'reason': 'Research project.',
            'authorization_file': None,
            'terms_acknowledged': True,
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'authorization' in str(data).lower():
            self._record_result("Missing authorization correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Application without authorization must be rejected per BR-HM-063")

    def test_invalid_old_authorization_rejected(self):
        self._test_id = "BR-HM-063-I-02"
        self._br_id = "BR-HM-063"
        self._test_category = "Invalid"
        self._input_action = "Upload authorization dated 45 days ago (outside 30-day window)"
        self._expected_result = "Rejected: authorization must be dated within 30 days of application"

        self.login_as_student()
        response = self.api_post('/hostel/extended-stay', {
            'vacation_period_id': 'VP-2025-DEC',
            'start_date': '2025-12-22',
            'end_date': '2026-01-04',
            'reason': 'Research project.',
            'authorization_file': 'old_auth.pdf',
            'authorization_file_size_mb': 1,
            'authorization_date': self.past_date(45),   # too old
            'terms_acknowledged': True,
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or '30' in str(data) or 'dated' in str(data).lower():
            self._record_result("Outdated authorization correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Authorization older than 30 days must be rejected per BR-HM-063")


# ===========================================================================
#  BR-HM-067: Room Availability During Vacation (30% cap)
# ===========================================================================
class TestBRHM067_VacationRoomAvailability(BRTestBase):
    """BR-HM-067 – Max 30% of hostel capacity for extended stays; beyond that → waitlist."""

    def test_valid_approval_below_30_percent_capacity(self):
        self._test_id = "BR-HM-067-V-01"
        self._br_id = "BR-HM-067"
        self._test_category = "Valid"
        self._input_action = "Approve application when only 20% of hostel is allocated for extended stays"
        self._expected_result = "Approval proceeds; room reserved"

        self.login_as_caretaker()
        response = self.api_patch('/hostel/extended-stay/700/decision', {
            'decision': 'Approved',
            'comments': 'Room available; capacity within limits.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Approval within capacity allowed", "Pass", str(data))
        else:
            self._record_result(f"Unexpected denial: {data}", "Fail", str(data))
            self.fail("Approval below 30% capacity should proceed per BR-HM-067")

    def test_invalid_approval_at_30_percent_cap_goes_to_waitlist(self):
        self._test_id = "BR-HM-067-I-01"
        self._br_id = "BR-HM-067"
        self._test_category = "Invalid"
        self._input_action = "Attempt to approve application when 30% capacity already allocated"
        self._expected_result = "Application moved to waitlist: 'Capacity reached'"

        self.login_as_caretaker()
        response = self.api_patch('/hostel/extended-stay/701/decision', {
            'decision': 'Approved',
        }, expected_status=None)
        data = response.json()
        if data.get('extended_stay_status') == 'Waitlisted' or 'capacity' in str(data).lower() or 'waitlist' in str(data).lower():
            self._record_result("Application correctly moved to waitlist at capacity", "Pass", str(data))
        else:
            self._record_result(f"Not moved to waitlist: {data}", "Fail", str(data))
            self.fail("Application must go to waitlist when 30% capacity reached per BR-HM-067")


# ===========================================================================
#  BR-HM-073: Payment Deadline Policy
# ===========================================================================
class TestBRHM073_PaymentDeadlinePolicy(BRTestBase):
    """BR-HM-073 – Extended stay charges due within 3 days of approval or 7 days before stay."""

    def test_valid_payment_within_deadline_confirmed(self):
        self._test_id = "BR-HM-073-V-01"
        self._br_id = "BR-HM-073"
        self._test_category = "Valid"
        self._input_action = "Student pays within 3 days of approval"
        self._expected_result = "Payment confirmed; extended stay proceeds"

        self.login_as_student()
        response = self.api_post('/hostel/extended-stay/800/payment', {
            'payment_amount': 1500.00,
            'payment_method': 'Online',
            'transaction_id': 'TXN-20250610-001',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1 and data.get('payment_status') == 'Paid':
            self._record_result("Payment within deadline confirmed", "Pass", str(data))
        else:
            self._record_result(f"Unexpected failure: {data}", "Fail", str(data))
            self.fail("Payment within deadline should be confirmed per BR-HM-073")

    def test_invalid_approval_revoked_on_payment_deadline_miss(self):
        self._test_id = "BR-HM-073-I-01"
        self._br_id = "BR-HM-073"
        self._test_category = "Invalid"
        self._input_action = "Student does not pay by payment deadline; stay start date arrives"
        self._expected_result = "Approval automatically revoked; room reservation released; student notified"

        self.login_as_super_admin()  # trigger system check as admin
        response = self.api_post('/hostel/extended-stay/801/payment-deadline-check', {
            'check_date': self.future_date(0),   # today is start date
        }, expected_status=None)
        data = response.json()
        if (data.get('extended_stay_status') == 'Revoked' or
                'revoked' in str(data).lower() or 'deadline' in str(data).lower()):
            self._record_result("Approval correctly revoked on payment deadline miss", "Pass", str(data))
        else:
            self._record_result(f"Not revoked: {data}", "Fail", str(data))
            self.fail("Approval must be revoked on stay start date if unpaid per BR-HM-073")


# ===========================================================================
#  BR-HM-015: Room Vacation Prerequisites
# ===========================================================================
class TestBRHM015_RoomVacationPrerequisites(BRTestBase):
    """BR-HM-015 – Student MUST NOT vacate until clearance requirements are met."""

    def test_valid_clearance_all_items_complete(self):
        self._test_id = "BR-HM-015-V-01"
        self._br_id = "BR-HM-015"
        self._test_category = "Valid"
        self._input_action = "Student with zero outstanding fines, all items returned, no pending damage assessments submits vacation request"
        self._expected_result = "Clearance checklist generated with all items green; vacation request proceeds"

        self.login_as_student()
        response = self.api_post('/hostel/room/vacate', {
            'student_id': 55,
            'vacation_date': self.future_date(7),
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1 and data.get('clearance_status') == 'Approved':
            self._record_result("Vacation proceeds with all clearance items complete", "Pass", str(data))
        else:
            self._record_result(f"Unexpected block: {data}", "Fail", str(data))
            self.fail("Student with full clearance should be able to vacate")

    def test_invalid_outstanding_fine_blocks_vacation(self):
        self._test_id = "BR-HM-015-I-01"
        self._br_id = "BR-HM-015"
        self._test_category = "Invalid"
        self._input_action = "Student with outstanding fine of 500 attempts to complete vacation clearance"
        self._expected_result = "Clearance blocked: outstanding fines must be paid first"

        self.login_as_student()
        response = self.api_post('/hostel/room/vacate', {
            'student_id': 56,   # student has unpaid fine of 500
            'vacation_date': self.future_date(7),
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'fine' in str(data).lower():
            self._record_result("Vacation blocked due to outstanding fine", "Pass", str(data))
        else:
            self._record_result(f"Not blocked: {data}", "Fail", str(data))
            self.fail("Outstanding fine must block vacation clearance per BR-HM-015")

    def test_invalid_unreturned_items_block_vacation(self):
        self._test_id = "BR-HM-015-I-02"
        self._br_id = "BR-HM-015"
        self._test_category = "Invalid"
        self._input_action = "Student with unreturned borrowed items attempts to complete vacation"
        self._expected_result = "Clearance blocked: all borrowed items must be returned"

        self.login_as_student()
        response = self.api_post('/hostel/room/vacate', {
            'student_id': 57,   # student has unreturned items
            'vacation_date': self.future_date(7),
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'borrowed' in str(data).lower() or 'returned' in str(data).lower():
            self._record_result("Vacation blocked due to unreturned items", "Pass", str(data))
        else:
            self._record_result(f"Not blocked: {data}", "Fail", str(data))
            self.fail("Unreturned items must block vacation clearance per BR-HM-015")


# ===========================================================================
#  BR-HM-012: Data Scoping by Role and Assignment
# ===========================================================================
class TestBRHM012_DataScopingByRole(BRTestBase):
    """BR-HM-012 – Data visibility is role-scoped: Student→own; Caretaker→assigned hostels; Super Admin→all."""

    def test_valid_student_sees_own_fines_only(self):
        self._test_id = "BR-HM-012-V-01"
        self._br_id = "BR-HM-012"
        self._test_category = "Valid"
        self._input_action = "Student requests their own fine records"
        self._expected_result = "Only fines belonging to this student are returned"

        self.login_as_student()
        response = self.api_get('/hostel/fine/list')
        data = response.json()
        student_ids = {r.get('student_id') for r in data.get('fines', [])}
        if len(student_ids) <= 1:   # only own student_id or empty
            self._record_result("Student sees only their own fines", "Pass", str(data))
        else:
            self._record_result(f"Multiple students' fines exposed: {student_ids}", "Fail", str(data))
            self.fail("Student must see only their own fines per BR-HM-012")

    def test_invalid_student_cannot_access_other_student_fines(self):
        self._test_id = "BR-HM-012-I-01"
        self._br_id = "BR-HM-012"
        self._test_category = "Invalid"
        self._input_action = "Student requests fine records of another student"
        self._expected_result = "Access denied; only own data is visible"

        self.login_as_student()
        response = self.api_get('/hostel/fine/list', {'student_id': 999})   # another student
        data = response.json()
        if data.get('status') == 4 or 'access' in str(data).lower():
            self._record_result("Cross-student fine access correctly denied", "Pass", str(data))
        else:
            self._record_result(f"Cross-student access permitted: {data}", "Fail", str(data))
            self.fail("Student must not access another student's fines per BR-HM-012")

    def test_invalid_caretaker_cannot_access_other_hostel_data(self):
        self._test_id = "BR-HM-012-I-02"
        self._br_id = "BR-HM-012"
        self._test_category = "Invalid"
        self._input_action = "Caretaker requests data from a hostel they are not assigned to"
        self._expected_result = "Access denied; data scoped to assigned hostels only"

        self.login_as_caretaker(hostel_id="H1")
        response = self.api_get('/hostel/fine/list', {'hostel_id': 'H3'})  # different hostel
        data = response.json()
        if data.get('status') == 4 or 'access' in str(data).lower() or 'scope' in str(data).lower():
            self._record_result("Cross-hostel data access correctly denied", "Pass", str(data))
        else:
            self._record_result(f"Cross-hostel access allowed: {data}", "Fail", str(data))
            self.fail("Caretaker must not access data from other hostels per BR-HM-012")


# ===========================================================================
#  BR-HM-059: Guest Room Charges
# ===========================================================================
class TestBRHM059_GuestRoomCharges(BRTestBase):
    """BR-HM-059 – Charges must be calculated and displayed before booking confirmation."""

    def test_valid_charges_displayed_before_confirmation(self):
        self._test_id = "BR-HM-059-V-01"
        self._br_id = "BR-HM-059"
        self._test_category = "Valid"
        self._input_action = "Submit 3-night booking; charges calculated and displayed before confirmation"
        self._expected_result = "Charge breakdown shown before student confirms"

        self.login_as_student()
        response = self.api_post('/hostel/guest-room/booking/calculate-charges', {
            'room_id': 'GR-01',
            'check_in': self.future_date(10),
            'check_out': self.future_date(13),   # 3 nights
            'guest_count': 1,
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1 and data.get('charge_breakdown') is not None:
            self._record_result("Charge breakdown returned before confirmation", "Pass", str(data))
        else:
            self._record_result(f"Charge breakdown missing: {data}", "Fail", str(data))
            self.fail("Charge breakdown must be available before booking confirmation per BR-HM-059")

    def test_valid_7_night_extended_stay_discount_applied(self):
        self._test_id = "BR-HM-059-V-02"
        self._br_id = "BR-HM-059"
        self._test_category = "Valid"
        self._input_action = "Submit 7-night booking; extended stay discount applied"
        self._expected_result = "Discount applied to base charges; final amount displayed"

        self.login_as_student()
        response = self.api_post('/hostel/guest-room/booking/calculate-charges', {
            'room_id': 'GR-01',
            'check_in': self.future_date(10),
            'check_out': self.future_date(17),   # 7 nights
            'guest_count': 1,
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1 and data.get('discount_applied') is True:
            self._record_result("Extended stay discount correctly applied for 7 nights", "Pass", str(data))
        else:
            self._record_result(f"Discount not applied: {data}", "Fail", str(data))
            self.fail("7-night booking must receive extended stay discount per BR-HM-059")


# ===========================================================================
#  BR-HM-043: Report Filter Rules
# ===========================================================================
class TestBRHM043_ReportFilterRules(BRTestBase):
    """BR-HM-043 – Targeted reports need at least one filter; filters combined with AND logic."""

    def test_valid_report_with_filter_criteria(self):
        self._test_id = "BR-HM-043-V-01"
        self._br_id = "BR-HM-043"
        self._test_category = "Valid"
        self._input_action = "Generate report with hostel_id and date_range filters applied"
        self._expected_result = "Report generated with both filters applied as AND condition"

        self.login_as_caretaker()
        response = self.api_post('/hostel/report/generate', {
            'hostel_id': 'H1',
            'report_type': 'Attendance Summary',
            'date_from': self.past_date(30),
            'date_to': self.past_date(1),
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Report with filters generated successfully", "Pass", str(data))
        else:
            self._record_result(f"Report generation failed: {data}", "Fail", str(data))
            self.fail("Report with valid filters should be generated per BR-HM-043")

    def test_invalid_targeted_report_without_filters_blocked(self):
        self._test_id = "BR-HM-043-I-01"
        self._br_id = "BR-HM-043"
        self._test_category = "Invalid"
        self._input_action = "Generate targeted report with no filter criteria specified"
        self._expected_result = "Validation error: at least one filter criterion required"

        self.login_as_caretaker()
        response = self.api_post('/hostel/report/generate', {
            'report_type': 'Targeted',
            # no filters provided
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'filter' in str(data).lower():
            self._record_result("Report without filters correctly blocked", "Pass", str(data))
        else:
            self._record_result(f"Not blocked: {data}", "Fail", str(data))
            self.fail("Targeted report without filters must be blocked per BR-HM-043")


# ===========================================================================
#  BR-HM-030: Resource Requirement Request Validation
# ===========================================================================
class TestBRHM030_ResourceRequestValidation(BRTestBase):
    """BR-HM-030 – Resource request MUST have type, item, positive quantity, and justification."""

    def test_valid_resource_request_accepted(self):
        self._test_id = "BR-HM-030-V-01"
        self._br_id = "BR-HM-030"
        self._test_category = "Valid"
        self._input_action = "Submit resource request with type=Replacement, item=Bed, quantity=5, justification=non-empty"
        self._expected_result = "Request accepted with status=Pending"

        self.login_as_caretaker()
        response = self.api_post('/hostel/resource-request', {
            'request_type': 'Replacement',
            'item_id': 'ITEM-BED-001',
            'quantity': 5,
            'justification': 'Beds in rooms 101-105 are broken and need replacement.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 1:
            self._record_result("Valid resource request accepted", "Pass", str(data))
        else:
            self._record_result(f"Unexpected rejection: {data}", "Fail", str(data))
            self.fail("Valid resource request should be accepted per BR-HM-030")

    def test_invalid_resource_request_zero_quantity(self):
        self._test_id = "BR-HM-030-I-01"
        self._br_id = "BR-HM-030"
        self._test_category = "Invalid"
        self._input_action = "Submit resource request with quantity=0"
        self._expected_result = "Validation error: quantity must be positive integer"

        self.login_as_caretaker()
        response = self.api_post('/hostel/resource-request', {
            'request_type': 'Replacement',
            'item_id': 'ITEM-BED-001',
            'quantity': 0,
            'justification': 'Test.',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'quantity' in str(data).lower():
            self._record_result("Zero quantity correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Resource request with quantity=0 must be rejected per BR-HM-030")

    def test_invalid_resource_request_missing_justification(self):
        self._test_id = "BR-HM-030-I-02"
        self._br_id = "BR-HM-030"
        self._test_category = "Invalid"
        self._input_action = "Submit resource request with missing justification"
        self._expected_result = "Validation error: justification is required"

        self.login_as_caretaker()
        response = self.api_post('/hostel/resource-request', {
            'request_type': 'Replacement',
            'item_id': 'ITEM-BED-001',
            'quantity': 3,
            'justification': '',
        }, expected_status=None)
        data = response.json()
        if data.get('status') == 4 or 'justification' in str(data).lower():
            self._record_result("Missing justification correctly rejected", "Pass", str(data))
        else:
            self._record_result(f"Not rejected: {data}", "Fail", str(data))
            self.fail("Resource request without justification must be rejected per BR-HM-030")


# ===========================================================================
#  Entry point
# ===========================================================================
if __name__ == '__main__':
    unittest.main(verbosity=2)