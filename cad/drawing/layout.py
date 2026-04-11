"""Compute TechDraw view positions from bounding box + sheet config.

Pure geometry — no FreeCAD imports. Given a shape's bounding box
dimensions, sheet size, and layout config, returns a dict of view
definitions with positions for each projection.
"""

# ISO 216 landscape dimensions (width, height) in mm
SHEET_DIMS = {
    "A4": (297, 210),
    "A3": (420, 297),
    "A2": (594, 420),
    "A1": (841, 594),
    "A0": (1189, 841),
}

TITLE_BLOCK_H = 58  # ISO 5457


def compute_layout(
    bb_x: float,
    bb_y: float,
    bb_z: float,
    sheet_size: str,
    scale: float,
    padding: float,
    gap: float,
    has_iso: bool,
) -> tuple[dict, float]:
    """Compute view positions distributed across the usable drawing area.

    Args:
        bb_x, bb_y, bb_z: shape bounding box dimensions in mm
        sheet_size: ISO 216 sheet (A4, A3, etc.)
        scale: drawing scale factor
        padding: margin padding in mm
        gap: gap between views in mm
        has_iso: whether to include isometric view

    Returns:
        (view_defs, final_scale) where view_defs maps name to
        (direction_tuple, cx, cy) and final_scale may be reduced
        if auto-scaling was needed.
    """
    sheet_w, sheet_h = SHEET_DIMS[sheet_size]
    margin_left, margin_top = 20, 10

    usable_l = margin_left + padding
    usable_r = sheet_w - margin_left - padding
    usable_top_y = sheet_h - margin_top - padding
    usable_bot_y = margin_top + TITLE_BLOCK_H + padding
    usable_w = usable_r - usable_l
    usable_h = usable_top_y - usable_bot_y

    def _at_scale(s):
        fw, fh = bb_x * s, bb_z * s
        rw = bb_y * s
        th = bb_y * s
        iso_est = max(fw, fh) * 1.2

        ortho_w = fw + gap + rw
        ortho_h = th + gap + fh
        total_w = ortho_w + (gap + iso_est if has_iso else 0)

        if has_iso:
            left_half_w = usable_w * 0.55
            right_half_cx = usable_l + left_half_w + (usable_w - left_half_w) / 2
        else:
            left_half_w = usable_w

        ortho_cx = usable_l + left_half_w / 2
        ortho_cy = usable_bot_y + usable_h / 2

        front_cx = ortho_cx - (ortho_w / 2) + fw / 2
        front_cy = ortho_cy - gap / 2
        right_cx = front_cx + fw / 2 + gap + rw / 2
        right_cy = front_cy
        top_cx = front_cx
        top_cy = front_cy + fh / 2 + gap + th / 2

        defs = {
            "FRONT": ((0, -1, 0), front_cx, front_cy),
            "RIGHT": ((1, 0, 0), right_cx, right_cy),
            "TOP": ((0, 0, 1), top_cx, top_cy),
        }
        if has_iso:
            iso_cy = usable_bot_y + usable_h / 2
            defs["ISOMETRIC"] = ((1, -1, 1), right_half_cx, iso_cy)

        return defs, total_w, ortho_h

    # Reason: auto-scale down if views don't fit the usable area.
    view_defs, total_w, total_h = _at_scale(scale)
    if total_w > usable_w or total_h > usable_h:
        fit_scale_w = usable_w / (total_w / scale)
        fit_scale_h = usable_h / (total_h / scale)
        scale = min(fit_scale_w, fit_scale_h) * 0.95
        view_defs, _, _ = _at_scale(scale)

    return view_defs, scale
