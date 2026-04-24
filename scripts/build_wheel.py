from __future__ import annotations

import base64
import csv
import hashlib
import io
import sys
import tomllib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def main() -> int:
    project = load_project()
    name = project["name"]
    version = project["version"]
    normalized = name.replace("-", "_")
    dist_info = f"{normalized}-{version}.dist-info"
    wheel_name = f"{normalized}-{version}-py3-none-any.whl"
    wheel_path = DIST / wheel_name

    DIST.mkdir(exist_ok=True)
    if wheel_path.exists():
        wheel_path.unlink()

    records: list[tuple[str, str, str]] = []
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as wheel:
        for path in package_files():
            archive_name = path.relative_to(ROOT).as_posix()
            write_file(wheel, path, archive_name, records)

        metadata = render_metadata(project)
        write_bytes(wheel, metadata.encode("utf-8"), f"{dist_info}/METADATA", records)
        write_bytes(wheel, render_wheel().encode("utf-8"), f"{dist_info}/WHEEL", records)
        write_bytes(wheel, render_entry_points().encode("utf-8"), f"{dist_info}/entry_points.txt", records)
        write_record(wheel, dist_info, records)

    print(wheel_path)
    return 0


def load_project() -> dict[str, object]:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return pyproject["project"]


def package_files() -> list[Path]:
    files = sorted((ROOT / "acdl").glob("*.py"))
    return [path for path in files if path.is_file()]


def write_file(
    wheel: zipfile.ZipFile,
    path: Path,
    archive_name: str,
    records: list[tuple[str, str, str]],
) -> None:
    write_bytes(wheel, path.read_bytes(), archive_name, records)


def write_bytes(
    wheel: zipfile.ZipFile,
    payload: bytes,
    archive_name: str,
    records: list[tuple[str, str, str]],
) -> None:
    wheel.writestr(archive_name, payload)
    digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode("ascii")
    records.append((archive_name, f"sha256={digest}", str(len(payload))))


def write_record(
    wheel: zipfile.ZipFile,
    dist_info: str,
    records: list[tuple[str, str, str]],
) -> None:
    record_name = f"{dist_info}/RECORD"
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    for row in records:
        writer.writerow(row)
    writer.writerow((record_name, "", ""))
    wheel.writestr(record_name, output.getvalue().encode("utf-8"))


def render_metadata(project: dict[str, object]) -> str:
    lines = [
        "Metadata-Version: 2.1",
        f"Name: {project['name']}",
        f"Version: {project['version']}",
        f"Summary: {project.get('description', '')}",
        f"Requires-Python: {project.get('requires-python', '')}",
        f"License: {project.get('license', '')}",
    ]
    for author in project.get("authors", []):
        if isinstance(author, dict) and author.get("name"):
            lines.append(f"Author: {author['name']}")
    for classifier in project.get("classifiers", []):
        lines.append(f"Classifier: {classifier}")
    for keyword in project.get("keywords", []):
        lines.append(f"Keywords: {keyword}")
    lines.append("")
    readme = ROOT / "README.md"
    if readme.exists():
        lines.append(readme.read_text(encoding="utf-8"))
    return "\n".join(lines) + "\n"


def render_wheel() -> str:
    return "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: acdl-build-wheel",
            "Root-Is-Purelib: true",
            "Tag: py3-none-any",
            "",
        ]
    )


def render_entry_points() -> str:
    return "\n".join(
        [
            "[console_scripts]",
            "acdl = acdl.cli:main",
            "",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
