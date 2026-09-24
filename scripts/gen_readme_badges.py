#!/usr/bin/env python3
"""Generate README badge block from project version and dependency info.

Reads:
  - apps/backend/pyproject.toml  → project.version, requires-python, fastapi minimum version
  - apps/frontend/package.json   → astro, react, typescript, tailwindcss versions

Regenerates the badge block between <!-- badges:start --> and <!-- badges:end -->
in README.md with version numbers derived from those files. The script is
idempotent: running it twice produces no changes if versions haven't changed.
"""

import json
import os
import re
import sys

try:
    import tomllib
except ImportError:  # pragma: no cover - Python < 3.11 fallback
    import tomli as tomllib  # type: ignore[no-redef]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README_PATH = os.path.join(BASE_DIR, "README.md")
BACKEND_PYPROJECT = os.path.join(BASE_DIR, "apps", "backend", "pyproject.toml")
FRONTEND_PACKAGE_JSON = os.path.join(BASE_DIR, "apps", "frontend", "package.json")


def parse_backend_versions():
    """Read pyproject.toml and extract version, requires-python, and fastapi min version."""
    with open(BACKEND_PYPROJECT, "rb") as f:
        data = tomllib.load(f)

    project = data["project"]
    version = project["version"]
    requires_python = project["requires-python"]

    fastapi_min = None
    for dep in project.get("dependencies", []):
        if dep.startswith("fastapi"):
            m = re.match(r"fastapi[>=<]+(\d+\.\d+(?:\.\d+)?)", dep)
            if m:
                fastapi_min = m.group(1)
            break

    return version, requires_python, fastapi_min


def strip_prefix(ver):
    return re.sub(r"^[~^]+", "", ver)


def major(ver):
    m = re.match(r"^(\d+)", ver)
    return m.group(1) if m else ver


def major_minor(ver):
    m = re.match(r"^(\d+)\.(\d+)", ver)
    return f"{m.group(1)}.{m.group(2)}" if m else ver


def parse_frontend_versions():
    """Read package.json and extract framework versions with prefix stripping."""
    with open(FRONTEND_PACKAGE_JSON, "r") as f:
        data = json.load(f)

    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}

    astro = major(strip_prefix(deps.get("astro", "0.0.0")))
    react = major(strip_prefix(deps.get("react", "0.0.0")))
    typescript = major_minor(strip_prefix(deps.get("typescript", "0.0.0")))
    tailwindcss = major_minor(strip_prefix(deps.get("tailwindcss", "0.0.0")))

    return astro, react, typescript, tailwindcss


def badge_url(label, version, color, logo=None):
    """Build a shields.io badge URL.

    Version strings are expected to already have shield escaping (-- for -).
    Only encode + as %2B if present.
    """
    ver = version.replace("+", "%2B")
    if logo:
        url = f"https://img.shields.io/badge/{label}-{ver}-{color}?logo={logo}&logoColor=white"
    else:
        url = f"https://img.shields.io/badge/{label}-{ver}-{color}"
    return f'<img alt="{label}" src="{url}" />'


def build_badge_block(app_version, requires_python, fastapi_min,
                      astro_ver, react_ver, ts_ver, tailwind_ver):
    """Build the badge block content between the markers.

    Returns the content BETWEEN <!-- badges:start --> and <!-- badges:end -->,
    not including the markers themselves.
    """
    # Version badge: v<version>--rc while major is 0 (pre-stable), plain v<version> otherwise
    major_ver = int(app_version.split(".")[0])
    if major_ver == 0:
        version_display = f"v{app_version}--rc"
    else:
        version_display = f"v{app_version}"

    # Gentle-AI block (always first, centered)
    gentle_block = "<p align=\"center\">\n  <a href=\"https://github.com/Gentleman-Programming/gentle-ai\">\n    <img width=\"220\" src=\"https://raw.githubusercontent.com/Gentleman-Programming/gentle-ai/main/docs/assets/brand/built-with-gentle-ai.png\" alt=\"Built with Gentle-AI\" />\n  </a>\n</p>"

    # Shields row badges (same order as current README)
    badges = [
        badge_url("version", version_display, "orange"),
        badge_url("python", requires_python.lstrip(">="), "3776AB", "python"),
        badge_url("fastapi", fastapi_min or "0.110", "009688", "fastapi"),
        badge_url("postgresql", "16", "4169E1", "postgresql"),
        badge_url("astro", astro_ver, "BC52EE", "astro"),
        badge_url("react", react_ver, "61DAFB", "react"),
        badge_url("typescript", ts_ver, "3178C6", "typescript"),
        badge_url("tailwindcss", tailwind_ver, "06B6D4", "tailwindcss"),
        badge_url("docker_compose", "ready", "2496ED", "docker"),
    ]

    shields_row = "<p align=\"center\">" + "  ".join(badges) + "</p>"

    # Return content between markers (not including the markers themselves).
    # The caller is responsible for placing this between the markers.
    return f"{gentle_block}\n\n{shields_row}\n"


def main():
    # ---- Parse sources ----
    app_version, requires_python, fastapi_min = parse_backend_versions()
    astro_ver, react_ver, ts_ver, tailwind_ver = parse_frontend_versions()

    # ---- Build new content between markers ----
    new_between = build_badge_block(
        app_version, requires_python, fastapi_min,
        astro_ver, react_ver, ts_ver, tailwind_ver,
    )

    # ---- Locate and optionally replace badge block in README ----
    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()

    start_marker = "<!-- badges:start -->"
    end_marker = "<!-- badges:end -->"

    start_idx = readme.find(start_marker)
    end_idx = readme.find(end_marker)

    if start_idx == -1 or end_idx == -1:
        print(
            "Error: badges markers not found in README.md",
            file=sys.stderr,
        )
        sys.exit(1)

    # Extract the current content between markers (for comparison)
    current_between = readme[start_idx + len(start_marker):end_idx]

    # If the current content already matches the new content, no changes needed
    if current_between == new_between:
        print("README badge block is already up to date.")
        return

    # Replace: keep content before start marker, keep start marker,
    # replace content between markers with new content, keep end marker,
    # keep content after end marker.
    new_readme = (
        readme[:start_idx]  # content before start marker (does not include marker)
        + start_marker  # start marker, kept as-is
        + new_between  # new content between markers (replaces old content between markers)
        + end_marker  # end marker, kept as-is
        + readme[end_idx + len(end_marker):]  # content after end marker (does not include marker)
    )

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_readme)

    print("README badge block regenerated successfully.")


if __name__ == "__main__":
    main()