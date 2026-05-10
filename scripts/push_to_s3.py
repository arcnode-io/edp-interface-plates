"""Push plate artifacts to S3 for downstream consumers.

Uploads each plate's spec.yaml + plate{,-defense}.step + plate{,-defense}.dxf +
drawing_meta{,-defense}.json to s3://{bucket}/plates/{plate_id}/v1/.

Consumed by edp-module-assemblies (`plate_loader.fetch`) which downloads
plate STEP files for compute_container / grid_container assembly tests.

Backend: real AWS S3 by default; localstack via `S3_ENDPOINT_URL` env var.

Usage:
    uv run poe push-s3                                           # real bucket
    S3_ENDPOINT_URL=http://localhost:4566 uv run poe push-s3     # localstack
"""

import logging
import os
from pathlib import Path
from typing import Final

import boto3
from botocore.client import BaseClient

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
SPECS_DIR: Final[Path] = REPO_ROOT / "cad" / "specs"

S3_BUCKET: Final[str] = os.environ.get("ARCNODE_ARTIFACTS_BUCKET", "arcnode-artifacts")
S3_ENDPOINT_URL: Final[str | None] = os.environ.get("S3_ENDPOINT_URL")
PLATE_VERSION: Final[str] = "v1"

PLATE_IDS: Final[tuple[str, ...]] = ("CG", "BG-AC", "BG-DC", "CD")

# Per-plate filenames to upload. Defense variants share artifacts with
# sovereign_government per plate spec; plate_loader.py keys both contexts to
# the same -defense suffix.
ARTIFACT_FILENAMES: Final[tuple[str, ...]] = (
    "spec.yaml",
    "plate.step",
    "plate-defense.step",
    "plate.dxf",
    "plate-defense.dxf",
    "drawing_meta.json",
    "drawing_meta-defense.json",
)


def _s3_client() -> BaseClient:
    """Create S3 client honoring optional localstack endpoint override."""
    if S3_ENDPOINT_URL:
        return boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id="test",
            aws_secret_access_key="test",
            region_name="us-east-1",
        )
    return boto3.client("s3")


def _upload(s3: BaseClient, local_path: Path, key: str) -> None:
    """Upload one file; warn + skip if missing."""
    if not local_path.exists():
        logger.warning(f"  ⊘ skip (missing): {local_path.relative_to(REPO_ROOT)}")
        return
    s3.upload_file(str(local_path), S3_BUCKET, key)
    logger.info(f"  → s3://{S3_BUCKET}/{key}")


def push() -> None:
    """Upload all plate artifacts to S3."""
    s3 = _s3_client()
    for plate_id in PLATE_IDS:
        logger.info(f"plate {plate_id}:")
        for filename in ARTIFACT_FILENAMES:
            local = SPECS_DIR / plate_id / filename
            key = f"plates/{plate_id}/{PLATE_VERSION}/{filename}"
            _upload(s3, local, key)


def main() -> None:
    """CLI entry: push plate artifacts to S3."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    push()


if __name__ == "__main__":
    main()
