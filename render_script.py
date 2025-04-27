import bpy # không phải không import được thư viện đâu, mà do cái này của blender
import math
import shutil
import gc
import sys
from mathutils import Vector # như trên
from pathlib import Path
def hard_memory_cleanup():
    """Nuclear cleanup that preserves lighting and materials"""
    # Backup critical data
    world_backup = bpy.data.worlds.get("World")
    lights = [obj for obj in bpy.data.objects if obj.type == 'LIGHT']
    
    # Remove all objects except cameras (needed for rendering)
    bpy.ops.object.select_all(action='SELECT')
    for obj in bpy.context.selected_objects:
        if obj.type != 'CAMERA':
            bpy.data.objects.remove(obj, do_unlink=True)
    
    # Purge orphaned data
    for data_type in ['meshes', 'materials', 'textures', 'images', 'node_groups']:
        for block in list(getattr(bpy.data, data_type)):
            if block.users == 0:
                try:
                    getattr(bpy.data, data_type).remove(block)
                except:
                    pass
    
    # Restore lighting
    if world_backup:
        bpy.data.worlds.new("World")
        bpy.data.worlds["World"].use_nodes = True
    for light in lights:
        bpy.context.scene.collection.objects.link(light)
    
    # Force garbage collection
    gc.collect()


def clear_memory():
    """Aggressive yet safe memory cleanup between renders"""
    # 1. Purge all unused data blocks (expanded list)
    for data_type in ['meshes', 'materials', 'textures', 'images', 
                     'lights', 'cameras', 'node_groups', 'brushes']:
        for block in list(getattr(bpy.data, data_type)):
            if block.users == 0:
                try:
                    getattr(bpy.data, data_type).remove(block)
                except:
                    pass
    # 3. Deep Python garbage collection
    import gc
    for generation in range(2, -1, -1):
        gc.collect(generation)

    # 4. Optional: Clear the undo stack (prevents history bloat)
    if bpy.app.background and hasattr(bpy.ops.ed, 'undo_push'):
        bpy.ops.ed.undo_push()

def process_batch(object_folders, batch_size=5):
    """Process objects in memory-controlled batches"""
    for i, folder in enumerate(object_folders, 1):
        try:
            print(f"Processing {folder.name}")
            process_object(folder)
            
            # Hard reset every N objects
            if i % batch_size == 0:
                print(f"Performing deep memory cleanup...")
                hard_memory_cleanup()
                
        except Exception as e:
            print(f"Failed on {folder.name}: {str(e)}")

def setup_world_nodes():
    """Set up world nodes for consistent lighting and background"""
    world = bpy.data.worlds["World"]
    world.use_nodes = True
    nodes = world.node_tree.nodes
    links = world.node_tree.links

    # Clear existing nodes
    nodes.clear()

    # Create nodes
    background_node = nodes.new('ShaderNodeBackground')
    background_node.inputs[0].default_value = (0.9, 0.9, 0.9, 1)
    background_node.inputs[1].default_value = 10.0

    transparent_node = nodes.new('ShaderNodeBackground')
    transparent_node.inputs[0].default_value = (0.8, 0.8, 0.8, 1)
    transparent_node.inputs[1].default_value = 1.0

    mix_shader = nodes.new('ShaderNodeMixShader')
    light_path = nodes.new('ShaderNodeLightPath')
    output_node = nodes.new('ShaderNodeOutputWorld')

    # Connect nodes
    links.new(light_path.outputs['Is Camera Ray'], mix_shader.inputs['Fac'])
    links.new(transparent_node.outputs['Background'], mix_shader.inputs[1])
    links.new(background_node.outputs['Background'], mix_shader.inputs[2])
    links.new(mix_shader.outputs['Shader'], output_node.inputs['Surface'])

def fix_disconnected_parts(obj):
    """Ensure all parts of the object are properly connected"""
    # Select all mesh objects that might be parts of this model
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    
    # Join all selected objects (assuming they should be one object)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.join()
    
    # Recalculate the origin to geometry center
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')

