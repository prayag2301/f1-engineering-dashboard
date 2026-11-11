import hashlib
import importlib.util
import json
import math
from functools import lru_cache
from app.config import get_settings


@lru_cache()
def catalog():
    root = get_settings().MODELING_ROOT
    data = json.loads((root / "catalog.json").read_text())
    if data.get("wing_profile_schema_version") == 1:
        spec = importlib.util.spec_from_file_location(
            "wing_profiles", root / "wing_profiles.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.validate_wing_profiles(data["teams"])
    return data


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
