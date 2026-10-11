import bpy
import csv
import math

# --- Configuration ---
csv_file_path = r"D:\hackturin\RADAR\simulation of FMCW\fmcwfinal\car_truth_data.csv"
blend_file_path = r"D:\hackturin\RADAR\simulation of FMCW\fmcwfinal\Challenger.blend"
scale_factor = 1.24

# 1. Append all objects from the .blend file
with bpy.data.libraries.load(blend_file_path, link=False) as (data_from, data_to):
    data_to.objects = data_from.objects

if not data_to.objects:
    print("Warning: No objects found inside Challenger.blend. Check the file.")

# Create a template collection to hold the original car parts
template_collection = bpy.data.collections.new("Challenger_Template")
bpy.context.scene.collection.children.link(template_collection)

# Link imported objects to this template collection
for obj in data_to.objects:
    if obj is not None:
        template_collection.objects.link(obj)

# Exclude the template collection from the view layer to hide original objects
layer_collection = bpy.context.view_layer.layer_collection.children[template_collection.name]
layer_collection.exclude = True

active_cars = {}
removed_cars = set()

# 2. Read the CSV and generate Collection Instances
with open(csv_file_path, newline='') as file:
    reader = csv.DictReader(file, delimiter=',')
    
    for row in reader:
        try:
            car_id = row['Car_ID']
            
            # If this car was already removed, skip processing any further rows for it
            if car_id in removed_cars:
                continue
                
            frame_num = int(row['Frame'])
            x_pos = float(row['X_m'])
            y_pos = float(row['Y_m'])
            velocity = float(row['Velocity_mps'])
            
            # If this Car_ID hasn't been seen yet, create a new instance Empty
            if car_id not in active_cars:
                car_instance = bpy.data.objects.new(f"Car_{car_id}", None)
                car_instance.instance_type = 'COLLECTION'
                car_instance.instance_collection = template_collection
                
                # Apply the scale and ONLY 90-deg Z rotation
                car_instance.scale = (scale_factor, scale_factor, scale_factor)
                car_instance.rotation_euler = (0.0, 0.0, math.radians(90))
                
                # --- NEW: Hide the car BEFORE it appears in the CSV ---
                hide_frame = max(0, frame_num - 1)
                car_instance.hide_viewport = True
                car_instance.hide_render = True
                car_instance.keyframe_insert(data_path="hide_viewport", frame=hide_frame)
                car_instance.keyframe_insert(data_path="hide_render", frame=hide_frame)
                
                # Ensure it is visible at the exact frame it spawns
                car_instance.hide_viewport = False
                car_instance.hide_render = False
                car_instance.keyframe_insert(data_path="hide_viewport", frame=frame_num)
                car_instance.keyframe_insert(data_path="hide_render", frame=frame_num)
                
                # Link the instance to the main scene collection
                bpy.context.scene.collection.objects.link(car_instance)
                
                active_cars[car_id] = car_instance
                
            current_car = active_cars[car_id]
            
            # --- Removal Condition ---
            # If Y is negative and velocity is exactly 0 (or close to 0 due to float noise)
            if y_pos < 0 and velocity <= 0.01:
                current_car.hide_viewport = True
                current_car.hide_render = True
                # Keyframe the hidden state at the exact frame it stops
                current_car.keyframe_insert(data_path="hide_viewport", frame=frame_num)
                current_car.keyframe_insert(data_path="hide_render", frame=frame_num)
                
                removed_cars.add(car_id)
                continue # Skip setting the location for this row
                
            # Update location and set keyframe for the specific car instance
            current_car.location = (x_pos, y_pos, 0.0)
            current_car.keyframe_insert(data_path="location", frame=frame_num)
            
        except ValueError:
            continue
        except KeyError as e:
            print(f"Header mismatch. Could not find column: {e}")
            break

print(f"Processed {len(active_cars)} total cars. Dynamically removed {len(removed_cars)} cars that stopped at -Y.")