def restore_missing_materials(obj):
    """Ensure all materials are properly assigned to the object"""
    if not obj.data.materials:
        # If no materials, try to find and assign them
        for mat in bpy.data.materials:
            if mat.name.startswith(obj.name):
                obj.data.materials.append(mat)
    
    # Ensure each face has material assigned
    if obj.type == 'MESH' and obj.data.polygons:
        for poly in obj.data.polygons:
            if poly.material_index >= len(obj.material_slots):
                poly.material_index = 0  # Assign to first material if invalid

def optimize_materials(obj):
    """Optimize materials by reducing shininess and roughness"""
    for slot in obj.material_slots:
        mat = slot.material
        if mat and mat.use_nodes:
            # Ensure we're using the principled BSDF
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            
            # Find principled BSDF or create one
            bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if not bsdf:
                bsdf = nodes.new('ShaderNodeBsdfPrincipled')
                output = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
                links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
            
            # Set material properties
            for inp in bsdf.inputs:
                name = inp.name.lower()
                if inp.type == 'VALUE':
                    if 'specular' in name:
                        if inp.is_linked:
                            inp.links.clear()
                        inp.default_value = 0.1
                    elif 'roughness' in name:
                        if inp.is_linked:
                            inp.links.clear()
                        inp.default_value = 0.5
            
            # Check for missing textures and reconnect them
            for node in nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    # Try to connect to Base Color if not connected
                    if not any(l.to_socket == bsdf.inputs['Base Color'] for l in node.outputs[0].links):
                        links.new(node.outputs['Color'], bsdf.inputs['Base Color'])

def calculate_optimal_distance(obj):
    """Calculate optimal camera distance based on object bounding box"""
    # Get all objects if this is a collection
    objects = [obj] if not obj.instance_collection else obj.instance_collection.objects
    
    # Calculate combined bounding box
    min_coord = Vector((float('inf'), float('inf'), float('inf')))
    max_coord = Vector((float('-inf'), float('-inf'), float('-inf')))
    
    for o in objects:
        if o.type == 'MESH':
            for v in o.bound_box:
                global_v = o.matrix_world @ Vector(v)
                min_coord.x = min(min_coord.x, global_v.x)
                min_coord.y = min(min_coord.y, global_v.y)
                min_coord.z = min(min_coord.z, global_v.z)
                max_coord.x = max(max_coord.x, global_v.x)
                max_coord.y = max(max_coord.y, global_v.y)
                max_coord.z = max(max_coord.z, global_v.z)
    
    # Calculate diagonal of combined bounding box
    diagonal = (max_coord - min_coord).length
    
    # Base distance is 2 times the diagonal plus some margin
    distance = diagonal * 2.0 + 0.5
    
    # Ensure minimum distance for very small objects
    return max(distance, 1.5)

def setup_camera(obj, camera_name="Camera"):
    """Set up camera with appropriate settings for the object"""
    if camera_name not in bpy.data.objects:
        bpy.ops.object.camera_add()
    camera = bpy.data.objects[camera_name]
    bpy.context.scene.camera = camera
    
    # Calculate focal length based on object size
    max_dimension = max(obj.dimensions)
    camera.data.lens = max_dimension * 40  # Adjusted multiplier for better framing
    
    # Set camera clipping to handle both large and small objects
    camera.data.clip_start = 0.01
    camera.data.clip_end = 1000.0
    
    return camera

def set_camera_position(camera, position, target):
    """Position camera and point it at the target"""
    camera.location = position
    direction = target - camera.location
    camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


