from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("forgot-password-code/", views.forgot_password_code, name="forgot_password_code"),
    path("force-password-change/", views.force_password_change, name="force_password_change"),
    
    # Student URLs
    path("student/", views.student_dashboard, name="student_dashboard"),
    path("student/surveys/", views.student_assigned_surveys, name="student_assigned_surveys"),
    path("student/responses/", views.student_response_history, name="student_response_history"),
    path("student/response/<int:response_id>/details/", views.student_view_response_details, name="student_view_response_details"),
    path("student/survey/<int:survey_id>/save-progress/", views.save_survey_progress, name="save_survey_progress"),
    path("student/survey/<int:survey_id>/", views.take_survey, name="take_survey"),
    
    # Teacher URLs
    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path("teacher/surveys/", views.manage_surveys, name="manage_surveys"),
    path("teacher/surveys/archived/", views.archived_surveys, name="archived_surveys"),
    path("teacher/responses/", views.responses_overview, name="responses_overview"),
    path("teacher/survey-builder/", views.survey_builder, name="survey_builder"),
    path("teacher/survey/<int:survey_id>/edit/", views.edit_survey, name="edit_survey"),
    path("teacher/survey/<int:survey_id>/publish/", views.publish_survey, name="publish_survey"),
    path("teacher/survey/<int:survey_id>/unpublish/", views.unpublish_survey, name="unpublish_survey"),
    path("teacher/survey/<int:survey_id>/archive/", views.archive_survey, name="archive_survey"),
    path("teacher/survey/<int:survey_id>/restore/", views.restore_survey, name="restore_survey"),
    path("teacher/survey/<int:survey_id>/responses/", views.response_management, name="response_management"),
    path("teacher/survey/<int:survey_id>/analytics/", views.analytics, name="analytics"),
    path("teacher/response/<int:response_id>/details/", views.view_response_details, name="view_response_details"),
    path("teacher/question/<int:question_id>/edit/", views.edit_question, name="edit_question"),
    path("teacher/question/<int:question_id>/delete/", views.delete_question, name="delete_question"),
    path("teacher/survey/<int:survey_id>/reorder-questions/", views.reorder_questions, name="reorder_questions"),
    path("teacher/survey/<int:survey_id>/delete/", views.delete_survey, name="delete_survey"),
    path("teacher/sections/", views.manage_sections, name="manage_sections"),
    path("teacher/sections/create/", views.create_section, name="create_section"),
    path("teacher/sections/<int:section_id>/edit/", views.edit_section, name="edit_section"),
    path("teacher/sections/<int:section_id>/delete/", views.delete_section, name="delete_section"),
    path("teacher/students/", views.manage_students, name="manage_students"),
    path("teacher/students/<int:student_id>/edit/", views.edit_student, name="edit_student"),
    path("teacher/students/<int:student_id>/toggle-access/", views.toggle_student_access, name="toggle_student_access"),
    path("teacher/sections/<int:section_id>/students/", views.section_students, name="section_students"),
    path("teacher/settings/", views.teacher_settings, name="teacher_settings"),
    path("teacher/settings/due-dates/", views.set_due_dates, name="set_due_dates"),
    path("teacher/settings/due-dates/<int:survey_id>/update/", views.update_survey_due_date, name="update_survey_due_date"),
]