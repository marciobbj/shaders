import bpy
import math
from mathutils import Vector

# Limpar cena
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.scene.frame_end = 500

# Limpar handlers existentes para evitar acumulação
bpy.app.handlers.frame_change_pre.clear()

# Dados dos planetas
planets = [
    {"name": "Mercury", "radius": 0.8, "distance": 20, "period": 88, "color": (0.7, 0.7, 0.7)},
    {"name": "Venus", "radius": 1.9, "distance": 30, "period": 225, "color": (0.9, 0.8, 0.5)},
    {"name": "Earth", "radius": 2.0, "distance": 40, "period": 365, "color": (0.2, 0.5, 0.8)},
    {"name": "Mars", "radius": 1.5, "distance": 50, "period": 687, "color": (0.8, 0.3, 0.2)},
    {"name": "Jupiter", "radius": 7.0, "distance": 70, "period": 4333, "color": (0.8, 0.6, 0.4)},
    {"name": "Saturn", "radius": 6.0, "distance": 90, "period": 10759, "color": (0.9, 0.8, 0.6)},
    {"name": "Uranus", "radius": 4.0, "distance": 110, "period": 30687, "color": (0.5, 0.7, 0.8)},
    {"name": "Neptune", "radius": 3.8, "distance": 130, "period": 60190, "color": (0.3, 0.4, 0.8)},
]

# Função segura para criar material
def create_material_safe(name, color, emission=0, strength=1):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = emission
    bsdf.inputs["Emission Color"].default_value = (*color, 1)

    output = nodes.new(type='ShaderNodeOutputMaterial')
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    return mat

# Criar Sol com movimento no eixo Z
bpy.ops.mesh.primitive_uv_sphere_add(radius=10, location=(0, 0, 0))
sun = bpy.context.active_object
sun.name = "Sun"
sun.data.materials.append(create_material_safe("Sun_Mat", (1, 0.8, 0), emission=5))

# Animação do Sol subindo e descendo
sun.location.z = 0
sun.keyframe_insert("location", frame=1)
sun.location.z = 500
sun.keyframe_insert("location", frame=500)

# Lista para updaters
updaters = []

# Criar planetas e trilhas como filhos do Sol
for p in planets:
    # Empty para órbita (filho do Sol)
    orbit = bpy.data.objects.new(f"{p['name']}_Orbit", None)
    bpy.context.collection.objects.link(orbit)
    orbit.parent = sun

    # Planeta
    bpy.ops.mesh.primitive_uv_sphere_add(radius=p['radius'], location=(p['distance'], 0, 0))
    planet = bpy.context.active_object
    planet.name = p['name']
    planet.parent = orbit
    planet.data.materials.append(create_material_safe(f"{p['name']}_Mat", p['color']))

    # Rotação 100× mais rápida
    orbit.rotation_euler = (0, 0, 0)
    orbit.keyframe_insert("rotation_euler", frame=1)
    orbit.rotation_euler[2] = math.radians(360 * (500 / p['period']) * 100)
    orbit.keyframe_insert("rotation_euler", frame=500)

    for fcurve in orbit.animation_data.action.fcurves:
        for key in fcurve.keyframe_points:
            key.interpolation = 'LINEAR'

    # Posição inicial do planeta
    initial_pos = planet.matrix_world.translation

    # Trilha com curva (não parentada, para deixar rastro no espaço mundial)
    curve_data = bpy.data.curves.new(f"{p['name']}_Trail", type='CURVE')
    curve_data.dimensions = '3D'
    curve_data.bevel_depth = 0.2  # espessura visível
    curve_data.bevel_resolution = 4
    curve_data.fill_mode = 'FULL'
    spline = curve_data.splines.new('POLY')
    spline.points.add(499)  # Total 500 points
    for pt in spline.points:
        pt.co = (*initial_pos, 1)
        pt.radius = 0

    trail_obj = bpy.data.objects.new(f"{p['name']}_Trail", curve_data)
    bpy.context.collection.objects.link(trail_obj)
    # Não parentar ao sol, para o rastro ficar fixo no espaço
    trail_obj.location = (0, 0, 0)

    # Material da trilha com efeito de luz neon
    trail_mat = bpy.data.materials.new(f"{p['name']}_Trail_Mat")
    trail_mat.use_nodes = True
    nodes = trail_mat.node_tree.nodes
    links = trail_mat.node_tree.links
    nodes.clear()

    emission = nodes.new(type='ShaderNodeEmission')
    emission.inputs["Color"].default_value = (*p['color'], 1)
    emission.inputs["Strength"].default_value = 5.0  # luz intensa

    output = nodes.new(type='ShaderNodeOutputMaterial')
    links.new(emission.outputs["Emission"], output.inputs["Surface"])
    trail_obj.data.materials.append(trail_mat)

    # Atualizar trilha
    def make_trail_updater(planet_obj, trail_obj):
        def updater(scene):
            frame = scene.frame_current
            if frame < 1 or frame > 500:
                return
            # Apagar apenas se frame=1, senão manter acumulado
            if frame == 1:
                spline.points.clear()
                spline.points.add(0)
            planet_world = planet_obj.matrix_world.translation
            spline = trail_obj.data.splines[0]
            # Definir ponto atual
            spline.points[frame - 1].co = (*planet_world, 1)
            spline.points[frame - 1].radius = 1.0
            # Colapsar e esconder pontos futuros
            current_co = (*planet_world, 1)
            
            for i in range(frame, len(spline.points)):
                spline.points[i].co = current_co
                spline.points[i].radius = 0.0
        return updater

    updater = make_trail_updater(planet, trail_obj)
    bpy.app.handlers.frame_change_pre.append(updater)
    updaters.append(updater)

