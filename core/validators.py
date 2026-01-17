"""
Image upload validators for file type, size, and dimensions.
"""
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from PIL import Image

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


def validate_image_file(value):
    """Validate that the uploaded file has an allowed image extension."""
    if not value:
        return
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(
            f'Unsupported file type "{ext}". Allowed: {", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))}'
        )


def validate_image_size(value):
    """Validate that the uploaded file does not exceed the maximum size."""
    if not value:
        return
    max_size_mb = getattr(settings, 'MAX_UPLOAD_SIZE_MB', 5)
    max_size_bytes = max_size_mb * 1024 * 1024
    if value.size > max_size_bytes:
        raise ValidationError(
            f'File too large. Maximum size: {max_size_mb}MB. '
            f'Uploaded file: {value.size / (1024 * 1024):.1f}MB'
        )


def validate_image_dimensions(value):
    """Validate that the uploaded image does not exceed maximum dimensions."""
    if not value:
        return
    max_dim = getattr(settings, 'MAX_IMAGE_DIMENSION', 4096)
    try:
        img = Image.open(value)
        width, height = img.size
        if width > max_dim or height > max_dim:
            raise ValidationError(
                f'Image dimensions too large. Maximum: {max_dim}x{max_dim}px. '
                f'Uploaded image: {width}x{height}px'
            )
    except (IOError, OSError) as exc:
        raise ValidationError(f'Invalid image file: {exc}') from exc
    finally:
        # Reset file pointer for subsequent processing
        if hasattr(value, 'seek'):
            value.seek(0)


# Composite validator for convenience
def validate_image(value):
    """Run all image validators."""
    validate_image_file(value)
    validate_image_size(value)
    validate_image_dimensions(value)
