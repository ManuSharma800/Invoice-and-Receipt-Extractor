
import json
from io import BytesIO
from typing import Any, Dict

from google.genai import types

from src.prompts import load_prompt
from src.config import get_gemini_client, GEMINI_MODEL


class ExtractionError(Exception):
    """Raised when invoice extraction fails."""
    pass


def get_mock_extraction() -> Dict[str, Any]:
    """Returns fixed sample data for offline development."""

    return {
        "document_type": "invoice",
        "document_number": "INV-2026-001",
        "document_date": "2026-11-15",
        "currency": "INR",
        "vendor": {
            "name": "ABC Traders",
            "address": "New Delhi, India",
            "contact": "9876543210",
            "tax_id": "GSTIN123456"
        },
        "items": [
            {
                "description": "Notebook",
                "quantity": 2,
                "unit_price": 100,
                "amount": 200
            },
            {
                "description": "Pen",
                "quantity": 5,
                "unit_price": 10,
                "amount": 50
            }
        ],
        "subtotal": 250,
        "discount": 0,
        "tax": 45,
        "tax_rate": 18,
        "additional_charges": 0,
        "total": 295
    }


def extract_with_mock(document: Dict[str, Any]) -> Dict[str, Any]:
    """Returns sample data without analyzing the document."""

    if not document:
        raise ExtractionError("No document was provided.")

    return {
        "success": True,
        "data": get_mock_extraction(),
        "mode": "mock",
        "message": (
            "Mock extraction result. "
            "The uploaded document was not actually analyzed."
        )
    }


def build_gemini_contents(document: Dict[str, Any], prompt: str):
    """Builds the input content sent to Gemini."""

    file_type = document.get("file_type")
    file_bytes = document.get("file_bytes")
    text = document.get("text")

    contents = [prompt]

    if file_type == "text":
        if not text or not text.strip():
            raise ExtractionError("The provided text is empty.")

        contents.append(
            "DOCUMENT CONTENT:\n" + text
        )

    elif file_type == "pdf":
        if not file_bytes:
            raise ExtractionError("PDF file data is missing.")

        contents.append(
            types.Part.from_bytes(
                data=file_bytes,
                mime_type="application/pdf"
            )
        )

    elif file_type in ["jpg", "jpeg", "png"]:
        if not file_bytes:
            raise ExtractionError("Image file data is missing.")

        mime_type = (
            "image/png" if file_type == "png"
            else "image/jpeg"
        )

        contents.append(
            types.Part.from_bytes(
                data=file_bytes,
                mime_type=mime_type
            )
        )

    else:
        raise ExtractionError(
            f"Unsupported document type: {file_type}"
        )

    return contents


def extract_with_gemini(
    document: Dict[str, Any],
    prompt_version: str = "final"
) -> Dict[str, Any]:
    """Extracts invoice information using the Gemini API."""

    if not document:
        raise ExtractionError("No document was provided.")

    try:
        prompt = load_prompt(prompt_version)

        contents = build_gemini_contents(
            document,
            prompt
        )

        client = get_gemini_client()

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0
            )
        )

        response_text = response.text

        if not response_text:
            raise ExtractionError(
                "Gemini returned an empty response."
            )

        extracted_data = json.loads(response_text)

        if not isinstance(extracted_data, dict):
            raise ExtractionError(
                "Gemini response must be a JSON object."
            )

        return {
            "success": True,
            "data": extracted_data,
            "mode": "gemini",
            "message": "Successfully extracted data using Gemini."
        }

    except ExtractionError:
        raise

    except json.JSONDecodeError as error:
        raise ExtractionError(
            f"Gemini returned invalid JSON: {error}"
        ) from error

    except Exception as error:
        raise ExtractionError(
            f"Gemini extraction failed: {error}"
        ) from error


def extract_document(
    document: Dict[str, Any],
    prompt_version: str = "final",
    mode: str = "mock"
) -> Dict[str, Any]:
    """Main extraction function."""

    if mode == "mock":
        load_prompt(prompt_version)
        return extract_with_mock(document)

    if mode == "gemini":
        return extract_with_gemini(
            document,
            prompt_version
        )

    raise ExtractionError(
        "Invalid extraction mode. Choose 'mock' or 'gemini'."
    )


def extraction_to_json(data: Dict[str, Any]) -> str:
    """Converts extracted data into formatted JSON."""

    try:
        return json.dumps(
            data,
            indent=4,
            ensure_ascii=False
        )

    except (TypeError, ValueError) as error:
        raise ExtractionError(
            f"Could not convert extraction result to JSON: {error}"
        ) from error
