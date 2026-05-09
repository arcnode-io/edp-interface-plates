"""Single dispatcher for all interface plates.

Replaces per-plate wrapper modules (cg.py, bg_ac.py, ex_g.py, ex_c.py, cd.py).
Each spec.yaml carries a `default_params:` block; the dispatcher loads that
spec, builds the plate, and exports STEP. Collapsed per Q-collapse decision:
all plates use identical build logic, so per-plate wrappers were overhead.

Usage:
    python cad/model/build.py --plate-id CG
    python cad/model/build.py --all
"""

import argparse
import logging
from dataclasses import replace
from pathlib import Path
from typing import Final

import cadquery as cq

from cad.model._plate import (
    PlateBuildParams,
    PlateSpec,
    build_plate,
    default_params_for,
    load_spec,
)

logger = logging.getLogger(__name__)

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
SPECS_DIR: Final[Path] = REPO_ROOT / "cad" / "specs"

# Reason: enumerate the v1 plate fleet here as the single source of truth;
# the dispatcher iterates this list for `--all`.
PLATE_IDS: Final[tuple[str, ...]] = ("CG", "BG-AC", "BG-DC", "CD")


def spec_path_for(plate_id: str) -> Path:
    """Return cad/specs/{plate_id}/spec.yaml."""
    return SPECS_DIR / plate_id / "spec.yaml"


def step_path_for(plate_id: str, deployment_context: str = "commercial") -> Path:
    """Return cad/specs/{plate_id}/plate{-defense}.step.

    Commercial → plate.step (unchanged).
    defense_forward / sovereign_government → plate-defense.step (suffix used
    for both DoD contexts; spec.yaml deployment_contexts table currently has
    them identical, so the artifact is shared).
    """
    suffix = "" if deployment_context == "commercial" else "-defense"
    return SPECS_DIR / plate_id / f"plate{suffix}.step"


def load_plate_spec(plate_id: str) -> PlateSpec:
    """Load the spec.yaml for a given plate_id."""
    return load_spec(spec_path_for(plate_id))


def build_for(
    plate_id: str,
    params: PlateBuildParams | None = None,
    spec: PlateSpec | None = None,
) -> cq.Workplane:
    """Build a plate workplane.

    Args:
        plate_id: Plate variant code (e.g. "CG", "CD").
        params: Optional override; defaults to spec's default_params block.
        spec: Optional pre-loaded spec to avoid re-reading the YAML.

    Returns:
        CadQuery workplane with plate solid.
    """
    if spec is None:
        spec = load_plate_spec(plate_id)
    if params is None:
        params = default_params_for(spec)
    return build_plate(params, spec)


def export_step(
    plate: cq.Workplane, plate_id: str, deployment_context: str = "commercial"
) -> Path:
    """Export plate STEP keyed by deployment context."""
    out = step_path_for(plate_id, deployment_context)
    cq.exporters.export(plate, str(out))
    return out


def main() -> None:
    """CLI entry: build one or all plates, export STEP."""
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plate-id", choices=PLATE_IDS, help="One plate to build")
    group.add_argument(
        "--all", action="store_true", help="Build every plate in PLATE_IDS"
    )
    parser.add_argument(
        "--deployment-context",
        choices=("commercial", "defense_forward", "sovereign_government"),
        default=None,
        help="Override default_params.deployment_context",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    targets = PLATE_IDS if args.all else (args.plate_id,)
    context = args.deployment_context or "commercial"
    for pid in targets:
        spec = load_plate_spec(pid)
        params = default_params_for(spec)
        if args.deployment_context is not None:
            params = replace(params, deployment_context=args.deployment_context)
        plate = build_for(pid, params=params, spec=spec)
        out = export_step(plate, pid, deployment_context=context)
        logger.info(f"  → {pid} ({context}): {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
