% =========================================================================
% SCRIPT 3: 3D Radar and Kinematic Visualizer (Video Export)
% Plugs directly into car_truth_data.csv for flawless 3D model alignment.
% =========================================================================
clear; clc; close all;

%% 1. Load Data
car_file   = 'car_truth_data.csv';
radar_file = 'radar_output_data.csv';
stl_file   = 'Car1.stl';

if ~isfile(car_file) || ~isfile(radar_file)
    error('CSV data files not found. Run the simulation script first.');
end

car_data   = readtable(car_file);
radar_data = readtable(radar_file);
num_frames = max(car_data.Frame);
dt = 0.1;

%% 2. Setup 3D Figure
fig = figure('Name', '3D Radar Playback', 'Position', [100, 100, 900, 700]);
hold on; grid on; axis equal;
view(-35, 40); 
camlight; lighting gouraud; 

% Fix axes to keep the environment stable (Restricted to 20m - 60m)
xlim([-8, 8]);
ylim([5, 60]);
zlim([0, 5]);
xlabel('Cross-Range X (m)');
ylabel('Down-Range Y (m)');
zlabel('Elevation Z (m)');

% Draw Road Surface
patch([-5 5 5 -5], [0 0 120 120], [0 0 0 0], [0.2 0.2 0.2], 'FaceAlpha', 0.8, 'EdgeColor', 'none');
plot3([-1.666, -1.666], [0, 120], [0.01, 0.01], 'w--', 'LineWidth', 1.5);
plot3([ 1.666,  1.666], [0, 120], [0.01, 0.01], 'w--', 'LineWidth', 1.5);

scatter3(0, 0, 0.5, 200, 'k', '^', 'filled');

%% 3. Load and Normalize STL Model
if isfile(stl_file)
    car_mesh = stlread(stl_file);
    V = car_mesh.Points;
    F = car_mesh.ConnectivityList;
    
    V = V - mean(V, 1); 
    
    angle_z = -pi/2; 
    angle_y = -pi/2; 
    Rz = makehgtform('zrotate', angle_z);
    Ry = makehgtform('yrotate', angle_y);
    
    V_homog = [V, ones(size(V,1), 1)]';
    V_rotated = Ry * Rz * V_homog;
    V = V_rotated(1:3, :)';
    
    span_x = max(V(:,1)) - min(V(:,1));
    span_y = max(V(:,2)) - min(V(:,2));
    scale_factor = min(2.5 / span_x, 3.0 / span_y);
    V = V * scale_factor; 
    
    V(:,3) = V(:,3) - min(V(:,3)); 
else
    fprintf('STL not found. Using generic 3D bounding box.\n');
    [Xb, Yb, Zb] = meshgrid([-1.25, 1.25], [-1.5, 1.5], [0, 1.6]);
    V = [Xb(:), Yb(:), Zb(:)];
    F = convhull(V);
end

%% 4. Initialize Fast-Updating Graphics Objects
max_cars = 20;
car_transforms = gobjects(max_cars, 1);
for i = 1:max_cars
    car_transforms(i) = hgtransform('Parent', gca);
    patch('Faces', F, 'Vertices', V, 'Parent', car_transforms(i), ...
          'FaceColor', [0.7 0.1 0.1], 'EdgeColor', 'none', ...
          'SpecularStrength', 0.5);
    car_transforms(i).Matrix = makehgtform('translate', [0, 0, -100]); 
end

% Radar Detection Scatter Cloud (Floating just above the road)
h_radar = scatter3(NaN, NaN, NaN, 50, NaN, 'filled', 'MarkerEdgeColor', 'k');

colormap('jet');
clim([-25, 0]); 
cb = colorbar;
ylabel(cb, 'Radial Velocity (m/s)');

title_text = title('Frame: 0 | Time: 0.00s');

%% 5. Animation Playback & Video Export Loop
video_filename = 'radar_3d_simulation.mp4';
v_writer = VideoWriter(video_filename, 'MPEG-4');
v_writer.FrameRate = 1 / dt; 
open(v_writer);

fprintf('Starting 3D Playback and Recording to %s...\n', video_filename);

for f = 1:num_frames
    
    % A. Radar Detections (Set to Z=0.02m)
    frame_radar = radar_data(radar_data.Frame == f, :);
    if ~isempty(frame_radar)
        Z_plane = repmat(0.02, height(frame_radar), 1); 
        set(h_radar, 'XData', frame_radar.X_m, ...
                     'YData', frame_radar.Y_m, ...
                     'ZData', Z_plane, ...
                     'CData', frame_radar.Velocity_mps);
    else
        set(h_radar, 'XData', NaN, 'YData', NaN, 'ZData', NaN, 'CData', NaN);
    end
    
    % B. Ground Truth Cars (Using Exact Centers)
    frame_cars = car_data(car_data.Frame == f, :);
    if ~isempty(frame_cars)
        current_time = frame_cars.Time_s(1);
        num_active = height(frame_cars);
        
        for i = 1:max_cars
            if i <= num_active
                cx = frame_cars.X_m(i);
                cy = frame_cars.Y_m(i);
                car_transforms(i).Matrix = makehgtform('translate', [cx, cy, 0]);
            else
                car_transforms(i).Matrix = makehgtform('translate', [0, 0, -100]);
            end
        end
    else
        current_time = (f-1) * dt;
        for i = 1:max_cars
            car_transforms(i).Matrix = makehgtform('translate', [0, 0, -100]);
        end
    end
    
    set(title_text, 'String', sprintf('Frame: %d/%d | Time: %.2f s', f, num_frames, current_time));
    
    drawnow;
    writeVideo(v_writer, getframe(fig));
end

close(v_writer);
fprintf('Playback Complete. Video successfully saved to %s.\n', video_filename);