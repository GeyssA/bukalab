"""
Blender — style CARTE AFRIQUE (vue dessus, bords nets, soleil visible)
=====================================================================
Ce n'est PAS une vue 3D touristique.
C'est une carte poster : caméra presque au-dessus, île extrudée,
ombre portée, soleil qui rase le relief.

1. File → New → General
2. Scripting → Open → ce fichier → Run ▶
3. F12

Prérequis dans blender_export/ :
  - color_communes.png
  - dem_heightmap.png
"""

import bpy
import bmesh
from mathutils import Vector, Euler
import os

# =============================================================================
_BASE = r"C:\Users\arnau\Documents\DEV CODE\CARTOGRAPHIES & ANALYSES\CARTES\blender_export"
DEM_PATH = os.path.join(_BASE, "dem_heightmap.png")
COLOR_PATH = os.path.join(_BASE, "color_communes.png")
MASK_PATH = os.path.join(_BASE, "mask_communes.png")  # optionnel

PLANE_SIZE = 8.0
ASPECT = 2.05              # Corse plus haute que large
SUBDIV = 350
DISPLACE_STRENGTH = 0.28   # relief doux type carte
EXTRUDE_DEPTH = 0.22       # « épaisseur » de l'île = bords marqués
SUN_ENERGY = 6.0           # soleil bien visible
SUN_ANGLE = (0.55, 0.05, 0.85)  # rasant depuis NO

RES_X, RES_Y = 2000, 2400
# =============================================================================


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.textures, bpy.data.lights, bpy.data.cameras):
        for block in list(coll):
            if block.users == 0:
                coll.remove(block)


