"""Export drawing views via CadQuery SVG export.

Reads view definitions from layout_spec.yaml.
"""

from pathlib import Path

import yaml
from cadquery import exporters

from cad.model.model import build_bracket

LAYOUT_SPEC_PATH = Path("cad/layout_spec.yaml")
DRAWINGS_DIR = Path("output/drawings")


def _load_spec() -> dict:
    return yaml.safe_load(LAYOUT_SPEC_PATH.read_text())


def export_views(single_views: bool = False) -> list[Path]:
    """Export bracket projections as SVG files.

    Args:
        single_views: if True, export individual front/side/iso SVGs.
            Default False — only used for debugging or web assets.
    """
    if not single_views:
        print("Skipping single-view SVGs (pass --single-views to enable)")
        return []

    spec = _load_spec()
    DRAWINGS_DIR.mkdir(parents=True, exist_ok=True)
    bracket = build_bracket()

    exported: list[Path] = []
    for name, view in spec["views"].items():
        svg_path = DRAWINGS_DIR / f"l_bracket_{name}.svg"
        exporters.export(
            bracket,
            str(svg_path),
            opt={
                "width": view.get("width", 400),
                "height": view.get("height", 400),
                "marginLeft": 20,
                "marginTop": 20,
                "showHidden": True,
                "projectionDir": tuple(view["projection_dir"]),
            },
        )
        exported.append(svg_path)
        print(f"Exported {svg_path}")

    return exported


if __name__ == "__main__":
    import sys

    single = "--single-views" in sys.argv
    paths = export_views(single_views=single)
    print(f"Generated {len(paths)} drawing views")
