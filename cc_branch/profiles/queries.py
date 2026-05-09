"""Profile catalog queries."""

from __future__ import annotations

from .definitions import PROFILES


def get_available_profiles() -> list[str]:
    """Return available profile names."""
    return list(PROFILES.keys())


def get_profile_description(profile: str) -> str:
    """Return a profile description."""
    if profile not in PROFILES:
        raise ValueError(f"Unknown profile: {profile}")
    return PROFILES[profile]["description"]