def setup_world():
    world = bpy.data.worlds.new("World_Map")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    # fond clair type poster
    bg.inputs["Color"].default_value = (0.97, 0.97, 0.96, 1)
    bg.inputs["Strength"].default_value = 0.35  # bas → le soleil domine
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def make_ground():
    """Plan blanc qui reçoit l'ombre portée (effet carte posée)."""
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -EXTRUDE_DEPTH - 0.001))
    ground = bpy.context.active_object
    ground.name = "Ground"
    mat = bpy.data.materials.new("GroundMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.97, 0.97, 0.96, 1)
    bsdf.inputs["Roughness"].default_value = 1.0
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
    mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    ground.data.materials.append(mat)
    return ground


def make_island():
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Corse_Map"
    obj.scale = (PLANE_SIZE, PLANE_SIZE * ASPECT, 1)
    bpy.ops.object.transform_apply(scale=True)

    # densifier
    bpy.ops.object.mode_set(mode="EDIT")
    bm = bmesh.from_edit_mesh(obj.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=max(1, SUBDIV // 4), use_grid_fill=True)
    bmesh.update_edit_mesh(obj.data)
    bpy.ops.uv.reset()
    bpy.ops.object.mode_set(mode="OBJECT")

    # --- Displacement MNT ---
    if not os.path.exists(DEM_PATH):
        raise FileNotFoundError(DEM_PATH)
    dem_img = bpy.data.images.load(DEM_PATH)
    dem_img.colorspace_settings.name = "Non-Color"
    dem_tex = bpy.data.textures.new("DEM", type="IMAGE")
    dem_tex.image = dem_img

    disp = obj.modifiers.new("Displace", "DISPLACE")
    disp.texture = dem_tex
    disp.texture_coords = "UV"
    disp.mid_level = 0.0
    disp.strength = DISPLACE_STRENGTH
    bpy.ops.object.modifier_apply(modifier="Displace")

    # --- Extrusion / Solidify = BORDS MARQUÉS (clé du style Afrique) ---
    solid = obj.modifiers.new("Solidify", "SOLIDIFY")
    solid.thickness = EXTRUDE_DEPTH
    solid.offset = 1.0          # extrude vers le bas
    solid.use_even_offset = True
    solid.use_quality_normals = True
    bpy.ops.object.modifier_apply(modifier="Solidify")

    # smooth dessus seulement
    bpy.ops.object.shade_smooth()
    # autosmooth-ish
    for p in obj.data.polygons:
        p.use_smooth = True

    # léger bevel sur les arêtes latérales
    bevel = obj.modifiers.new("Bevel", "BEVEL")
    bevel.width = 0.015
    bevel.segments = 2
    bevel.limit_method = "ANGLE"
    bevel.angle_limit = 0.7

    return obj


def make_material(obj):
    if not os.path.exists(COLOR_PATH):
        raise FileNotFoundError(COLOR_PATH)

    mat = bpy.data.materials.new("MapColors")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new("ShaderNodeOutputMaterial")
    out.location = (500, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    # mat carte, pas plastique
    bsdf.inputs["Roughness"].default_value = 0.75
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.15
    elif "Specular" in bsdf.inputs:
        bsdf.inputs["Specular"].default_value = 0.15

    tex = nodes.new("ShaderNodeTexImage")
    tex.location = (-300, 100)
    tex.image = bpy.data.images.load(COLOR_PATH)
    tex.interpolation = "Closest"

    # Géométrie: faces du dessus (normale Z) = couleurs ; côtés = brun foncé
    geom = nodes.new("ShaderNodeNewGeometry")
    geom.location = (-300, -150)
    sep = nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-100, -150)
    links.new(geom.outputs["Normal"], sep.inputs["Vector"])

    # si normale.z > 0.5 → top, sinon côté
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (50, -150)
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    links.new(sep.outputs["Z"], ramp.inputs["Fac"])

    side_col = nodes.new("ShaderNodeRGB")
    side_col.location = (-100, -320)
    side_col.outputs[0].default_value = (0.25, 0.18, 0.12, 1)  # bord foncé

    mix = nodes.new("ShaderNodeMixRGB")
    mix.location = (50, 50)
    mix.blend_type = "MIX"
    links.new(ramp.outputs["Color"], mix.inputs["Fac"])
    links.new(side_col.outputs["Color"], mix.inputs["Color1"])
    links.new(tex.outputs["Color"], mix.inputs["Color2"])

    links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    obj.data.materials.clear()
    obj.data.materials.append(mat)


def make_lights():
    # Soleil principal — bien visible, rasant (ombrage naturel)
    bpy.ops.object.light_add(type="SUN", location=(6, -4, 12))
    sun = bpy.context.active_object
    sun.name = "Sun_Main"
    sun.data.energy = SUN_ENERGY
    sun.data.angle = 0.02  # ombres nettes un peu soft
    sun.rotation_euler = Euler(SUN_ANGLE, "XYZ")

    # Fill très faible pour déboucher sans tuer le relief
    bpy.ops.object.light_add(type="AREA", location=(-5, 5, 8))
    fill = bpy.context.active_object
    fill.name = "Fill"
    fill.data.energy = 8
    fill.data.size = 12
    fill.data.color = (0.85, 0.9, 1.0)


def make_camera():
    """Caméra AU-DESSUS, légère inclinaison style poster Afrique."""
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    cam.name = "Cam_Map"
    # haut + un peu décalé
    cam.location = Vector((0.8, -2.2, 18.0))
    # regarde vers le centre, quasi zenith
    cam.rotation_euler = Euler((0.18, 0.0, 0.08), "XYZ")
    cam.data.type = "ORTHO"          # ← crucial pour look carte
    cam.data.ortho_scale = 18.5
    bpy.context.scene.camera = cam


def setup_render():
    scene = bpy.context.scene
    scene.render.resolution_x = RES_X
    scene.render.resolution_y = RES_Y
    scene.render.filepath = os.path.join(_BASE, "corse_style_afrique.png")

    # Cycles = meilleures ombres portées
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True

    # ombres
    scene.render.film_transparent = False
    if hasattr(scene.world, "cycles"):
        pass

    # Eevee fallback si Cycles trop lent — décommente :
    # try:
    #     scene.render.engine = "BLENDER_EEVEE_NEXT"
    # except Exception:
    #     scene.render.engine = "BLENDER_EEVEE"


def frame_island():
    # recentre vue
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.region_3d.view_perspective = "ORTHO"
                    space.shading.type = "MATERIAL"


def main():
    clear_scene()
    setup_world()
    make_ground()
    obj = make_island()
    make_material(obj)
    make_lights()
    make_camera()
    setup_render()
    frame_island()
    print("=" * 60)
    print("STYLE AFRIQUE pret")
    print("  - camera ORTHO vue dessus")
    print("  - bords extrudes (Solidify)")
    print("  - soleil rasant")
    print("  - ombre portee sur fond blanc")
    print("  F12 pour rendu →", os.path.join(_BASE, "corse_style_afrique.png"))
    print("Si relief faible: DISPLACE_STRENGTH=0.4")
    print("Si bords trop bas: EXTRUDE_DEPTH=0.35")
    print("Si soleil faible: SUN_ENERGY=8")
    print("=" * 60)


if __name__ == "__main__":
    main()