# Inicializar as trilhas no frame 1
bpy.context.scene.frame_set(1)
for updater in updaters:
    updater(bpy.context.scene)

# Luz
bpy.ops.object.light_add(type='SUN', location=(0, 0, 100))
light = bpy.context.active_object
light.data.energy = 3
light.parent = sun

# Câmera seguindo o Sol
cam_pivot = bpy.data.objects.new("Cam_Pivot", None)
bpy.context.collection.objects.link(cam_pivot)
cam_pivot.parent = sun
bpy.ops.object.camera_add(location=(0, -400, 150))
camera = bpy.context.active_object
camera.name = "Follow_Camera"
camera.parent = cam_pivot
track = camera.constraints.new(type='TRACK_TO')
track.target = sun
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'

# Animação da câmera mais cinematográfica
# Rotação em Z (circulação horizontal)
cam_pivot.rotation_euler = (0, 0, 0)
cam_pivot.keyframe_insert("rotation_euler", frame=1)
cam_pivot.rotation_euler[2] = math.radians(720)
cam_pivot.keyframe_insert("rotation_euler", frame=500)

# Inclinação em X para variar perspectivas verticais
cam_pivot.rotation_euler[0] = 0
cam_pivot.keyframe_insert("rotation_euler", frame=1)
cam_pivot.rotation_euler[0] = math.radians(30)
cam_pivot.keyframe_insert("rotation_euler", frame=150)
cam_pivot.rotation_euler[0] = math.radians(60)
cam_pivot.keyframe_insert("rotation_euler", frame=300)
cam_pivot.rotation_euler[0] = math.radians(-30)
cam_pivot.keyframe_insert("rotation_euler", frame=400)
cam_pivot.rotation_euler[0] = 0
cam_pivot.keyframe_insert("rotation_euler", frame=500)

# Zoom e variação de altura da câmera (local)
camera.location = (0, -400, 150)
camera.keyframe_insert("location", frame=1)
camera.location.y = -200
camera.location.z = 300
camera.keyframe_insert("location", frame=200)
camera.location.y = -300
camera.location.z = 0
camera.keyframe_insert("location", frame=350)
camera.location.y = -400
camera.location.z = 150
camera.keyframe_insert("location", frame=500)

bpy.context.scene.camera = camera

# Fundo negro com estrelas no mundo
bpy.context.scene.world.use_nodes = True
world_nodes = bpy.context.scene.world.node_tree.nodes
world_links = bpy.context.scene.world.node_tree.links
world_nodes.clear()

output = world_nodes.new(type='ShaderNodeOutputWorld')
background = world_nodes.new(type='ShaderNodeBackground')
world_links.new(background.outputs['Background'], output.inputs['Surface'])

# Adicionar estrelas procedurais
noise = world_nodes.new(type='ShaderNodeTexNoise')
noise.noise_dimensions = '3D'
noise.inputs['Scale'].default_value = 200.0
noise.inputs['Detail'].default_value = 2.0
noise.inputs['Roughness'].default_value = 0.5

colorramp = world_nodes.new(type='ShaderNodeValToRGB')
colorramp.color_ramp.interpolation = 'CONSTANT'
colorramp.color_ramp.elements[0].position = 0.0
colorramp.color_ramp.elements[0].color = (0, 0, 0, 1)
colorramp.color_ramp.elements[1].position = 0.995
colorramp.color_ramp.elements[1].color = (0, 0, 0, 1)
new_elem = colorramp.color_ramp.elements.new(0.999)
new_elem.color = (1, 1, 1, 1)

world_links.new(noise.outputs['Fac'], colorramp.inputs['Fac'])
world_links.new(colorramp.outputs['Color'], background.inputs['Color'])

background.inputs['Strength'].default_value = 1.0

# Viewport
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        area.spaces[0].shading.type = 'MATERIAL'
        break
