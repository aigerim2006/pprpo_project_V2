"""Валидаторы загружаемых документов (ТЗ: .pdf, .jpg, .png; до 10 МБ)."""
import os
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE_BYTES = getattr(settings, "MAX_DOCUMENT_SIZE_MB", 10) * 1024 * 1024


def validate_document_file(file_obj):
    if not file_obj:
        raise ValidationError(_("Выберите файл документа."))

    ext = os.path.splitext(file_obj.name or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(_("Допустимы только форматы PDF, JPG, PNG."))

    if file_obj.size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(_("Превышен максимальный размер файла (10 МБ)."))