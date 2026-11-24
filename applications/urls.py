from django.urls import path
from . import views

app_name = "applications"

urlpatterns = [
    path("", views.application_list, name="list"),
    path("apply/<int:vacancy_id>/", views.apply_to_vacancy, name="apply"),
    path("<int:pk>/", views.application_detail, name="detail"),
    path("<int:pk>/decide/", views.employer_decide, name="decide"),
    path("<int:pk>/offer-response/", views.respond_job_offer, name="offer_response"),
    path("<int:pk>/withdraw/", views.withdraw_application, name="withdraw"),
    path("<int:pk>/offer-file/", views.download_job_offer, name="offer_file"),
    path("visa/<int:pk>/permit-file/", views.download_work_permit, name="permit_file"),
    path("coordinator/visas/", views.coordinator_visas, name="coordinator_visas"),
    path("coordinator/visas/<int:pk>/update/", views.update_visa_stage, name="update_visa"),
]