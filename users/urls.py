from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/student/", views.register_student, name="register_student"),
    path("register/employer/", views.register_employer, name="register_employer"),
    path("cabinet/", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("coordinator/users/", views.coordinator_users, name="coordinator_users"),
    path(
        "coordinator/users/<int:pk>/toggle-active/",
        views.user_toggle_active,
        name="user_toggle_active",
    ),
    path(
        "coordinator/employers/<int:pk>/verify/",
        views.employer_verify,
        name="employer_verify",
    ),
]
