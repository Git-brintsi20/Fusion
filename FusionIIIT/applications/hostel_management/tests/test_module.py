from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from applications.hostel_management.services import (
	_parse_room_identifier,
	build_student_details_for_hall,
	get_staff_assigned_hall,
	is_user_faculty,
	is_user_staff,
)


class HostelManagementUtilsTests(SimpleTestCase):
	def test_parse_room_identifier_dash_format(self):
		block, room = _parse_room_identifier("A-101")
		self.assertEqual(block, "A")
		self.assertEqual(room, "101")

	def test_parse_room_identifier_compact_format(self):
		block, room = _parse_room_identifier("B201")
		self.assertEqual(block, "B")
		self.assertEqual(room, "201")

	def test_parse_room_identifier_invalid(self):
		block, room = _parse_room_identifier("")
		self.assertIsNone(block)
		self.assertIsNone(room)


class HostelManagementServicesTests(SimpleTestCase):
	@patch("applications.hostel_management.services.Staff")
	def test_is_user_staff_true(self, StaffMock):
		StaffMock.objects.filter.return_value.exists.return_value = True
		self.assertTrue(is_user_staff(MagicMock()))

	@patch("applications.hostel_management.services.Staff")
	def test_is_user_staff_false(self, StaffMock):
		StaffMock.objects.filter.return_value.exists.return_value = False
		self.assertFalse(is_user_staff(MagicMock()))

	@patch("applications.hostel_management.services.Faculty")
	def test_is_user_faculty_true(self, FacultyMock):
		FacultyMock.objects.filter.return_value.exists.return_value = True
		self.assertTrue(is_user_faculty(MagicMock()))

	@patch("applications.hostel_management.services.HallWarden")
	@patch("applications.hostel_management.services.HallCaretaker")
	def test_get_staff_assigned_hall_prefers_caretaker(self, CaretakerMock, WardenMock):
		hall = MagicMock()

		caretaker_qs = MagicMock()
		caretaker_qs.select_related.return_value.first.return_value = MagicMock(hall=hall)
		CaretakerMock.objects.filter.return_value = caretaker_qs

		warden_qs = MagicMock()
		warden_qs.select_related.return_value.first.return_value = MagicMock(hall=MagicMock())
		WardenMock.objects.filter.return_value = warden_qs

		user = MagicMock(is_authenticated=True)
		user.extrainfo.id = 123

		self.assertIs(get_staff_assigned_hall(user), hall)

	@patch("applications.hostel_management.services.Student")
	def test_build_student_details_for_hall_structure(self, StudentMock):
		hall = MagicMock(hall_id="hall1")

		extra = MagicMock()
		extra.id = "2019XX"
		extra.address = "Addr"
		extra.phone_no = "999"
		extra.user.first_name = "Alex"

		student = MagicMock()
		student.id = extra
		student.programme = "BTech"
		student.batch = "2019"
		student.hall_no = 1
		student.room_no = "A-101"
		student.specialization = "CSE"

		qs = MagicMock()
		qs.select_related.return_value = [student]
		StudentMock.objects.filter.return_value = qs

		payload = build_student_details_for_hall(hall, include_available_rooms=False)
		self.assertIn("students", payload)
		self.assertEqual(len(payload["students"]), 1)
		self.assertEqual(payload["students"][0]["student_id"], "2019XX")
