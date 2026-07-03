"""Plane instance configuration — Python equivalent of plane-adapter.ts."""
import os

PLANE_URL = os.getenv("PLANE_URL", "http://localhost:3000")
EMAIL = os.getenv("PLANE_EMAIL", "admin@admin.com")
PASSWORD = os.getenv("PLANE_PASSWORD", "qweQWE123!@#")
WORKSPACE = os.getenv("PLANE_WORKSPACE", "plane-dev")
PROJECT = os.getenv("PLANE_PROJECT", "SEED")
API_BASE = f"{PLANE_URL}/api/v1"

# Computed URLs
LOGIN_URL = PLANE_URL
WORKSPACE_URL = f"{PLANE_URL}/{WORKSPACE}"


def issues_path(project_id: str = "") -> str:
    """URL path to project issues."""
    if project_id:
        return f"{WORKSPACE_URL}/projects/{project_id}/issues"
    return f"{WORKSPACE_URL}/projects"


def stickies_path() -> str:
    """URL path to stickies."""
    return f"{WORKSPACE_URL}/stickies"


# Seed data inventory (from seeded Plane instance)
SEED_DATA = {
    "issues": 30,
    "states": 5,
    "cycles": 3,
    "modules": 4,
    "pages": 5,
    "sub_issues": 5,
    "stickies": 0,
}
