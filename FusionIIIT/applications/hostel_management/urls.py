from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import include
from django.contrib import admin
from django.conf.urls import url, include

from .api.urls import urlpatterns as api_urlpatterns

app_name = 'hostelmanagement'

urlpatterns = [

    path('admin/', admin.site.urls),
    #Home 
    path('', views.hostel_view, name="hostel_view"),
    path('hello', views.hostel_view, name="hello"),

    #Notice Board
    path('notice_form/', views.notice_board, name="notice_board"),
    path('create_notice/', views.notice_board, name='notice_board_create'),
    path('update_notice/', views.update_notice, name='notice_board_update'),
    path('delete_notice/', views.delete_notice, name="delete_notice"),

    # Warden room allotment
    path('assign-roomsbywarden/', views.assign_rooms_by_warden, name='assign_rooms_by_warden'),
    path('update-student-allotment/', views.update_student_allotment, name='update_student_allotment'),

    #Worker Schedule
    path('edit_schedule/', views.staff_edit_schedule, name='staff_edit_schedule'),
    path('delete_schedule/', views.staff_delete_schedule, name='staff_delete_schedule'),
    
    #Student Room
    path('edit_student/',views.edit_student_room,name="edit_student_room"),
    path('edit_student_rooms_sheet/', views.edit_student_rooms_sheet, name="edit_student_rooms_sheet"),

    #Attendance
    path('edit_attendance/', views.edit_attendance, name='edit_attendance'),

    #Attendance
    path('edit_attendance/', views.edit_attendance, name='edit_attendance'),

    #Worker Report
    path('worker_report/', views.generate_worker_report, name='workerreport'),
    path('pdf/', views.GeneratePDF.as_view(), name="pdf"),



    #for superUser

    path('hostel-notices/', views.hostel_notice_board, name='hostel_notices_board'),
    # //caretaker and warden can see all leaves
    path('all_leave_data/', views.all_leave_data, name='all_leave_data'),
    # caretaker  or wardern can approve leave
    path('update_leave_status/', views.update_leave_status, name='update_leave_status'),
    # //apply for leave
    path('create_hostel_leave/', views.create_hostel_leave, name='create_hostel_leave'),
    
    # caretaker and warden can get all complaints
    path('hostel_complaints/', views.hostel_complaint_list, name='hostel_complaint_list'),
    path('hostel-complaints/', views.hostel_complaints_api, name='hostel_complaints_api'),
    path('hostel-complaints/<int:complaint_id>/status/', views.update_hostel_complaint_status, name='hostel_complaint_status_api'),

    # API endpoints (kept in hostel_management/api/urls.py)




    path('accounts/', include('django.contrib.auth.urls')),
    path('logout/', views.logout_view, name='logout_view'),
    # path('logout/', auth_views.LogoutView.as_view(), name='logout'),
  

    # !!todo: Add Fine Functionality (web page)
    path('fine/', views.impose_fine_view, name='fine_form_show'),
    path('fine/delete/<int:fine_id>/', views.delete_fine_api, name='fine_delete_api'),

]

# Keep API routes in a dedicated module but preserve existing paths.
urlpatterns += api_urlpatterns