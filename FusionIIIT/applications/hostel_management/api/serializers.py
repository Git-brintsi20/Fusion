from rest_framework import serializers

from ..models import (
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
    HostelStudentAttendence,
    HostelTransactionHistory,
    StaffSchedule,
    StudentDetails,
    WorkerReport,
)


class HallSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hall
        fields = "__all__"


class HallRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = HallRoom
        fields = "__all__"


class HallCaretakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HallCaretaker
        fields = "__all__"


class HallWardenSerializer(serializers.ModelSerializer):
    class Meta:
        model = HallWarden
        fields = "__all__"


class StaffScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffSchedule
        fields = "__all__"


class HostelNoticeBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelNoticeBoard
        fields = "__all__"


class HostelStudentAttendenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelStudentAttendence
        fields = "__all__"


class GuestRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestRoom
        fields = "__all__"


class GuestRoomBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuestRoomBooking
        fields = "__all__"


class WorkerReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkerReport
        fields = "__all__"


class HostelLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelLeave
        fields = "__all__"


class HostelComplaintSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelComplaint
        fields = "__all__"


class HostelAllotmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelAllotment
        fields = "__all__"


class StudentDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentDetails
        fields = "__all__"


class HostelFineSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelFine
        fields = "__all__"


class HostelInventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelInventory
        fields = "__all__"


class HostelTransactionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelTransactionHistory
        fields = "__all__"


class HostelHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HostelHistory
        fields = "__all__"
