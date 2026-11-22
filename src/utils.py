
from typing import Any, Dict, List
import json
import re



def flatten_dict(data, prefix=""):
    """
    Flattens nested dictionaries and lists.

    Example:
    items[0].description
    items[0].quantity
    """

    flattened = {}

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, (dict, list)):
                flattened.update(flatten_dict(value, new_key))
            else:
                flattened[new_key] = value

    elif isinstance(data, list):
        if not data:
            flattened[prefix] = []

        for index, value in enumerate(data):
            new_key = f"{prefix}[{index}]"

            if isinstance(value, (dict, list)):
                flattened.update(flatten_dict(value, new_key))
            else:
                flattened[new_key] = value

    else:
        flattened[prefix] = data

    return flattened


def normalize_value(value: Any) -> Any:
    """
    Normalizes values before comparison.
    Makes string comparisons case-insensitive and ignores
    unnecessary whitespace.
    """

    if isinstance(value, str):
        value = re.sub(r"\s+", " ", value.strip())
        return value.lower()

    return value


def compare_values(expected: Any, actual: Any) -> bool:
    """
    Compares two values after normalization.
    """

    expected = normalize_value(expected)
    actual = normalize_value(actual)

    # Avoid treating True as equal to 1.
    if isinstance(expected, bool) or isinstance(actual, bool):
        return type(expected) == type(actual) and expected == actual

    # Compare numeric values with a small tolerance.
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return abs(expected - actual) < 0.000001

    return expected == actual


def calculate_field_accuracy(
    expected: Dict[str, Any],
    actual: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculates field-level accuracy between expected and extracted data.

    Only fields present in expected data are evaluated.
    """

    expected_flat = flatten_dict(expected)
    actual_flat = flatten_dict(actual)

    total_fields = len(expected_flat)
    correct_fields = 0

    field_results = {}

    for field, expected_value in expected_flat.items():
        actual_value = actual_flat.get(field)

        is_correct = (
            field in actual_flat
            and compare_values(expected_value, actual_value)
        )

        if is_correct:
            correct_fields += 1

        field_results[field] = {
            "expected": expected_value,
            "actual": actual_value,
            "correct": is_correct
        }

    accuracy = (
        (correct_fields / total_fields) * 100
        if total_fields > 0
        else 0.0
    )

    return {
        "total_fields": total_fields,
        "correct_fields": correct_fields,
        "incorrect_fields": total_fields - correct_fields,
        "accuracy": round(accuracy, 2),
        "field_results": field_results
    }


def compare_prompt_versions(
    expected: Dict[str, Any],
    prompt_outputs: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compares the extraction accuracy of multiple prompt versions.

    Example:
    {
        "v1": extracted_data_v1,
        "v2": extracted_data_v2,
        "v3": extracted_data_v3
    }
    """

    comparison = {}

    for version, extracted_data in prompt_outputs.items():
        comparison[version] = calculate_field_accuracy(
            expected,
            extracted_data
        )

    return comparison


def get_best_prompt_version(
    comparison: Dict[str, Any]
) -> str:
    """
    Returns the prompt version with the highest accuracy.
    """

    if not comparison:
        raise ValueError("No prompt comparison results provided.")

    return max(
        comparison,
        key=lambda version: comparison[version]["accuracy"]
    )


def save_json(data: Dict[str, Any], file_path: str) -> None:
    """Saves a dictionary as a formatted JSON file."""

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def load_json(file_path: str) -> Dict[str, Any]:
    """Loads a JSON file and returns its contents."""

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)
