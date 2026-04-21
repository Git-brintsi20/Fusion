"""
test_workflows.py
=================
End-to-End and Negative Workflow Tests for the Hostel Management (HM) module.
Each test class maps to one workflow defined in workflows.yaml / HM_WFs.docx.

Usage:
    python -m pytest tests/test_workflows.py -v

Base class:
    from .test_base import WFTestBase   # adjust import to your project layout
"""

# ---------------------------------------------------------------------------
# Adjust this import to match your actual project structure
# ---------------------------------------------------------------------------
from .test_base import WFTestBase          # noqa: E402  (relative import)
# ---------------------------------------------------------------------------


# ===========================================================================
# HM-WF-101 – Student Leave Request Workflow
# ===========================================================================
class TestWF101_LeaveRequestFlow(WFTestBase):
    """
    WF-101: Student Leave Request → Caretaker Reviews → Approved / Rejected
    Actors : Student · Caretaker · System
    BRs    : BR-HM-101 to BR-HM-105
    """

    # -----------------------------------------------------------------------
    # E2E – happy path
    # -----------------------------------------------------------------------
    def test_e2e_leave_approved_attendance_updated(self):
        self._test_id = "HM-WF-101-E2E-01"
        self._wf_id = "HM-WF-101"
        self._test_category = "End-to-End"
        self._scenario = (
            "Student submits valid leave → Caretaker approves → "
            "attendance updated to 'On Leave'"
        )
        self._expected_final_state = (
            "Leave status=Approved; attendance=On Leave for requested dates; "
            "student notified; leave visible in history"
        )

        # Step 1 – Student submits leave with valid payload
        self.login_as_student()
        payload = {
            "start_date": "2025-08-01",
            "end_date": "2025-08-03",
            "reason": "Family function",
            "document": "document_base64_or_path_here",
        }
        resp = self.api_post("/hostel/leave/apply", payload, expected_status=None)
        data = resp.json()
        step1_ok = data.get("status") == "Pending"
        self._add_step(
            1,
            "Student submits leave request (BR-HM-101, BR-HM-102, BR-HM-103)",
            "Leave created with status=Pending; Caretaker notified",
            str(data),
            step1_ok,
        )
        leave_id = data.get("leave_id") or data.get("id")

        # Step 2 – Caretaker approves
        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/leave/respond",
            {"leave_id": leave_id, "action": "approve", "remarks": "Approved"},
            expected_status=None,
        )
        data = resp.json()
        step2_ok = data.get("status") == "Approved"
        self._add_step(
            2,
            "Caretaker approves leave (BR-HM-104)",
            "Leave status changed to Approved",
            str(data),
            step2_ok,
        )

        # Step 3 – Verify attendance updated
        self.login_as_student()
        resp = self.api_get(f"/hostel/leave/{leave_id}", expected_status=None)
        data = resp.json()
        # Adjust field name to match your model
        step3_ok = data.get("attendance_status") in ("On Leave", "on_leave")
        self._add_step(
            3,
            "Verify attendance marked as 'On Leave' (BR-HM-105)",
            "attendance_status = On Leave for approved dates",
            str(data),
            step3_ok,
        )

        # Step 4 – Verify leave appears in history
        resp = self.api_get("/hostel/leave/history", expected_status=None)
        history = resp.json()
        step4_ok = any(str(r.get("id")) == str(leave_id) for r in history.get("results", [history]))
        self._add_step(
            4,
            "Leave visible in student's leave history",
            "Leave record present in history list",
            str(history)[:200],
            step4_ok,
        )

        if self._all_steps_passed():
            self._record_result("Full leave approval flow completed", "Pass")
        else:
            self._record_result("Leave approval flow incomplete", "Fail")
            self.fail("WF-101 E2E: Leave approval workflow did not complete successfully")

    # -----------------------------------------------------------------------
    # Negative – Caretaker rejects leave
    # -----------------------------------------------------------------------
    def test_neg_leave_rejected_by_caretaker(self):
        self._test_id = "HM-WF-101-NEG-01"
        self._wf_id = "HM-WF-101"
        self._test_category = "Negative"
        self._scenario = "Student submits leave; Caretaker rejects with mandatory remarks"
        self._expected_final_state = (
            "Leave status=Rejected; attendance unchanged; student notified with rejection reason"
        )

        self.login_as_student()
        resp = self.api_post(
            "/hostel/leave/apply",
            {"start_date": "2025-08-10", "end_date": "2025-08-12", "reason": "Travel"},
            expected_status=None,
        )
        leave_id = resp.json().get("leave_id") or resp.json().get("id")
        step1_ok = resp.json().get("status") == "Pending"
        self._add_step(1, "Student submits leave", "status=Pending", str(resp.json()), step1_ok)

        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/leave/respond",
            {"leave_id": leave_id, "action": "reject", "remarks": "Not permitted during exams"},
            expected_status=None,
        )
        data = resp.json()
        step2_ok = data.get("status") == "Rejected"
        self._add_step(
            2,
            "Caretaker rejects leave with remarks",
            "status=Rejected; student notified",
            str(data),
            step2_ok,
        )

        if self._all_steps_passed():
            self._record_result("Rejection flow worked correctly", "Pass")
        else:
            self._record_result("Rejection flow failed", "Fail")
            self.fail("WF-101 NEG-01: Leave rejection flow did not complete successfully")

    # -----------------------------------------------------------------------
    # Negative – student without active allotment
    # -----------------------------------------------------------------------
    def test_neg_leave_submission_no_active_allotment(self):
        self._test_id = "HM-WF-101-NEG-02"
        self._wf_id = "HM-WF-101"
        self._test_category = "Negative"
        self._scenario = "Student with hostel_status=Vacated submits leave request"
        self._expected_final_state = (
            "Leave submission rejected; no leave record created; eligibility error displayed"
        )

        self.login_as_vacated_student()          # helper that logs in a vacated student
        resp = self.api_post(
            "/hostel/leave/apply",
            {"start_date": "2025-08-01", "end_date": "2025-08-03", "reason": "Test"},
            expected_status=None,
        )
        data = resp.json()
        # Expect 400/403 and an eligibility error message
        step1_ok = resp.status_code in (400, 403) or "eligib" in str(data).lower()
        self._add_step(
            1,
            "Vacated student submits leave (BR-HM-101)",
            "System blocks submission with eligibility error",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Eligibility guard worked correctly", "Pass")
        else:
            self._record_result("Eligibility guard failed", "Fail")
            self.fail("WF-101 NEG-02: Vacated student should not be allowed to apply for leave")

    # -----------------------------------------------------------------------
    # Negative – invalid date range
    # -----------------------------------------------------------------------
    def test_neg_leave_invalid_date_range(self):
        self._test_id = "HM-WF-101-NEG-03"
        self._wf_id = "HM-WF-101"
        self._test_category = "Negative"
        self._scenario = "Leave submission with end_date before start_date"
        self._expected_final_state = (
            "Validation error; leave request not created; form data retained"
        )

        self.login_as_student()
        resp = self.api_post(
            "/hostel/leave/apply",
            {"start_date": "2025-08-10", "end_date": "2025-08-01", "reason": "Test"},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code == 400 or "date" in str(data).lower()
        self._add_step(
            1,
            "Submit leave with end_date < start_date (BR-HM-102)",
            "400 validation error returned",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Date validation guard worked correctly", "Pass")
        else:
            self._record_result("Date validation guard failed", "Fail")
            self.fail("WF-101 NEG-03: Invalid date range should be rejected")


# ===========================================================================
# HM-WF-102 – Complaint Resolution Workflow
# ===========================================================================
class TestWF102_ComplaintResolutionFlow(WFTestBase):
    """
    WF-102: Student Submits Complaint → Routed → Investigated → Resolved
    Actors : Student · Caretaker · Warden · System
    BRs    : BR-HM-106 to BR-HM-110
    """

    def test_e2e_maintenance_complaint_resolved_by_caretaker(self):
        self._test_id = "HM-WF-102-E2E-01"
        self._wf_id = "HM-WF-102"
        self._test_category = "End-to-End"
        self._scenario = "Student submits Maintenance complaint; Caretaker investigates and resolves"
        self._expected_final_state = (
            "Complaint status=Resolved; resolution remarks recorded; "
            "student notified; complaint history maintained"
        )

        # Step 1 – Student submits maintenance complaint
        self.login_as_student()
        resp = self.api_post(
            "/hostel/complaint/submit",
            {"category": "Maintenance", "description": "Tap leaking in bathroom"},
            expected_status=None,
        )
        data = resp.json()
        complaint_id = data.get("complaint_id") or data.get("id")
        step1_ok = data.get("status") in ("Pending", "Open")
        self._add_step(
            1,
            "Student submits maintenance complaint (BR-HM-106)",
            "Complaint recorded with status=Pending; routed to Caretaker (BR-HM-107.b)",
            str(data),
            step1_ok,
        )

        # Step 2 – Caretaker sets in-progress
        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/complaint/update",
            {"complaint_id": complaint_id, "status": "In Progress"},
            expected_status=None,
        )
        step2_ok = resp.json().get("status") == "In Progress"
        self._add_step(
            2,
            "Caretaker sets complaint to In Progress",
            "status=In Progress",
            str(resp.json()),
            step2_ok,
        )

        # Step 3 – Caretaker resolves with remarks
        resp = self.api_post(
            "/hostel/complaint/resolve",
            {
                "complaint_id": complaint_id,
                "resolution_remarks": "Tap fixed by plumber",
            },
            expected_status=None,
        )
        data = resp.json()
        step3_ok = data.get("status") == "Resolved"
        self._add_step(
            3,
            "Caretaker resolves complaint with mandatory remarks (BR-HM-108)",
            "status=Resolved; student notified",
            str(data),
            step3_ok,
        )

        # Step 4 – Student verifies status
        self.login_as_student()
        resp = self.api_get(f"/hostel/complaint/{complaint_id}", expected_status=None)
        data = resp.json()
        step4_ok = data.get("status") == "Resolved"
        self._add_step(
            4,
            "Student views resolved complaint",
            "Complaint shows Resolved with remarks",
            str(data),
            step4_ok,
        )

        if self._all_steps_passed():
            self._record_result("Caretaker resolution flow completed", "Pass")
        else:
            self._record_result("Caretaker resolution flow incomplete", "Fail")
            self.fail("WF-102 E2E-01: Maintenance complaint resolution flow failed")

    def test_e2e_security_complaint_routed_to_warden(self):
        self._test_id = "HM-WF-102-E2E-02"
        self._wf_id = "HM-WF-102"
        self._test_category = "End-to-End"
        self._scenario = "Student submits Security complaint; Warden resolves"
        self._expected_final_state = "Complaint status=Resolved by Warden; student notified"

        self.login_as_student()
        resp = self.api_post(
            "/hostel/complaint/submit",
            {"category": "Security", "description": "Unauthorized person on floor"},
            expected_status=None,
        )
        data = resp.json()
        complaint_id = data.get("complaint_id") or data.get("id")
        step1_ok = data.get("assigned_to") in ("Warden", "warden")
        self._add_step(
            1,
            "Security complaint routed to Warden (BR-HM-107.a)",
            "assigned_to=Warden",
            str(data),
            step1_ok,
        )

        self.login_as_warden()
        resp = self.api_post(
            "/hostel/complaint/resolve",
            {"complaint_id": complaint_id, "resolution_remarks": "Security check conducted"},
            expected_status=None,
        )
        data = resp.json()
        step2_ok = data.get("status") == "Resolved"
        self._add_step(
            2,
            "Warden resolves security complaint (BR-HM-110)",
            "status=Resolved",
            str(data),
            step2_ok,
        )

        if self._all_steps_passed():
            self._record_result("Security complaint–Warden flow completed", "Pass")
        else:
            self._record_result("Security complaint–Warden flow failed", "Fail")
            self.fail("WF-102 E2E-02: Security complaint Warden flow failed")

    def test_neg_complaint_escalated_to_warden(self):
        self._test_id = "HM-WF-102-NEG-01"
        self._wf_id = "HM-WF-102"
        self._test_category = "Negative"
        self._scenario = "Caretaker cannot resolve; escalates to Warden"
        self._expected_final_state = (
            "Complaint status=Resolved by Warden; escalation reason recorded"
        )

        self.login_as_student()
        resp = self.api_post(
            "/hostel/complaint/submit",
            {"category": "Maintenance", "description": "Electrical fault – sparking"},
            expected_status=None,
        )
        complaint_id = resp.json().get("complaint_id") or resp.json().get("id")
        step1_ok = resp.status_code in (200, 201)
        self._add_step(1, "Student submits complaint", "Complaint created", str(resp.json()), step1_ok)

        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/complaint/escalate",
            {"complaint_id": complaint_id, "reason": "Requires electrical expert"},
            expected_status=None,
        )
        data = resp.json()
        step2_ok = data.get("status") == "Escalated"
        self._add_step(
            2,
            "Caretaker escalates with mandatory reason (BR-HM-109)",
            "status=Escalated; Warden notified",
            str(data),
            step2_ok,
        )

        self.login_as_warden()
        resp = self.api_post(
            "/hostel/complaint/resolve",
            {"complaint_id": complaint_id, "resolution_remarks": "Electrician deployed"},
            expected_status=None,
        )
        step3_ok = resp.json().get("status") == "Resolved"
        self._add_step(
            3,
            "Warden resolves escalated complaint",
            "status=Resolved by Warden",
            str(resp.json()),
            step3_ok,
        )

        if self._all_steps_passed():
            self._record_result("Escalation + Warden resolution flow completed", "Pass")
        else:
            self._record_result("Escalation flow incomplete", "Fail")
            self.fail("WF-102 NEG-01: Escalation flow failed")

    def test_neg_escalate_resolved_complaint_blocked(self):
        self._test_id = "HM-WF-102-NEG-03"
        self._wf_id = "HM-WF-102"
        self._test_category = "Negative"
        self._scenario = "Caretaker attempts to escalate an already-Resolved complaint"
        self._expected_final_state = (
            "Escalation blocked; complaint must be In Progress to escalate"
        )

        resolved_complaint_id = self._get_resolved_complaint_id()   # helper or fixture

        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/complaint/escalate",
            {"complaint_id": resolved_complaint_id, "reason": "Late escalation attempt"},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code in (400, 403) or "resolved" in str(data).lower()
        self._add_step(
            1,
            "Escalate already-Resolved complaint (BR-HM-109)",
            "System blocks escalation",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Escalation guard on resolved complaint works", "Pass")
        else:
            self._record_result("Escalation guard failed", "Fail")
            self.fail("WF-102 NEG-03: Resolved complaint should not be escalatable")


# ===========================================================================
# HM-WF-103 – New Student Room Allotment & Onboarding Workflow
# ===========================================================================
class TestWF103_BulkRoomAllotmentFlow(WFTestBase):
    """
    WF-103: Bulk Room Allotment → Students Notified → Hostel Access Enabled
    Actors : Super Admin · Student · System
    BRs    : BR-HM-111 to BR-HM-114
    """

    def test_e2e_bulk_allotment_within_capacity(self):
        self._test_id = "HM-WF-103-E2E-01"
        self._wf_id = "HM-WF-103"
        self._test_category = "End-to-End"
        self._scenario = "Super Admin performs bulk allotment within capacity; students notified"
        self._expected_final_state = (
            "All selected students have rooms; occupancy updated; "
            "notifications sent; request statuses=Allotted"
        )

        # Step 1 – Students submit accommodation requests
        self.login_as_student()
        resp = self.api_post(
            "/hostel/accommodation/request",
            {"preferred_hostel": "Hostel-A"},
            expected_status=None,
        )
        request_id = resp.json().get("request_id") or resp.json().get("id")
        step1_ok = resp.json().get("status") == "Pending"
        self._add_step(
            1,
            "Student submits accommodation request during open window (BR-HM-111)",
            "status=Pending",
            str(resp.json()),
            step1_ok,
        )

        # Step 2 – Super Admin performs bulk allotment
        self.login_as_super_admin()
        resp = self.api_post(
            "/hostel/allotment/bulk",
            {"request_ids": [request_id], "hostel_id": "Hostel-A"},
            expected_status=None,
        )
        data = resp.json()
        step2_ok = data.get("allotted_count", 0) >= 1
        self._add_step(
            2,
            "Super Admin performs bulk allotment; capacity validated (BR-HM-112, BR-HM-113)",
            "Rooms assigned; occupancy updated",
            str(data),
            step2_ok,
        )

        # Step 3 – Verify student notification sent
        step3_ok = data.get("notifications_sent") is True or data.get("notified_count", 0) >= 1
        self._add_step(
            3,
            "System notifies students and Caretakers (BR-HM-114)",
            "notifications_sent=True",
            str(data),
            step3_ok,
        )

        # Step 4 – Student views room allocation
        self.login_as_student()
        resp = self.api_get("/hostel/my-room", expected_status=None)
        data = resp.json()
        step4_ok = data.get("room_number") is not None
        self._add_step(
            4,
            "Student views assigned room",
            "Room number visible",
            str(data),
            step4_ok,
        )

        if self._all_steps_passed():
            self._record_result("Bulk allotment flow completed successfully", "Pass")
        else:
            self._record_result("Bulk allotment flow incomplete", "Fail")
            self.fail("WF-103 E2E-01: Bulk room allotment flow failed")

    def test_neg_allotment_exceeds_capacity(self):
        self._test_id = "HM-WF-103-NEG-01"
        self._wf_id = "HM-WF-103"
        self._test_category = "Negative"
        self._scenario = "Allotment attempted beyond room capacity"
        self._expected_final_state = (
            "Allotment blocked; over-allocation warning displayed; occupancy unchanged"
        )

        self.login_as_super_admin()
        over_capacity_ids = self._get_over_capacity_request_ids()   # fixture
        resp = self.api_post(
            "/hostel/allotment/bulk",
            {"request_ids": over_capacity_ids, "hostel_id": "Hostel-A"},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code in (400, 409) or "capacity" in str(data).lower()
        self._add_step(
            1,
            "Over-capacity bulk allotment blocked (BR-HM-112)",
            "Capacity warning returned; no allotment performed",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Capacity guard works correctly", "Pass")
        else:
            self._record_result("Capacity guard failed", "Fail")
            self.fail("WF-103 NEG-01: Over-capacity allotment should be blocked")

    def test_neg_non_admin_cannot_allot(self):
        self._test_id = "HM-WF-103-NEG-02"
        self._wf_id = "HM-WF-103"
        self._test_category = "Negative"
        self._scenario = "Caretaker initiates bulk allotment (role check)"
        self._expected_final_state = "Action denied with authorization error"

        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/allotment/bulk",
            {"request_ids": ["req-001"], "hostel_id": "Hostel-A"},
            expected_status=None,
        )
        step1_ok = resp.status_code in (401, 403)
        self._add_step(
            1,
            "Caretaker attempts bulk allotment (BR-HM-113 role guard)",
            "HTTP 401/403 returned",
            str(resp.json()),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Role guard on bulk allotment works", "Pass")
        else:
            self._record_result("Role guard failed", "Fail")
            self.fail("WF-103 NEG-02: Non-admin bulk allotment should be denied")


# ===========================================================================
# HM-WF-104 – Student Room Change Workflow
# ===========================================================================
class TestWF104_RoomChangeFlow(WFTestBase):
    """
    WF-104: Student Requests Room Change → Dual Approval → Reallocated
    Actors : Student · Caretaker · Warden · System
    BRs    : BR-HM-115 to BR-HM-118
    """

    def test_e2e_room_change_dual_approval(self):
        self._test_id = "HM-WF-104-E2E-01"
        self._wf_id = "HM-WF-104"
        self._test_category = "End-to-End"
        self._scenario = "Student requests; room available; both approve; room reallocated"
        self._expected_final_state = (
            "Student assigned to new room; occupancy reconciled; student notified"
        )

        # Step 1 – Student submits request
        self.login_as_student()
        resp = self.api_post(
            "/hostel/room-change/apply",
            {"requested_room": "B-204", "reason": "Better ventilation needed"},
            expected_status=None,
        )
        data = resp.json()
        rc_id = data.get("request_id") or data.get("id")
        step1_ok = data.get("status") == "Pending"
        self._add_step(
            1,
            "Student submits room change request with mandatory reason (BR-HM-115)",
            "status=Pending",
            str(data),
            step1_ok,
        )

        # Step 2 – Caretaker approves
        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/room-change/respond",
            {"request_id": rc_id, "action": "approve", "role": "caretaker"},
            expected_status=None,
        )
        step2_ok = resp.json().get("caretaker_approval") is True
        self._add_step(
            2,
            "Caretaker verifies availability and approves",
            "caretaker_approval=True",
            str(resp.json()),
            step2_ok,
        )

        # Step 3 – Warden approves (dual approval BR-HM-116)
        self.login_as_warden()
        resp = self.api_post(
            "/hostel/room-change/respond",
            {"request_id": rc_id, "action": "approve", "role": "warden"},
            expected_status=None,
        )
        data = resp.json()
        step3_ok = data.get("status") == "Approved"
        self._add_step(
            3,
            "Warden approves for policy compliance (BR-HM-116)",
            "Both approvals obtained; status=Approved",
            str(data),
            step3_ok,
        )

        # Step 4 – Verify room reassignment
        self.login_as_student()
        resp = self.api_get("/hostel/my-room", expected_status=None)
        data = resp.json()
        step4_ok = str(data.get("room_number", "")) == "B-204"
        self._add_step(
            4,
            "Student now assigned to new room (BR-HM-117, BR-HM-118)",
            "room_number=B-204",
            str(data),
            step4_ok,
        )

        if self._all_steps_passed():
            self._record_result("Dual-approval room change flow completed", "Pass")
        else:
            self._record_result("Room change flow incomplete", "Fail")
            self.fail("WF-104 E2E-01: Room change dual-approval flow failed")

    def test_neg_room_change_single_approval_blocked(self):
        self._test_id = "HM-WF-104-NEG-03"
        self._wf_id = "HM-WF-104"
        self._test_category = "Negative"
        self._scenario = "Caretaker approves; Warden has not reviewed; reallocation blocked"
        self._expected_final_state = (
            "Reallocation blocked; request remains Pending until both approvals obtained"
        )

        rc_id = self._get_caretaker_approved_request_id()   # fixture

        self.login_as_super_admin()          # attempt to force-process via admin
        resp = self.api_post(
            "/hostel/room-change/execute",
            {"request_id": rc_id},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code in (400, 403) or "approval" in str(data).lower()
        self._add_step(
            1,
            "Reallocation attempted without dual approval (BR-HM-116)",
            "System blocks; request remains Pending",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Single-approval guard works", "Pass")
        else:
            self._record_result("Single-approval guard failed", "Fail")
            self.fail("WF-104 NEG-03: Single approval should not trigger reallocation")


# ===========================================================================
# HM-WF-105 – Fine Management Workflow
# ===========================================================================
class TestWF105_FineManagementFlow(WFTestBase):
    """
    WF-105: Caretaker Imposes Fine → Student Views → Warden Monitors
    Actors : Caretaker · Student · Warden · System
    BRs    : BR-HM-012 to BR-HM-014 · BR-HM-022
    """

    def test_e2e_fine_imposed_viewed_monitored_no_escalation(self):
        self._test_id = "HM-WF-105-E2E-01"
        self._wf_id = "HM-WF-105"
        self._test_category = "End-to-End"
        self._scenario = "Caretaker imposes fine; student views; Warden monitors; no escalation"
        self._expected_final_state = (
            "Fine status=Unpaid; visible to student and Warden; no escalation triggered"
        )

        # Step 1 – Caretaker imposes fine
        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/fine/impose",
            {
                "student_id": self._student_id,
                "amount": 500,
                "category": "Room Damage",
                "reason": "Chair scratched",
            },
            expected_status=None,
        )
        data = resp.json()
        fine_id = data.get("fine_id") or data.get("id")
        step1_ok = data.get("status") == "Unpaid"
        self._add_step(
            1,
            "Caretaker imposes fine with valid amount and reason (BR-HM-013)",
            "Fine created with status=Unpaid; student notified",
            str(data),
            step1_ok,
        )

        # Step 2 – Student views fine
        self.login_as_student()
        resp = self.api_get("/hostel/fine/my-fines", expected_status=None)
        fines = resp.json()
        step2_ok = any(str(f.get("id")) == str(fine_id) for f in fines.get("results", [fines]))
        self._add_step(
            2,
            "Student views fine in 'My Fines' section (BR-HM-012.a)",
            "Fine appears in student view",
            str(fines)[:200],
            step2_ok,
        )

        # Step 3 – Warden monitors
        self.login_as_warden()
        resp = self.api_get("/hostel/fine/monitor", expected_status=None)
        warden_data = resp.json()
        step3_ok = resp.status_code == 200
        self._add_step(
            3,
            "Warden reviews fine dashboard for disciplinary patterns (BR-HM-012.b)",
            "Dashboard data returned",
            str(warden_data)[:200],
            step3_ok,
        )

        # Step 4 – Confirm no escalation (count below threshold)
        step4_ok = warden_data.get("escalation_required") is not True
        self._add_step(
            4,
            "Fine count below threshold; no escalation (BR-HM-014)",
            "escalation_required=False",
            str(warden_data.get("escalation_required")),
            step4_ok,
        )

        if self._all_steps_passed():
            self._record_result("Fine management flow completed; no escalation", "Pass")
        else:
            self._record_result("Fine management flow incomplete", "Fail")
            self.fail("WF-105 E2E-01: Fine management flow failed")

    def test_neg_fine_zero_amount_blocked(self):
        self._test_id = "HM-WF-105-NEG-02"
        self._wf_id = "HM-WF-105"
        self._test_category = "Negative"
        self._scenario = "Fine rejected due to invalid amount (amount=0)"
        self._expected_final_state = "Fine submission blocked; validation error; no fine record created"

        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/fine/impose",
            {"student_id": self._student_id, "amount": 0, "category": "Noise", "reason": "Test"},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code == 400 or "amount" in str(data).lower()
        self._add_step(
            1,
            "Impose fine with amount=0 (BR-HM-013.a)",
            "Validation error returned",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Zero-amount fine guard works", "Pass")
        else:
            self._record_result("Zero-amount fine guard failed", "Fail")
            self.fail("WF-105 NEG-02: Zero-amount fine should be blocked")

    def test_neg_fine_evidence_file_too_large(self):
        self._test_id = "HM-WF-105-NEG-03"
        self._wf_id = "HM-WF-105"
        self._test_category = "Negative"
        self._scenario = "Fine rejected due to evidence file > 5 MB"
        self._expected_final_state = "Upload rejected; fine not submitted; Caretaker prompted to correct"

        self.login_as_caretaker()
        large_file = self._create_dummy_file_bytes(size_mb=6)
        resp = self.api_post(
            "/hostel/fine/impose",
            {
                "student_id": self._student_id,
                "amount": 300,
                "category": "Property Damage",
                "reason": "Broken window",
                "evidence_file": large_file,
            },
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code in (400, 413) or "file" in str(data).lower()
        self._add_step(
            1,
            "Upload evidence file > 5 MB (BR-HM-022)",
            "Upload rejected with file-size error",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("File-size guard works", "Pass")
        else:
            self._record_result("File-size guard failed", "Fail")
            self.fail("WF-105 NEG-03: Oversized evidence file should be rejected")


# ===========================================================================
# HM-WF-106 – Hostel Setup & Staffing Workflow
# ===========================================================================
class TestWF106_HostelSetupFlow(WFTestBase):
    """
    WF-106: Super Admin Creates Hostel → Assigns Staff → Activates
    Actors : Super Admin · System
    BRs    : BR-HM-008 · BR-HM-019 · BR-HM-025
    """

    def test_e2e_hostel_created_staffed_activated(self):
        self._test_id = "HM-WF-106-E2E-01"
        self._wf_id = "HM-WF-106"
        self._test_category = "End-to-End"
        self._scenario = "Super Admin creates hostel, assigns both staff roles, activates"
        self._expected_final_state = (
            "Hostel status=Active; Warden and Caretaker assigned; ready for room allocation"
        )

        self.login_as_super_admin()

        # Step 1 – Create hostel
        resp = self.api_post(
            "/hostel/admin/create",
            {"name": "New Block H", "capacity": 100, "gender": "Male"},
            expected_status=None,
        )
        data = resp.json()
        hostel_id = data.get("hostel_id") or data.get("id")
        step1_ok = data.get("status") == "Inactive"
        self._add_step(
            1,
            "Super Admin creates hostel with valid details (BR-HM-025)",
            "Hostel registered with status=Inactive; unique ID generated",
            str(data),
            step1_ok,
        )

        # Step 2 – Assign Warden
        resp = self.api_post(
            "/hostel/admin/assign-staff",
            {"hostel_id": hostel_id, "role": "Warden", "staff_id": "W-001"},
            expected_status=None,
        )
        step2_ok = resp.json().get("warden_assigned") is True
        self._add_step(
            2,
            "Assign Warden to hostel",
            "warden_assigned=True",
            str(resp.json()),
            step2_ok,
        )

        # Step 3 – Assign Caretaker
        resp = self.api_post(
            "/hostel/admin/assign-staff",
            {"hostel_id": hostel_id, "role": "Caretaker", "staff_id": "C-001"},
            expected_status=None,
        )
        step3_ok = resp.json().get("caretaker_assigned") is True
        self._add_step(
            3,
            "Assign Caretaker to hostel",
            "caretaker_assigned=True",
            str(resp.json()),
            step3_ok,
        )

        # Step 4 – Activate hostel
        resp = self.api_post(
            "/hostel/admin/activate",
            {"hostel_id": hostel_id},
            expected_status=None,
        )
        data = resp.json()
        step4_ok = data.get("status") == "Active"
        self._add_step(
            4,
            "Super Admin activates hostel (BR-HM-008); mandatory staff validated (BR-HM-019)",
            "Hostel status=Active",
            str(data),
            step4_ok,
        )

        if self._all_steps_passed():
            self._record_result("Hostel setup and activation flow completed", "Pass")
        else:
            self._record_result("Hostel setup flow incomplete", "Fail")
            self.fail("WF-106 E2E-01: Hostel setup flow failed")

    def test_neg_activation_without_caretaker_blocked(self):
        self._test_id = "HM-WF-106-NEG-01"
        self._wf_id = "HM-WF-106"
        self._test_category = "Negative"
        self._scenario = "Activation blocked because Caretaker not yet assigned"
        self._expected_final_state = (
            "Activation blocked; hostel remains Inactive; "
            "error: 'Caretaker is required before activation'"
        )

        self.login_as_super_admin()
        hostel_id = self._get_warden_only_hostel_id()   # fixture: hostel with Warden but no Caretaker

        resp = self.api_post(
            "/hostel/admin/activate",
            {"hostel_id": hostel_id},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code in (400, 422) and "caretaker" in str(data).lower()
        self._add_step(
            1,
            "Activate hostel missing Caretaker (BR-HM-019)",
            "Activation blocked with Caretaker required error",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Missing-caretaker activation guard works", "Pass")
        else:
            self._record_result("Missing-caretaker activation guard failed", "Fail")
            self.fail("WF-106 NEG-01: Activation should require Caretaker")

    def test_neg_duplicate_hostel_name_blocked(self):
        self._test_id = "HM-WF-106-NEG-02"
        self._wf_id = "HM-WF-106"
        self._test_category = "Negative"
        self._scenario = "Hostel creation fails due to duplicate name"
        self._expected_final_state = (
            "Hostel not created; validation error: 'A hostel with this name already exists'"
        )

        self.login_as_super_admin()
        resp = self.api_post(
            "/hostel/admin/create",
            {"name": "Existing Hostel", "capacity": 50, "gender": "Female"},   # already exists
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code == 400 and "exist" in str(data).lower()
        self._add_step(
            1,
            "Create hostel with duplicate name (BR-HM-025)",
            "Validation error: name already exists",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Duplicate-name guard works", "Pass")
        else:
            self._record_result("Duplicate-name guard failed", "Fail")
            self.fail("WF-106 NEG-02: Duplicate hostel name should be rejected")


# ===========================================================================
# HM-WF-107 – Security & Guard Shift Management Workflow
# ===========================================================================
class TestWF107_GuardShiftFlow(WFTestBase):
    """
    WF-107: Warden Manages Guard Shifts → System Validates → Security Status Reviewed
    Actors : Warden · System
    BRs    : BR-HM-016 · BR-HM-026 · BR-HM-027
    """

    def test_e2e_valid_schedule_saved_and_reviewed(self):
        self._test_id = "HM-WF-107-E2E-01"
        self._wf_id = "HM-WF-107"
        self._test_category = "End-to-End"
        self._scenario = "Warden creates valid full-coverage schedule; reviews security status"
        self._expected_final_state = (
            "Schedule saved and active; audit trail created; Warden has full security overview"
        )

        self.login_as_warden()

        # Step 1 – Assign guards to all shifts
        resp = self.api_post(
            "/hostel/security/schedule",
            {
                "week": "2025-W32",
                "shifts": [
                    {"day": "Monday", "slot": "Morning", "guard_id": "G-001"},
                    {"day": "Monday", "slot": "Evening", "guard_id": "G-002"},
                    {"day": "Monday", "slot": "Night",   "guard_id": "G-003"},
                    # ... rest of week omitted for brevity; fixture can expand
                ],
            },
            expected_status=None,
        )
        data = resp.json()
        step1_ok = data.get("saved") is True
        self._add_step(
            1,
            "Warden assigns guards; no overlaps (BR-HM-016); coverage met (BR-HM-026)",
            "Schedule saved; guards notified; audit log created (BR-HM-027)",
            str(data),
            step1_ok,
        )

        # Step 2 – Review consolidated security dashboard
        resp = self.api_get("/hostel/security/status", expected_status=None)
        data = resp.json()
        step2_ok = resp.status_code == 200 and data.get("coverage_status") is not None
        self._add_step(
            2,
            "Warden reviews security dashboard",
            "Dashboard data returned with deployment and incident info",
            str(data)[:200],
            step2_ok,
        )

        if self._all_steps_passed():
            self._record_result("Guard shift management flow completed", "Pass")
        else:
            self._record_result("Guard shift management flow incomplete", "Fail")
            self.fail("WF-107 E2E-01: Security schedule flow failed")

    def test_neg_coverage_gap_blocks_save(self):
        self._test_id = "HM-WF-107-NEG-01"
        self._wf_id = "HM-WF-107"
        self._test_category = "Negative"
        self._scenario = "Schedule save blocked due to night-shift coverage gap"
        self._expected_final_state = (
            "Save blocked; night shift highlighted as coverage gap; schedule not saved"
        )

        self.login_as_warden()
        resp = self.api_post(
            "/hostel/security/schedule",
            {
                "week": "2025-W33",
                "shifts": [
                    {"day": "Monday", "slot": "Morning", "guard_id": "G-001"},
                    {"day": "Monday", "slot": "Evening", "guard_id": "G-002"},
                    # Night shift intentionally missing
                ],
            },
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code == 400 and "night" in str(data).lower()
        self._add_step(
            1,
            "Save schedule with missing night shift (BR-HM-026)",
            "Coverage gap error; save blocked",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Coverage gap guard works", "Pass")
        else:
            self._record_result("Coverage gap guard failed", "Fail")
            self.fail("WF-107 NEG-01: Schedule with coverage gap should not save")

    def test_neg_overlapping_shift_assignment_rejected(self):
        self._test_id = "HM-WF-107-NEG-02"
        self._wf_id = "HM-WF-107"
        self._test_category = "Negative"
        self._scenario = "Same guard assigned to Morning and Evening on the same day"
        self._expected_final_state = "Assignment rejected with conflict error; Warden revises"

        self.login_as_warden()
        resp = self.api_post(
            "/hostel/security/schedule",
            {
                "week": "2025-W34",
                "shifts": [
                    {"day": "Tuesday", "slot": "Morning", "guard_id": "G-005"},
                    {"day": "Tuesday", "slot": "Evening", "guard_id": "G-005"},  # duplicate
                    {"day": "Tuesday", "slot": "Night",   "guard_id": "G-006"},
                ],
            },
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code == 400 and "conflict" in str(data).lower()
        self._add_step(
            1,
            "Overlapping shift assignment (BR-HM-016)",
            "Conflict error returned; assignment rejected",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Overlap conflict guard works", "Pass")
        else:
            self._record_result("Overlap conflict guard failed", "Fail")
            self.fail("WF-107 NEG-02: Overlapping shifts should be rejected")


# ===========================================================================
# HM-WF-108 – Inventory Management Workflow
# ===========================================================================
class TestWF108_InventoryManagementFlow(WFTestBase):
    """
    WF-108: Caretaker Inspects Inventory → Logs Issues → Raises Resource Request
    Actors : Caretaker · System
    BRs    : BR-HM-021 · BR-HM-030 · BR-HM-031
    """

    def test_e2e_inventory_discrepancy_logged_request_raised(self):
        self._test_id = "HM-WF-108-E2E-01"
        self._wf_id = "HM-WF-108"
        self._test_category = "End-to-End"
        self._scenario = "Caretaker finds damaged items; logs discrepancy; raises resource request"
        self._expected_final_state = (
            "Inventory updated with discrepancy log; resource request=Pending; audit trail maintained"
        )

        self.login_as_caretaker()

        # Step 1 – Log discrepancy
        resp = self.api_post(
            "/hostel/inventory/discrepancy",
            {
                "item_id": "CHAIR-101",
                "type": "Damaged",
                "quantity": 3,
                "remarks": "Legs broken",
            },
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code in (200, 201)
        self._add_step(
            1,
            "Caretaker marks 3 chairs as damaged (BR-HM-021)",
            "Discrepancy saved with details",
            str(data),
            step1_ok,
        )

        # Step 2 – Update inventory records
        resp = self.api_post(
            "/hostel/inventory/update",
            {"item_id": "CHAIR-101", "quantity": 17, "condition": "Damaged"},
            expected_status=None,
        )
        step2_ok = resp.json().get("audit_log_created") is True
        self._add_step(
            2,
            "Caretaker updates inventory quantity and condition (BR-HM-031)",
            "Inventory updated; audit log entry created",
            str(resp.json()),
            step2_ok,
        )

        # Step 3 – Raise resource request
        resp = self.api_post(
            "/hostel/inventory/resource-request",
            {
                "item_id": "CHAIR-101",
                "quantity_needed": 3,
                "justification": "3 chairs damaged beyond repair",
            },
            expected_status=None,
        )
        data = resp.json()
        step3_ok = data.get("status") == "Pending"
        self._add_step(
            3,
            "Resource request submitted (BR-HM-030); forwarded to Warden and Super Admin",
            "Request status=Pending",
            str(data),
            step3_ok,
        )

        if self._all_steps_passed():
            self._record_result("Inventory discrepancy and request flow completed", "Pass")
        else:
            self._record_result("Inventory flow incomplete", "Fail")
            self.fail("WF-108 E2E-01: Inventory management flow failed")

    def test_neg_resource_request_missing_justification(self):
        self._test_id = "HM-WF-108-NEG-02"
        self._wf_id = "HM-WF-108"
        self._test_category = "Negative"
        self._scenario = "Resource request rejected due to missing justification"
        self._expected_final_state = "Request blocked; validation error; no approval workflow initiated"

        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/inventory/resource-request",
            {"item_id": "TABLE-005", "quantity_needed": 2, "justification": ""},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code == 400 and "justification" in str(data).lower()
        self._add_step(
            1,
            "Submit resource request without justification (BR-HM-030)",
            "Validation error returned",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Missing-justification guard works", "Pass")
        else:
            self._record_result("Missing-justification guard failed", "Fail")
            self.fail("WF-108 NEG-02: Resource request without justification should be blocked")

    def test_neg_inventory_update_negative_quantity(self):
        self._test_id = "HM-WF-108-NEG-03"
        self._wf_id = "HM-WF-108"
        self._test_category = "Negative"
        self._scenario = "Inventory update with negative quantity"
        self._expected_final_state = "Update rejected with validation error; records unchanged"

        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/inventory/update",
            {"item_id": "BED-012", "quantity": -2, "condition": "Good"},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code == 400 and "quantity" in str(data).lower()
        self._add_step(
            1,
            "Inventory update with quantity=-2 (BR-HM-031)",
            "Validation error; quantity must be ≥ 0",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Negative-quantity guard works", "Pass")
        else:
            self._record_result("Negative-quantity guard failed", "Fail")
            self.fail("WF-108 NEG-03: Negative inventory quantity should be rejected")


# ===========================================================================
# HM-WF-109 – Student Room Vacation & Clearance Workflow
# ===========================================================================
class TestWF109_RoomVacationFlow(WFTestBase):
    """
    WF-109: Student Requests Vacation → Caretaker Clears → Super Admin Finalizes
    Actors : Student · Caretaker · Super Admin · System
    BRs    : BR-HM-015 · BR-HM-023 · BR-HM-028
    """

    def test_e2e_full_clearance_vacation_completed(self):
        self._test_id = "HM-WF-109-E2E-01"
        self._wf_id = "HM-WF-109"
        self._test_category = "End-to-End"
        self._scenario = "Student with all clearances satisfied completes room vacation"
        self._expected_final_state = (
            "Room deallocated; room status=Available; hostel history archived; "
            "vacation request=Completed; student notified"
        )

        # Step 1 – Student submits vacation request
        self.login_as_student()
        resp = self.api_post(
            "/hostel/vacation/request",
            {"vacation_date": "2025-11-01", "reason": "Course completion"},
            expected_status=None,
        )
        data = resp.json()
        vac_id = data.get("request_id") or data.get("id")
        step1_ok = data.get("status") == "Pending Clearance"
        self._add_step(
            1,
            "Student submits vacation request; checklist generated (BR-HM-015.c)",
            "status=Pending Clearance; checklist received",
            str(data),
            step1_ok,
        )

        # Step 2 – Caretaker issues clearance
        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/vacation/clearance",
            {
                "request_id": vac_id,
                "no_fines": True,
                "items_returned": True,
                "no_damages": True,
                "attendance_ok": True,
            },
            expected_status=None,
        )
        data = resp.json()
        step2_ok = data.get("status") == "Clearance Approved"
        self._add_step(
            2,
            "Caretaker verifies all clearance items (BR-HM-015.b)",
            "All clear; status=Clearance Approved",
            str(data),
            step2_ok,
        )

        # Step 3 – Super Admin finalizes vacation
        self.login_as_super_admin()
        resp = self.api_post(
            "/hostel/vacation/finalize",
            {"request_id": vac_id},
            expected_status=None,
        )
        data = resp.json()
        step3_ok = data.get("status") == "Completed" and data.get("room_status") == "Available"
        self._add_step(
            3,
            "Super Admin finalizes vacation (BR-HM-028); room deallocated (BR-HM-023)",
            "status=Completed; room=Available; history archived",
            str(data),
            step3_ok,
        )

        if self._all_steps_passed():
            self._record_result("Full vacation and clearance flow completed", "Pass")
        else:
            self._record_result("Vacation flow incomplete", "Fail")
            self.fail("WF-109 E2E-01: Room vacation flow failed")

    def test_neg_finalization_without_clearance_blocked(self):
        self._test_id = "HM-WF-109-NEG-03"
        self._wf_id = "HM-WF-109"
        self._test_category = "Negative"
        self._scenario = "Finalization attempted without clearance approval"
        self._expected_final_state = "Finalization blocked: 'Prerequisites not satisfied'"

        vac_id = self._get_pending_clearance_request_id()   # fixture

        self.login_as_super_admin()
        resp = self.api_post(
            "/hostel/vacation/finalize",
            {"request_id": vac_id},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code in (400, 422) and "prerequisite" in str(data).lower()
        self._add_step(
            1,
            "Finalize vacation without clearance approval (BR-HM-028)",
            "Finalization blocked; prerequisites not satisfied",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Finalization prerequisite guard works", "Pass")
        else:
            self._record_result("Finalization prerequisite guard failed", "Fail")
            self.fail("WF-109 NEG-03: Finalization without clearance should be blocked")


# ===========================================================================
# HM-WF-110 – Staff Notice Management Workflow
# ===========================================================================
class TestWF110_NoticeManagementFlow(WFTestBase):
    """
    WF-110: Staff Creates Notice → Notifies Students → Auto-Archives on Expiry
    Actors : Caretaker · Warden · Student · System
    BRs    : BR-HM-029 · BR-HM-033 · BR-HM-035 · BR-HM-039
    """

    def test_e2e_urgent_notice_published_archived(self):
        self._test_id = "HM-WF-110-E2E-01"
        self._wf_id = "HM-WF-110"
        self._test_category = "End-to-End"
        self._scenario = "Staff publishes Urgent notice; students notified; auto-archived after expiry"
        self._expected_final_state = (
            "Notice published; read status tracked; expired notice archived; accessible in history"
        )

        self.login_as_caretaker()

        # Step 1 – Publish urgent notice
        resp = self.api_post(
            "/hostel/notice/publish",
            {
                "title": "Urgent Water Supply Disruption",
                "description": "Water supply interrupted from 8 AM to 12 PM tomorrow.",
                "priority": "Urgent",
                "audience": "All",
                "end_date": "2025-08-15",
            },
            expected_status=None,
        )
        data = resp.json()
        notice_id = data.get("notice_id") or data.get("id")
        step1_ok = data.get("status") == "Published"
        self._add_step(
            1,
            "Staff publishes Urgent notice; content validated (BR-HM-029); "
            "push notification sent immediately (BR-HM-033.b)",
            "Notice published with Urgent priority; red banner set (BR-HM-035.a)",
            str(data),
            step1_ok,
        )

        # Step 2 – Student sees notice with red banner
        self.login_as_student()
        resp = self.api_get("/hostel/notice/board", expected_status=None)
        board = resp.json()
        found = any(str(n.get("id")) == str(notice_id) for n in board.get("notices", []))
        step2_ok = found
        self._add_step(
            2,
            "Student views notice board (BR-HM-035.c)",
            "Urgent notice visible with red banner",
            str(board)[:200],
            step2_ok,
        )

        # Step 3 – Student marks as read
        resp = self.api_post(
            "/hostel/notice/mark-read",
            {"notice_id": notice_id},
            expected_status=None,
        )
        step3_ok = resp.json().get("read") is True
        self._add_step(
            3,
            "Student marks notice as read",
            "read=True recorded",
            str(resp.json()),
            step3_ok,
        )

        if self._all_steps_passed():
            self._record_result("Urgent notice publish and read flow completed", "Pass")
        else:
            self._record_result("Notice flow incomplete", "Fail")
            self.fail("WF-110 E2E-01: Notice management flow failed")

    def test_neg_notice_title_too_short_blocked(self):
        self._test_id = "HM-WF-110-NEG-01"
        self._wf_id = "HM-WF-110"
        self._test_category = "Negative"
        self._scenario = "Notice publication blocked due to short title (< 5 chars)"
        self._expected_final_state = (
            "Publication blocked; validation error: title must be 5-200 characters"
        )

        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/notice/publish",
            {
                "title": "Hi",
                "description": "Short title test.",
                "priority": "Normal",
                "audience": "All",
                "end_date": "2025-08-20",
            },
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code == 400 and "title" in str(data).lower()
        self._add_step(
            1,
            "Publish notice with title='Hi' (BR-HM-029.a)",
            "Validation error: title length 5-200 required",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Title length guard works", "Pass")
        else:
            self._record_result("Title length guard failed", "Fail")
            self.fail("WF-110 NEG-01: Short-title notice should be blocked")

    def test_neg_cross_hostel_notice_not_visible(self):
        self._test_id = "HM-WF-110-NEG-02"
        self._wf_id = "HM-WF-110"
        self._test_category = "Negative"
        self._scenario = "Student from Hostel-B cannot see Hostel-A notice"
        self._expected_final_state = (
            "Hostel-B student sees only their own hostel and All-Students notices"
        )

        notice_id_hostel_a = self._get_hostel_a_notice_id()    # fixture

        self.login_as_hostel_b_student()
        resp = self.api_get("/hostel/notice/board", expected_status=None)
        board = resp.json()
        found = any(str(n.get("id")) == str(notice_id_hostel_a) for n in board.get("notices", []))
        step1_ok = not found
        self._add_step(
            1,
            "Hostel-B student accesses notice board (BR-HM-035.c, BR-HM-039.a)",
            "Hostel-A notice NOT visible",
            str(board)[:200],
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Hostel-specific notice filter works", "Pass")
        else:
            self._record_result("Hostel notice filter failed", "Fail")
            self.fail("WF-110 NEG-02: Cross-hostel notice visibility leak detected")


# ===========================================================================
# HM-WF-111 – Staff Report Generation Workflow
# ===========================================================================
class TestWF111_ReportGenerationFlow(WFTestBase):
    """
    WF-111: Warden Generates Report → Submits to Super Admin → Reviews & Downloads
    Actors : Warden · Caretaker · Super Admin · System
    BRs    : BR-HM-040 · BR-HM-043–046 · BR-HM-050
    """

    def test_e2e_report_generated_submitted_approved_downloaded(self):
        self._test_id = "HM-WF-111-E2E-01"
        self._wf_id = "HM-WF-111"
        self._test_category = "End-to-End"
        self._scenario = "Warden generates report, submits; Super Admin approves and downloads"
        self._expected_final_state = (
            "Report submitted and approved; downloaded by Super Admin; audit trail maintained"
        )

        self.login_as_warden()

        # Step 1 – Generate report
        resp = self.api_post(
            "/hostel/report/generate",
            {"type": "Monthly Summary", "start_date": "2025-07-01", "end_date": "2025-07-31"},
            expected_status=None,
        )
        data = resp.json()
        report_id = data.get("report_id") or data.get("id")
        step1_ok = data.get("status") == "Generated"
        self._add_step(
            1,
            "Warden selects report type and date range; system generates (BR-HM-040, BR-HM-043, BR-HM-044)",
            "Report generated with statistics and charts",
            str(data),
            step1_ok,
        )

        # Step 2 – Submit to Super Admin
        resp = self.api_post(
            "/hostel/report/submit",
            {"report_id": report_id, "notes": "July monthly report for review"},
            expected_status=None,
        )
        data = resp.json()
        step2_ok = data.get("status") == "Submitted"
        self._add_step(
            2,
            "Warden submits to Super Admin with notes (BR-HM-045)",
            "status=Submitted; timestamp recorded; Super Admin notified",
            str(data),
            step2_ok,
        )

        # Step 3 – Super Admin approves and downloads
        self.login_as_super_admin()
        resp = self.api_post(
            "/hostel/report/download",
            {"report_id": report_id, "format": "PDF"},
            expected_status=None,
        )
        data = resp.json()
        step3_ok = data.get("download_url") is not None and data.get("audit_logged") is True
        self._add_step(
            3,
            "Super Admin downloads report as PDF (BR-HM-050); audit logged",
            "download_url returned; audit_logged=True",
            str(data),
            step3_ok,
        )

        if self._all_steps_passed():
            self._record_result("Report generation and approval flow completed", "Pass")
        else:
            self._record_result("Report flow incomplete", "Fail")
            self.fail("WF-111 E2E-01: Report generation flow failed")

    def test_neg_caretaker_cannot_submit_directly_to_super_admin(self):
        self._test_id = "HM-WF-111-NEG-02"
        self._wf_id = "HM-WF-111"
        self._test_category = "Negative"
        self._scenario = "Caretaker attempts to submit report directly to Super Admin"
        self._expected_final_state = "Submission denied: Caretakers must submit to their Warden"

        self.login_as_caretaker()
        report_id = self._get_caretaker_generated_report_id()   # fixture

        resp = self.api_post(
            "/hostel/report/submit",
            {"report_id": report_id, "submit_to": "super_admin"},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code in (400, 403) and "warden" in str(data).lower()
        self._add_step(
            1,
            "Caretaker submits directly to Super Admin (BR-HM-045.b)",
            "Submission denied; must go through Warden",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Caretaker direct-to-admin submission guard works", "Pass")
        else:
            self._record_result("Caretaker submission guard failed", "Fail")
            self.fail("WF-111 NEG-02: Caretaker direct Super Admin submission should be denied")

    def test_neg_report_generation_invalid_date_range(self):
        self._test_id = "HM-WF-111-NEG-03"
        self._wf_id = "HM-WF-111"
        self._test_category = "Negative"
        self._scenario = "Report generation fails with end_date before start_date"
        self._expected_final_state = "Validation error; problematic fields highlighted; no report generated"

        self.login_as_warden()
        resp = self.api_post(
            "/hostel/report/generate",
            {"type": "Monthly Summary", "start_date": "2025-07-31", "end_date": "2025-07-01"},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code == 400 and "date" in str(data).lower()
        self._add_step(
            1,
            "Generate report with end_date < start_date (BR-HM-043)",
            "Validation error; date fields highlighted",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Date range validation guard works", "Pass")
        else:
            self._record_result("Date range validation guard failed", "Fail")
            self.fail("WF-111 NEG-03: Invalid date range should block report generation")


# ===========================================================================
# HM-WF-112 – Student Guest Room Booking Workflow
# ===========================================================================
class TestWF112_GuestRoomBookingFlow(WFTestBase):
    """
    WF-112: Student Requests Guest Room → Caretaker Approves → Check-in / Check-out
    Actors : Student · Caretaker · System
    BRs    : BR-HM-051 to BR-HM-059
    """

    def test_e2e_booking_approved_checkin_checkout_no_damage(self):
        self._test_id = "HM-WF-112-E2E-01"
        self._wf_id = "HM-WF-112"
        self._test_category = "End-to-End"
        self._scenario = "Student books guest room; approved; check-in and check-out without damages"
        self._expected_final_state = (
            "Booking completed; room=Available; no fines; complete booking record maintained"
        )

        # Step 1 – Student submits booking
        self.login_as_student()
        resp = self.api_post(
            "/hostel/guest-room/book",
            {
                "guest_name": "John Doe",
                "checkin_date": "2025-09-01",
                "checkout_date": "2025-09-03",
                "purpose": "Family visit",
            },
            expected_status=None,
        )
        data = resp.json()
        booking_id = data.get("booking_id") or data.get("id")
        step1_ok = data.get("status") == "Pending"
        self._add_step(
            1,
            "Student submits booking with valid details (BR-HM-052, BR-HM-053, BR-HM-054)",
            "Booking status=Pending; Caretaker notified",
            str(data),
            step1_ok,
        )

        # Step 2 – Caretaker approves
        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/guest-room/respond",
            {"booking_id": booking_id, "action": "approve"},
            expected_status=None,
        )
        data = resp.json()
        step2_ok = data.get("status") == "Approved"
        self._add_step(
            2,
            "Caretaker verifies eligibility (BR-HM-051) and approves; "
            "room reserved (BR-HM-059)",
            "status=Approved; room reserved; student notified",
            str(data),
            step2_ok,
        )

        # Step 3 – Check-in
        resp = self.api_post(
            "/hostel/guest-room/checkin",
            {"booking_id": booking_id, "guest_id_verified": True},
            expected_status=None,
        )
        data = resp.json()
        step3_ok = data.get("status") == "Checked-In"
        self._add_step(
            3,
            "Caretaker verifies guest identity and checks in (BR-HM-056)",
            "status=Checked-In",
            str(data),
            step3_ok,
        )

        # Step 4 – Check-out (no damages)
        resp = self.api_post(
            "/hostel/guest-room/checkout",
            {"booking_id": booking_id, "damages_found": False},
            expected_status=None,
        )
        data = resp.json()
        step4_ok = data.get("status") == "Completed" and data.get("room_status") == "Available"
        self._add_step(
            4,
            "Caretaker inspects room (BR-HM-057); no damages; check-out completed",
            "Booking=Completed; room=Available",
            str(data),
            step4_ok,
        )

        if self._all_steps_passed():
            self._record_result("Guest room booking full lifecycle completed", "Pass")
        else:
            self._record_result("Guest room booking flow incomplete", "Fail")
            self.fail("WF-112 E2E-01: Guest room booking flow failed")

    def test_neg_booking_max_concurrent_limit_reached(self):
        self._test_id = "HM-WF-112-NEG-02"
        self._wf_id = "HM-WF-112"
        self._test_category = "Negative"
        self._scenario = "Student submits new booking when already at 3 active bookings"
        self._expected_final_state = "Booking rejected: maximum concurrent bookings limit reached"

        self.login_as_max_bookings_student()     # fixture: student with 3 active bookings
        resp = self.api_post(
            "/hostel/guest-room/book",
            {
                "guest_name": "Jane Doe",
                "checkin_date": "2025-10-01",
                "checkout_date": "2025-10-02",
                "purpose": "Visit",
            },
            expected_status=None,
        )
        data = resp.json()
        step1_ok = resp.status_code in (400, 409) and "limit" in str(data).lower()
        self._add_step(
            1,
            "Submit booking when already at maximum active count (BR-HM-051.d)",
            "Booking rejected: concurrent limit reached",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Concurrent booking limit guard works", "Pass")
        else:
            self._record_result("Concurrent booking limit guard failed", "Fail")
            self.fail("WF-112 NEG-02: Booking over concurrent limit should be rejected")

    def test_neg_checkout_with_damages_fine_imposed(self):
        self._test_id = "HM-WF-112-NEG-03"
        self._wf_id = "HM-WF-112"
        self._test_category = "Negative"
        self._scenario = "Guest damages found at check-out; fine imposed"
        self._expected_final_state = (
            "Booking=Completed with Damages; fine=Unpaid; room=Available; student notified"
        )

        booking_id = self._get_checked_in_booking_id()    # fixture

        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/guest-room/checkout",
            {
                "booking_id": booking_id,
                "damages_found": True,
                "damage_description": "Broken chair leg",
                "repair_cost": 750,
            },
            expected_status=None,
        )
        data = resp.json()
        step1_ok = (
            data.get("status") == "Completed"
            and data.get("fine_imposed") is True
            and data.get("fine_status") == "Unpaid"
        )
        self._add_step(
            1,
            "Check-out with damages; fine linked to booking (BR-HM-057, BR-HM-058)",
            "Booking=Completed with Damages; fine=Unpaid",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Damage-fine checkout flow works", "Pass")
        else:
            self._record_result("Damage-fine checkout flow failed", "Fail")
            self.fail("WF-112 NEG-03: Damage-at-checkout fine imposition failed")


# ===========================================================================
# HM-WF-113 – Extended Stay During Vacations Management Workflow
# ===========================================================================
class TestWF113_ExtendedStayFlow(WFTestBase):
    """
    WF-113: Student Applies for Extended Stay → Staff Approves →
            System Manages Operations → Completion / Termination
    Actors : Student · Caretaker · Warden · System
    BRs    : BR-HM-061 to BR-HM-067 · BR-HM-073 · BR-HM-074
    """

    def test_e2e_extended_stay_approved_completed(self):
        self._test_id = "HM-WF-113-E2E-01"
        self._wf_id = "HM-WF-113"
        self._test_category = "End-to-End"
        self._scenario = "Student applies with valid auth; approved; pays charges; completes stay"
        self._expected_final_state = (
            "Extended stay completed; charges paid; room released; "
            "stay record archived; no violations; report generated"
        )

        # Step 1 – Student submits application
        self.login_as_student()
        resp = self.api_post(
            "/hostel/extended-stay/apply",
            {
                "start_date": "2025-12-01",
                "end_date": "2025-12-15",
                "reason": "Research thesis work",
                "faculty_authorization": "auth_doc_base64_here",
            },
            expected_status=None,
        )
        data = resp.json()
        stay_id = data.get("stay_id") or data.get("id")
        step1_ok = data.get("status") == "Pending"
        self._add_step(
            1,
            "Student submits application with dates in vacation window (BR-HM-062) "
            "and faculty authorization (BR-HM-063); charges calculated (BR-HM-064)",
            "status=Pending; charges displayed; eligibility checked (BR-HM-061)",
            str(data),
            step1_ok,
        )

        # Step 2 – Staff approves
        self.login_as_warden()
        resp = self.api_post(
            "/hostel/extended-stay/review",
            {"stay_id": stay_id, "action": "approve"},
            expected_status=None,
        )
        data = resp.json()
        step2_ok = data.get("status") == "Approved"
        self._add_step(
            2,
            "Warden verifies authorization (BR-HM-066) and room availability (BR-HM-067); approves",
            "status=Approved; room reserved; charge notification sent (BR-HM-073)",
            str(data),
            step2_ok,
        )

        # Step 3 – Student pays charges
        self.login_as_student()
        resp = self.api_post(
            "/hostel/extended-stay/payment",
            {"stay_id": stay_id, "payment_status": "Paid"},
            expected_status=None,
        )
        step3_ok = resp.json().get("payment_status") == "Paid"
        self._add_step(
            3,
            "Student pays charges within deadline (BR-HM-073)",
            "payment_status=Paid",
            str(resp.json()),
            step3_ok,
        )

        # Step 4 – Services coordinated and stay completed
        # (Simulated: trigger system end-of-stay processing)
        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/extended-stay/complete",
            {"stay_id": stay_id},
            expected_status=None,
        )
        data = resp.json()
        step4_ok = data.get("status") == "Completed" and data.get("report_generated") is True
        self._add_step(
            4,
            "Services coordinated (BR-HM-074); no violations; stay completed",
            "status=Completed; occupancy updated; completion report generated",
            str(data),
            step4_ok,
        )

        if self._all_steps_passed():
            self._record_result("Extended stay full lifecycle completed", "Pass")
        else:
            self._record_result("Extended stay flow incomplete", "Fail")
            self.fail("WF-113 E2E-01: Extended stay flow failed")

    def test_neg_approval_revoked_due_to_non_payment(self):
        self._test_id = "HM-WF-113-NEG-02"
        self._wf_id = "HM-WF-113"
        self._test_category = "Negative"
        self._scenario = "Approval revoked because payment not received by deadline"
        self._expected_final_state = (
            "Approval revoked; room reservation cancelled; "
            "student notified; application status=Cancelled"
        )

        stay_id = self._get_approved_unpaid_stay_id()   # fixture: approved but payment not made

        # Simulate timeout trigger
        self.login_as_system_admin()         # or admin triggering the daily cron
        resp = self.api_post(
            "/hostel/extended-stay/payment-timeout",
            {"stay_id": stay_id},
            expected_status=None,
        )
        data = resp.json()
        step1_ok = data.get("status") == "Cancelled" and data.get("reason") == "Non-payment"
        self._add_step(
            1,
            "Payment deadline expires; system revokes approval (BR-HM-073.a, BR-HM-073.d)",
            "status=Cancelled; room released; student notified",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Non-payment revocation works", "Pass")
        else:
            self._record_result("Non-payment revocation failed", "Fail")
            self.fail("WF-113 NEG-02: Non-payment should revoke extended stay approval")

    def test_neg_stay_terminated_major_violation(self):
        self._test_id = "HM-WF-113-NEG-03"
        self._wf_id = "HM-WF-113"
        self._test_category = "Negative"
        self._scenario = "Stay terminated due to major violation (unauthorized guest)"
        self._expected_final_state = (
            "Stay terminated; fine imposed; violation logged; "
            "room released; future eligibility affected for 1 year"
        )

        stay_id = self._get_active_extended_stay_id()   # fixture: active extended stay

        self.login_as_caretaker()
        resp = self.api_post(
            "/hostel/extended-stay/violation",
            {
                "stay_id": stay_id,
                "severity": "Major",
                "description": "Unauthorized guest found in room",
                "fine_amount": 1000,
            },
            expected_status=None,
        )
        data = resp.json()
        step1_ok = (
            data.get("stay_status") == "Terminated"
            and data.get("fine_imposed") is True
            and data.get("eligibility_suspended_years") == 1
        )
        self._add_step(
            1,
            "Caretaker records Major violation; stay terminated (BR-HM-076)",
            "Stay terminated; fine imposed; 1-year eligibility suspension",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Major violation termination flow works", "Pass")
        else:
            self._record_result("Major violation termination flow failed", "Fail")
            self.fail("WF-113 NEG-03: Major violation should terminate extended stay")

    def test_neg_capacity_limit_reached_waitlist(self):
        self._test_id = "HM-WF-113-NEG-04"
        self._wf_id = "HM-WF-113"
        self._test_category = "Negative"
        self._scenario = "Capacity limit (30%) reached; new application placed on waitlist"
        self._expected_final_state = (
            "Application moved to waitlist; student notified: 'Capacity reached'"
        )

        self.login_as_student()
        resp = self.api_post(
            "/hostel/extended-stay/apply",
            {
                "start_date": "2025-12-01",
                "end_date": "2025-12-10",
                "reason": "Project work",
                "faculty_authorization": "auth_doc_base64_here",
            },
            expected_status=None,
        )
        data = resp.json()
        step1_ok = data.get("status") == "Waitlisted" or "waitlist" in str(data).lower()
        self._add_step(
            1,
            "Apply when hostel extended-stay capacity is at 30% limit (BR-HM-067.b)",
            "Application placed on waitlist; student notified",
            str(data),
            step1_ok,
        )

        if self._all_steps_passed():
            self._record_result("Capacity waitlist logic works", "Pass")
        else:
            self._record_result("Capacity waitlist logic failed", "Fail")
            self.fail("WF-113 NEG-04: Application should be waitlisted when capacity is full")
