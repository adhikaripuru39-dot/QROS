"""Builds a clean, optimized deployment zip file for transfer to the Windows VPS.

Excludes ephemeral files, virtual environments, node_modules, and cache.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import zipfile


EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".implementation-backups",
    ".phase1-backups",
    "var",
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".tmp",
    ".log",
}

EXCLUDE_FILES = {
    ".env",
    "DASHBOARD_LOGIN_PRIVATE.txt",
    "COPY_LOG.txt",
    "COPY_RETRY_LOG.txt",
    "COPY_MANIFEST.json",
    "PREPARE_COPY.py",
    "phase1-overview.png",
    "QROS-PROP-VPS-Deployment.zip",
}


def should_include(rel_path: Path) -> bool:
    parts = rel_path.parts
    for p in parts:
        if p in EXCLUDE_DIRS:
            return False
    if rel_path.suffix in EXCLUDE_EXTENSIONS:
        return False
    if rel_path.name in EXCLUDE_FILES:
        return False
    return True


def build_deployment_zip(project_root: Path, output_zip: Path):
    print(f"Scanning files in {project_root}...")
    files_to_pack = []
    total_uncompressed_bytes = 0

    for root, dirs, files in os.walk(project_root):
        rel_dir = Path(root).relative_to(project_root)
        # Skip excluded dirs early to avoid walking them
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        for f in files:
            file_path = Path(root) / f
            rel_file = file_path.relative_to(project_root)
            if should_include(rel_file):
                files_to_pack.append((file_path, rel_file))
                total_uncompressed_bytes += file_path.stat().st_size

    print(f"Found {len(files_to_pack)} files to pack ({total_uncompressed_bytes / (1024 * 1024):.2f} MB uncompressed).")
    print(f"Creating archive: {output_zip}...")
    
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
        for full_path, rel_path in files_to_pack:
            # Prefix with QROS-PROP root directory inside zip
            archive_name = Path("QROS-PROP") / rel_path
            zipf.write(full_path, arcname=str(archive_name))

    compressed_size = output_zip.stat().st_size
    print(f"Successfully created: {output_zip}")
    print(f"Compressed size: {compressed_size / (1024 * 1024):.2f} MB")
    return output_zip


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    
    # Target 1: In project root
    target1 = root / "QROS-PROP-VPS-Deployment.zip"
    build_deployment_zip(root, target1)

    # Target 2: On Desktop for direct user transfer
    desktop_dir = Path(os.path.expanduser("~")) / "Desktop"
    if desktop_dir.is_dir():
        target2 = desktop_dir / "QROS-PROP-VPS-Deployment.zip"
        shutil.copy2(target1, target2)
        print(f"Copied deployment zip directly to Desktop: {target2}")
