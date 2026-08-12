import hashlib
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "policies" / "ANNOTATION_POLICY.md"


def get_policy_path() -> Path:
    override = os.getenv("CVAT_ANNOTATION_POLICY", "").strip()

    if override:
        return Path(override).expanduser().resolve()

    return DEFAULT_POLICY_PATH


def read_policy() -> str:
    path = get_policy_path()

    if not path.exists():
        raise FileNotFoundError(
            f"Annotation policy not found: {path}"
        )

    text = path.read_text(encoding="utf-8").strip()

    if not text:
        raise ValueError(
            f"Annotation policy is empty: {path}"
        )

    return text


def policy_info():
    path = get_policy_path()
    text = read_policy()

    digest = hashlib.sha256(
        text.encode("utf-8")
    ).hexdigest()

    return {
        "path": str(path),
        "sha256": digest,
        "bytes": len(text.encode("utf-8")),
    }
