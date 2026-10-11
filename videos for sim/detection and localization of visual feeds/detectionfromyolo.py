import math


def calculate_vehicle_location(
    bbox_center_x, 
    bbox_center_y, 
    bbox_width, 
    bbox_height, 
):
    """
    Calculates the 3D Euclidean coordinates of a vehicle on a road.
    
    Parameters:
    - bbox_*: YOLO bounding box parameters in pixels (absolute, not normalized).
    - cam_loc_x, cam_loc_y: Camera X, Y coordinates (0,0 is the traffic light).
    - cam_height: Height of the camera above the ground (Z).
    - cam_pitch_deg: Downward tilt of the camera in degrees (0 is looking straight at the horizon).
    - img_width, img_height: Resolution of the camera image.
    - vfov_deg: Vertical Field of View of the camera in degrees.
    
    Returns:
    - (world_x, world_y): Euclidean coordinates of the vehicle on the road.
    """
    
    # 1. Convert FOV and Pitch to radians
    vfov_rad = math.radians(vfov_deg)
    pitch_rad = math.radians(cam_pitch_deg)
    
    # 2. Calculate the focal length in pixels based on the vertical FOV
    focal_length = (img_height / 2.0) / math.tan(vfov_rad / 2.0)
    
    # 3. Find the pixel coordinate where the vehicle touches the ground
    # We use the bottom center of the bounding box
    u = bbox_center_x
    v = bbox_center_y + (bbox_height / 2.0)
    
    # 4. Calculate the angles from the optical center of the image to the target pixel
    # Optical center is assumed to be exactly in the middle of the image
    c_x = img_width / 2.0
    c_y = img_height / 2.0
    
    # Angle vertically from the center of the camera lens
    alpha_y = math.atan2((v - c_y), focal_length)
    
    # Angle horizontally from the center of the camera lens
    alpha_x = math.atan2((u - c_x), focal_length)
    
    # 5. Calculate forward distance (Y-axis) using the camera height and total downward angle
    # Total angle to the ground point = camera pitch + pixel vertical angle offset
    total_elevation_angle = pitch_rad + alpha_y
    
    # Avoid division by zero if looking at or above the horizon
    if total_elevation_angle <= 0:
        return None # Vehicle is above the horizon line (flying or error)
        
    forward_distance = cam_height / math.tan(total_elevation_angle)
    
    # 6. Calculate lateral distance (X-axis)
    # The lateral distance scales with the forward distance and the horizontal angle
    lateral_distance = forward_distance * math.tan(alpha_x)
    
    # 7. Map to World Coordinates
    # Add the camera's location offset to get the final position relative to the traffic light
    world_x = cam_loc_x + lateral_distance
    world_y = cam_loc_y + forward_distance
    
    return (world_x, world_y)

# --- Example Usage ---

cam_loc_x = 0
cam_loc_y = 0
cam_height = 3 # meters
cam_pitch_deg = 30
img_width = 640
img_height = 480
vfov_deg = 73.74 # FOV

print(f"Vehicle coordinates (X, Y): {vehicle_location}")