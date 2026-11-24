from django.urls import path
from . import views

app_name = "documents"

urlpatterns = [
    path("", views.document_list, name="list"),
    path("upload/", views.document_upload, name="upload"),
    path("<int:pk>/edit/", views.document_edit, name="edit"),
    path("<int:pk>/delete/", views.document_delete, name="delete"),
    path("<int:pk>/download/", views.document_download, name="download"),
    path("coordinator/", views.coordinator_documents, name="coordinator_list"),
    path("coordinator/<int:pk>/review/", views.review_document, name="review"),
    path("coordinator/student/<int:student_id>/toggle-verify/", views.toggle_student_verification, name="toggle_student_verify"),
]