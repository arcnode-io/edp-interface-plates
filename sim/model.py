"""CalculiX FEM solver for L-bracket via pygccx.

Meshes CadQuery STEP geometry, fixes bolt hole surfaces, applies load
at free end, solves, and extracts bolt reaction forces and max stress.
"""

import math
import os
from pathlib import Path

import numpy as np
from pygccx import enums
from pygccx import model as ccx_model
from pygccx import model_keywords as mk
from pygccx import step_keywords as sk
from pygccx.tools import stress_tools as st

from cad.model.model import STEP_PATH
from sim.constants import (
    APPLIED_LOAD,
    BRACKET_THICKNESS,
    HOLE_DIAMETER,
    HORIZONTAL_LEG_LENGTH,
    POISSONS_RATIO,
    VERTICAL_LEG_HEIGHT,
    YOUNGS_MODULUS,
    ureg,
)

RESULTS_DIR = Path("sim/results")
MESH_SIZE = 2.0  # mm — balance between accuracy and speed
CCX_PATH = "ccx"
CGX_PATH = "cgx"


def solve() -> tuple[float, float]:
    """Run FEM and return (critical_bolt_force_N, max_von_mises_MPa)."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    wkd = str(RESULTS_DIR.resolve())

    with ccx_model.Model(
        CCX_PATH, CGX_PATH, jobname="l_bracket", working_dir=wkd
    ) as model:
        gmsh = model.get_gmsh()
        gmsh.model.occ.importShapes(os.path.abspath(STEP_PATH))
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMin", MESH_SIZE)
        gmsh.option.setNumber("Mesh.MeshSizeMax", MESH_SIZE)
        gmsh.model.mesh.generate(3)

        gmsh.model.add_physical_group(3, [1], name="BRACKET")
        _add_face_groups(gmsh)
        gmsh.model.occ.synchronize()

        model.update_mesh_from_gmsh()
        mesh = model.mesh

        # Material
        e_mpa = YOUNGS_MODULUS.magnitude.nominal_value * 1e3  # GPa -> MPa
        nu = POISSONS_RATIO.magnitude
        mat = mk.Material("STEEL")
        el = mk.Elastic((e_mpa, nu))
        sos = mk.SolidSection(
            elset=mesh.get_el_set_by_name("BRACKET"),
            material=mat,
        )

        # BCs: fix all DOFs at bolt hole surfaces
        fix_set = mesh.get_node_set_by_name("BOLT_HOLES")
        model.add_model_keywords(
            mk.Boundary(fix_set, first_dof=1, last_dof=3),
            mat,
            el,
            sos,
        )

        # Load: distributed on free end face, -Z direction
        load_set = mesh.get_node_set_by_name("LOAD")
        load_nids = list(load_set.ids)
        load_n = APPLIED_LOAD.to(ureg.N).magnitude
        load_per_node = load_n / len(load_nids)

        # Reason: cast to int() because pygccx isinstance check fails on numpy int64
        cload = sk.Cload(int(load_nids[0]), 3, -load_per_node)
        for nid in load_nids[1:]:
            cload.add_load(int(nid), 3, -load_per_node)

        step = sk.Step(nlgeom=False)
        step.add_step_keywords(
            sk.Static(),
            cload,
            sk.NodeFile([enums.ENodeFileResults.U, enums.ENodeFileResults.RF]),
            sk.ElFile([enums.EElFileResults.S]),
        )
        model.add_steps(step)

        model.solve()

        # Extract results
        frd = model.get_frd_result()
        stress_sets = frd.get_result_sets_by(entity=enums.EFrdEntities.STRESS)
        forc_sets = frd.get_result_sets_by(entity=enums.EFrdEntities.FORC)

        all_nids = list(mesh.nodes.keys())
        stress_vals = stress_sets[-1].get_values_by_ids(all_nids)
        mises = st.get_mises_stress(stress_vals)
        max_stress_mpa = float(np.max(mises))

        # Reaction forces at bolt hole nodes
        bolt_force_n = _extract_critical_bolt_force(forc_sets[-1], mesh)

    return bolt_force_n, max_stress_mpa


def _extract_critical_bolt_force(forc_set, mesh) -> float:
    """Compute per-bolt reaction resultant, return the maximum."""
    h = VERTICAL_LEG_HEIGHT.to(ureg.mm).magnitude
    z_mid = h / 2  # bolt group centroid Z

    fix_nids = list(mesh.get_node_set_by_name("BOLT_HOLES").ids)

    # Reason: split nodes into upper/lower bolt by Z-coordinate relative to centroid
    lower_nids = []
    upper_nids = []
    for nid in fix_nids:
        node_z = mesh.nodes[nid][2]
        if node_z < z_mid:
            lower_nids.append(nid)
        else:
            upper_nids.append(nid)

    # Resultant force per bolt = magnitude of summed force vector
    bolt_forces = []
    for group in [lower_nids, upper_nids]:
        vals = forc_set.get_values_by_ids(group)
        force_vec = np.sum(vals, axis=0)
        bolt_forces.append(float(np.linalg.norm(force_vec)))

    return max(bolt_forces)


def _add_face_groups(gmsh) -> None:
    """Add physical groups for bolt holes and loaded free end."""
    t = BRACKET_THICKNESS.to(ureg.mm).magnitude
    d_hole = HOLE_DIAMETER.to(ureg.mm).magnitude

    # Reason: each bolt hole cylinder may be split into halves by OCC.
    # Half-cylinder area = pi * d * t / 2. Match any cylinder in that range.
    half_hole_area = math.pi * d_hole * t / 2
    area_tol = half_hole_area * 0.3

    horiz_end_x = t + HORIZONTAL_LEG_LENGTH.to(ureg.mm).magnitude
    face_tol = 0.5

    entities = gmsh.model.occ.getEntities(2)
    bolt_hole_tags = []
    load_tags = []

    for dim, tag in entities:
        stype = gmsh.model.getType(dim, tag)
        area = gmsh.model.occ.getMass(dim, tag)

        # Bolt holes: cylinder surfaces within vertical leg (x <= t)
        if stype == "Cylinder" and abs(area - half_hole_area) < area_tol:
            bolt_hole_tags.append(tag)
            continue

        # Load face: free end of horizontal leg (max X face)
        bbox = gmsh.model.occ.getBoundingBox(dim, tag)
        xmin, _ymin, _zmin, xmax, _ymax, _zmax = bbox
        if abs(xmin - horiz_end_x) < face_tol and abs(xmax - horiz_end_x) < face_tol:
            load_tags.append(tag)

    gmsh.model.add_physical_group(2, bolt_hole_tags, name="BOLT_HOLES")
    gmsh.model.add_physical_group(2, load_tags, name="LOAD")
