import hashlib
import json
import math
from functools import lru_cache
from app.config import get_settings


@lru_cache()
def catalog():
    return json.loads((get_settings().MODELING_ROOT / "catalog.json").read_text())


def validate_parameters(component, parameters):
    definition = catalog()["components"].get(component)
    if definition is None:
        raise ValueError(f"Unknown component: {component}")
    expected = definition["parameters"]
    if set(parameters) != set(expected):
        raise ValueError(
            f"{component} requires exactly these parameters: {', '.join(expected) or '(none)'}"
        )
    for key, value in parameters.items():
        low, high = expected[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or not low <= value <= high
        ):
            raise ValueError(f"{component}.{key} must be between {low} and {high}")


def content_hash(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()
