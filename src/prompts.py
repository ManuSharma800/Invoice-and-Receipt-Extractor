
from pathlib import Path


# Locate the prompts directory relative to the project.
BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"


PROMPT_FILES = {
    "v1": "v1.txt",
    "v2": "v2.txt",
    "v3": "v3.txt",
    "final": "final.txt"
}


def load_prompt(version: str) -> str:
    """
    Load a selected prompt version.

    Supported versions: v1, v2, v3, final
    """

    version = version.lower().strip()

    if version not in PROMPT_FILES:
        raise ValueError(
            f"Unknown prompt version: {version}. "
            f"Available versions: {list(PROMPT_FILES)}"
        )

    prompt_path = PROMPTS_DIR / PROMPT_FILES[version]

    if not prompt_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {prompt_path}"
        )

    return prompt_path.read_text(encoding="utf-8")


def get_available_prompts() -> list:
    """Return available prompt versions."""

    return list(PROMPT_FILES.keys())