def render_views(obj, camera, output_path, num_views=12, resolution=(512, 512)):
    """Render multiple views of the object from different angles"""
    obj_location = obj.location
    radius = calculate_optimal_distance(obj)
    
    # Common render settings
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = resolution
    
    # View angles with better framing
    angles = [
        ('angle_top', 35),    # 35° elevation
        ('angle_middle', 5),   # Eye level
    ]
    
    for view_name, elevation_deg in angles:
        elevation_rad = math.radians(elevation_deg)
        horizontal_scale = math.cos(elevation_rad)
        elevation = radius * math.sin(elevation_rad)
        
        for i in range(num_views):
            angle = math.radians(i * 360 / num_views)
            cam_x = obj_location.x + radius * math.cos(angle) * horizontal_scale
            cam_y = obj_location.y + radius * math.sin(angle) * horizontal_scale
            cam_z = obj_location.z + elevation
            
            set_camera_position(camera, (cam_x, cam_y, cam_z), obj_location)
            bpy.context.scene.render.filepath = f"{output_path}/{view_name}_{i:02d}.jpg"
            bpy.ops.render.render(write_still=True)
    
    # top
    angle = math.radians(90)
    cam_y = radius * math.cos(angle)
    cam_z = obj_location.z + radius * math.sin(angle)
    cam_x = obj_location.x
    set_camera_position(camera, (cam_x, cam_y, cam_z), obj_location)
    bpy.context.scene.render.filepath = f"{output_path}/angle_top.jpg"
    bpy.ops.render.render(write_still=True)
    # bottom
    angle = math.radians(-90)
    cam_y = radius * math.cos(angle)
    cam_z = obj_location.z + radius * math.sin(angle)
    cam_x = obj_location.x
    set_camera_position(camera, (cam_x, cam_y, cam_z), obj_location)
    bpy.context.scene.render.filepath = f"{output_path}/angle_bottom.jpg"
    bpy.ops.render.render(write_still=True)

def clean_scene():
    """Remove all objects and lights from the scene"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Remove lights and cameras more efficiently
    for obj in bpy.data.objects:
        if obj.type in {'LIGHT', 'CAMERA'}:
            bpy.data.objects.remove(obj, do_unlink=True)


def process_object(object_folder):
    clear_memory()
    """Process a single object folder"""
    clean_scene()
    
    # Import OBJ with corrected axis specification
    obj_path = object_folder / 'normalized_model.obj'
    bpy.ops.wm.obj_import(
        filepath=str(obj_path),
        forward_axis='NEGATIVE_Z',  # Corrected from '-Z'
        up_axis='Y',                # Keeps objects upright
        global_scale=1.0
    )
    
    # Get imported object(s)
    imported_objects = [obj for obj in bpy.context.selected_objects]
    
    # If multiple objects, join them
    if len(imported_objects) > 1:
        bpy.context.view_layer.objects.active = imported_objects[0]
        bpy.ops.object.join()
    
    obj = bpy.context.active_object
    # Fix object issues
    fix_disconnected_parts(obj)
    restore_missing_materials(obj)
    # Prepare object - NO MANUAL ROTATION NEEDED
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    obj.location = (0, 0, 0)
    # Optimize materials
    optimize_materials(obj)
    # Set up camera
    camera = setup_camera(obj)
    # Create output directory
    rendered_images_dir = object_folder / 'rendered_images'
    if rendered_images_dir.exists():
        shutil.rmtree(rendered_images_dir)
    rendered_images_dir.mkdir(parents=True)
    # Render views (using your original camera angles)
    render_views(obj, camera, str(rendered_images_dir))

    #clear cache
    clear_memory()
from pathlib import Path
import bpy

def blend(all_rooms_folder_path):
    """Main processing function"""
    # Set render settings
    bpy.context.scene.render.image_settings.file_format = 'JPEG'
    bpy.context.scene.render.image_settings.quality = 90
    setup_world_nodes()
    
    # Collect all object folders directly from the root folder
    base_dir = Path(all_rooms_folder_path)
    object_folders = [folder for folder in base_dir.iterdir() if folder.is_dir()]
    
    # Debug: Print information
    print(f"Root path: {base_dir}")
    print(f"Number of subfolder found: {len(object_folders)}")
    if object_folders:
        print(f"Subfolder: {[str(f) for f in object_folders]}")
    else:
        print("Cant find any subfolder")
    
    # Check if no folders are found
    if not object_folders:
        print("Warn: there is no Subfolder. please check again")
        return  # Exit if no folders to process
    
    # Process in batches
    process_batch(object_folders, batch_size=5)

if __name__ == "__main__":
    print("Start render")
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    
    if args:
        print(f"Starting to process folder: {args[0]}")
        blend(args[0])
    else:
        print("Usage: blender -b -P render_script.py -- /path/to/rooms_folder")
        print("Or: blender -b -P render_script.py /path/to/rooms_folder")
    
    print("Finished rendered")
