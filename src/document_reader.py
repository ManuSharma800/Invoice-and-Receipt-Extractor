
from io import BytesIO
from typing import Any, Dict

from pypdf import PdfReader
from PIL import Image, UnidentifiedImageError


class DocumentProcessingError(Exception):
    """Raised when a document cannot be processed."""
    pass


SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png"
}


def get_file_extension(filename: str) -> str:
    """Return the lowercase file extension."""

    if not filename or "." not in filename:
        raise DocumentProcessingError(
            "Invalid filename or missing file extension."
        )

    return "." + filename.rsplit(".", 1)[-1].lower()


def validate_file(filename: str, file_bytes: bytes) -> str:
    """Validate filename, format and file content."""

    if not filename:
        raise DocumentProcessingError(
            "Filename cannot be empty."
        )

    if not file_bytes:
        raise DocumentProcessingError(
            "The uploaded document is empty."
        )

    extension = get_file_extension(filename)

    if extension not in SUPPORTED_EXTENSIONS:
        raise DocumentProcessingError(
            f"Unsupported file format: {extension}. "
            "Supported formats: PDF, JPG, JPEG and PNG."
        )

    return extension


def extract_pdf_text(file_bytes: bytes) -> Dict[str, Any]:
    """Extract selectable text from a PDF document."""

    try:
        pdf_file = BytesIO(file_bytes)
        reader = PdfReader(pdf_file)

        if reader.is_encrypted:
            raise DocumentProcessingError(
                "Password-protected PDFs are not supported."
            )

        page_count = len(reader.pages)

        if page_count == 0:
            raise DocumentProcessingError(
                "The PDF contains no pages."
            )

        extracted_pages = []

        for page_number, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""

            extracted_pages.append(
                f"--- Page {page_number} ---\n{page_text}"
            )

        full_text = "\n\n".join(extracted_pages).strip()

        warnings = []

        if not full_text:
            warnings.append(
                "No selectable text found. "
                "This may be a scanned PDF requiring OCR "
                "or multimodal AI processing."
            )

        return {
            "text": full_text,
            "page_count": page_count,
            "warnings": warnings
        }

    except DocumentProcessingError:
        raise

    except Exception as error:
        raise DocumentProcessingError(
            f"Unable to read PDF: {error}"
        ) from error


def load_image(file_bytes: bytes) -> Image.Image:
    """Validate and load a JPG or PNG image."""

    try:
        image_data = BytesIO(file_bytes)

        # Verify that the image is not corrupted.
        with Image.open(image_data) as img:
            img.verify()

        # Reopen after verification to load actual image data.
        image_data.seek(0)

        with Image.open(image_data) as img:
            img.load()
            return img.convert("RGB")

    except (
        UnidentifiedImageError,
        OSError,
        ValueError
    ) as error:
        raise DocumentProcessingError(
            f"Unable to read image. "
            f"The file may be corrupted or invalid: {error}"
        ) from error


def process_document(
    filename: str,
    file_bytes: bytes
) -> Dict[str, Any]:
    """
    Process an uploaded PDF or image.

    Returns a consistent dictionary containing:
    filename, file_type, text, image, page_count and warnings.
    """

    extension = validate_file(filename, file_bytes)

    if extension == ".pdf":

        result = extract_pdf_text(file_bytes)

        return {
            "filename": filename,
            "file_type": "pdf",
            "text": result["text"],
            "image": None,
            "file_bytes": file_bytes,
            "page_count": result["page_count"],
            "warnings": result["warnings"]
        }

    image = load_image(file_bytes)

    return {
        "filename": filename,
        "file_type": extension[1:],
        "text": None,
        "image": image,
        "file_bytes": file_bytes,
        "page_count": None,
        "warnings": []
    }


def process_pasted_text(text: str) -> Dict[str, Any]:
    """Validate and process manually pasted invoice text."""

    if not isinstance(text, str) or not text.strip():
        raise DocumentProcessingError(
            "Pasted invoice text cannot be empty."
        )

    return {
        "filename": "pasted_invoice_text",
        "file_type": "text",
        "text": text.strip(),
        "image": None,
        "file_bytes": None,
        "page_count": None,
        "warnings": []
    }
