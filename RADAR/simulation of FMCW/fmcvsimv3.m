% =========================================================================
% SCRIPT 1: 4D Kinematic Radar Simulation (IDM & Dynamic Traffic)
% Simulates continuous traffic using the Intelligent Driver Model, dynamic
% lane changes, line-of-sight occlusion, and extended rough targets.
% =========================================================================
clear; clc; close all;

%% 1. Radar & Simulation Time Parameters
c       = 3e8;             
fc      = 77e9;            
lambda  = c / fc;          
bw      = 150e6;           
T_chirp = 32e-6;           
slope   = bw / T_chirp;    
fs      = 16e6;            
N_fast  = 512;             
N_slow  = 64;
N_virt  = 16;              
d_virt  = lambda / 2;      
virt_pos = (0:N_virt-1) * d_virt; 

dt = 0.1;                  
T_total = 150;            % 30s to watch traffic jams and lane changes develop
time_vector = 0:dt:T_total;
num_frames = length(time_vector);

lane_width = 10 / 3;
lane_to_x = @(lane_idx) (lane_idx - 2) * lane_width;

%% 2. Traffic Configuration (IDM & Spawner)
max_active_cars = 20;      % Memory buffer for dynamic arrays
lane_speeds = [12.0, 18.0, 25.0]; % Base speeds (Lane 1, 2, 3)
spawn_timers = [0, 0, 0];  % Staggered initial spawn delays
spawn_y = 160.0;           % Spawn entry point

% IDM Parameters
IDM_T  = 1.5;  % Safe time headway (s)
IDM_s0 = 5.0;  % Minimum bumper-to-bumper gap (m)
IDM_a  = 2.0;  % Max comfortable acceleration (m/s^2)
IDM_b  = 3.0;  % Max comfortable deceleration (m/s^2)
car_L  = 3.0;  % Vehicle length

targets = []; % Dynamic array of active cars

[X_local, Y_local] = meshgrid(-1.25 : 0.25 : 1.25, -1.5 : 0.25 : 1.5);
local_points = [X_local(:), Y_local(:)];
voxels_per_target = size(local_points, 1);
total_voxels = max_active_cars * voxels_per_target;

%% 3. Output Array Initialization
voxel_truth_array = NaN(num_frames, total_voxels, 3);
max_detections = 500; 
radar_output_array = NaN(num_frames, max_detections, 4); 

%% 4. Time-Stepped Simulation Loop
fprintf('Simulating %d frames of dynamic IDM traffic...\n', num_frames);
t_fast_vec = (0:N_fast-1)' / fs;
t_slow_vec = (0:N_slow-1) * T_chirp;
window_1d = hanning(N_fast);
window_2d = hanning(N_slow)';
window_3d = hanning(N_virt)';

for f = 1:num_frames
    
    % A. Despawn cars that passed the radar (Y < -10)
    if ~isempty(targets)
        keep_idx = [targets.y] >= -10.0;
        targets = targets(keep_idx);
    end
    
    % B. Spawn new cars at regular intervals if clear
    for l = 1:3
        spawn_timers(l) = spawn_timers(l) - dt;
        if spawn_timers(l) <= 0 && length(targets) < max_active_cars
            % Check if spawn area is safe (no car within 25m)
            is_clear = true;
            for i = 1:length(targets)
                if targets(i).target_lane == l && targets(i).y > (spawn_y - 25.0)
                    is_clear = false;
                    break;
                end
            end
            
            if is_clear
                % Add random +/- 3 m/s variation so cars catch up to each other
                speed_variation = (rand() - 0.5) * 6.0; 
                final_speed = max(lane_speeds(l) + speed_variation, 5.0);
                
                new_car.y = spawn_y;
                new_car.x = lane_to_x(l);
                new_car.v = final_speed;     % Current speed
                new_car.v0 = final_speed;    % Desired speed
                new_car.lane = l;
                new_car.target_lane = l;
                new_car.vx = 0.0;
                new_car.lc_timer = 0;
                targets = [targets, new_car];
                
                % Reset timer to random interval (2 to 4 seconds)
                spawn_timers(l) = 2.0 + rand() * 2.0; 
            end
        end
    end
    
    % C. Update Traffic Logic (IDM & Lane Changing)
    for i = 1:length(targets)
        % Find the leader in the current lane (closest car ahead)
        leader_idx = -1;
        min_gap = inf;
        for j = 1:length(targets)
            if i ~= j && targets(j).target_lane == targets(i).target_lane
                gap = targets(i).y - targets(j).y - car_L;
                if gap > 0 && gap < min_gap
                    min_gap = gap;
                    leader_idx = j;
                end
            end
        end
        
        % IDM Acceleration Math
        s = min_gap;
        v = targets(i).v;
        if leader_idx ~= -1
            delta_v = v - targets(leader_idx).v;
            s_star = IDM_s0 + v * IDM_T + (v * delta_v) / (2 * sqrt(IDM_a * IDM_b));
            accel = IDM_a * (1 - (v / targets(i).v0)^4 - (s_star / s)^2);
        else
            accel = IDM_a * (1 - (v / targets(i).v0)^4); % Free road
        end
        
        % Integration (Velocity cannot be negative in IDM)
        targets(i).v = max(targets(i).v + accel * dt, 0);
        targets(i).y = targets(i).y - (targets(i).v * dt); % Move down-range
        
        % Evaluate Lane Change
        % Trigger if severely blocked (<90% desired speed) OR a 2% random urge per frame
        is_blocked = targets(i).v < (targets(i).v0 * 0.9);
        random_urge = rand() < 0.02; 
        
        if targets(i).lane == targets(i).target_lane && ((is_blocked && rand() < 0.2) || random_urge)
            possible_lanes = [];
            if targets(i).lane > 1, possible_lanes(end+1) = targets(i).lane - 1; end
            if targets(i).lane < 3, possible_lanes(end+1) = targets(i).lane + 1; end
            
            % Randomize the order of lanes checked so they don't always favor moving left
            possible_lanes = possible_lanes(randperm(length(possible_lanes)));
            
            for p_lane = possible_lanes
                % Check if adjacent lane has safe gaps
                safe = true;
                for j = 1:length(targets)
                    if targets(j).target_lane == p_lane
                        gap = abs(targets(i).y - targets(j).y) - car_L;
                        if gap < 15.0 % Need 15 meters clear to safely merge
                            safe = false;
                            break;
                        end
                    end
                end
                if safe
                    targets(i).target_lane = p_lane;
                    targets(i).lc_timer = 2.0; % 2 second maneuver
                    break;
                end
            end
        end
        
        % Execute active lane change lateral movement
        if targets(i).lc_timer > 0
            targets(i).lc_timer = targets(i).lc_timer - dt;
            target_x = lane_to_x(targets(i).target_lane);
            targets(i).vx = (target_x - targets(i).x) / max(targets(i).lc_timer, dt);
            targets(i).x = targets(i).x + (targets(i).vx * dt);
            if targets(i).lc_timer <= 0
                targets(i).lane = targets(i).target_lane;
                targets(i).x = target_x;
                targets(i).vx = 0.0;
            end
        end
    end
    
    % D. Build Voxel Arrays dynamically based on active targets
    vox_X = NaN(total_voxels, 1);
    vox_Y = NaN(total_voxels, 1);
    vox_Vx = NaN(total_voxels, 1);
    vox_Vy = NaN(total_voxels, 1);
    
    for i = 1:length(targets)
        start_idx = (i-1)*voxels_per_target + 1;
        end_idx = i*voxels_per_target;
        vox_X(start_idx:end_idx) = local_points(:,1) + targets(i).x;
        vox_Y(start_idx:end_idx) = local_points(:,2) + targets(i).y;
        vox_Vx(start_idx:end_idx) = targets(i).vx;
        vox_Vy(start_idx:end_idx) = -targets(i).v; % Convert IDM speed to radar negative Y velocity
    end
    
    % Strip NaNs for math
    active_mask = ~isnan(vox_X);
    act_X = vox_X(active_mask);
    act_Y = vox_Y(active_mask);
    act_Vx = vox_Vx(active_mask);
    act_Vy = vox_Vy(active_mask);
    
    % Spherical Math
    act_R = sqrt(act_X.^2 + act_Y.^2); 
    act_Az = asind(act_X ./ act_R); 
    act_V_rad = (act_X .* act_Vx + act_Y .* act_Vy) ./ act_R;
    
    % Save to Truth Array (re-insert into padded matrix)
    voxel_truth_array(f, active_mask, 1) = act_X;
    voxel_truth_array(f, active_mask, 2) = act_Y;
    voxel_truth_array(f, active_mask, 3) = act_V_rad;
    
    % E. Occlusion Shadowing Filter
    front_mask = (act_Y > 0);
    az_res = 0.5;
    az_bins = round(act_Az / az_res);
    bin_offset = min(az_bins) - 1;
    bin_idx = az_bins - bin_offset;
    
    temp_R = act_R;
    temp_R(~front_mask) = inf; 
    min_R_per_bin = accumarray(bin_idx, temp_R, [], @min, inf);
    
    visible_mask = front_mask & (act_R <= min_R_per_bin(bin_idx) + 0.5);
    vis_idx = find(visible_mask);
    
    % F. Synthesize Raw ADC Cube
    raw_adc_cube = zeros(N_fast, N_slow, N_virt);
    for v = vis_idx'
        f_beat = (2 * slope * act_R(v)) / c;
        roughness_phase = rand() * 2 * pi;
        range_phase = (4 * pi * act_R(v)) / lambda + roughness_phase; 
        spatial_phase = (2 * pi / lambda) * virt_pos * sind(act_Az(v));
        
        for ch = 1:N_virt
            fast_signal = exp(1i * (2 * pi * f_beat * t_fast_vec + range_phase));
            doppler_signal = exp(1i * (4 * pi * act_V_rad(v) / lambda) * t_slow_vec);
            IF_signal = 0.1 * exp(1i * spatial_phase(ch)) * (fast_signal * doppler_signal);
            raw_adc_cube(:,:,ch) = raw_adc_cube(:,:,ch) + IF_signal;
        end
    end
    raw_adc_cube = raw_adc_cube + sqrt(0.5/2) * (randn(size(raw_adc_cube)) + 1i*randn(size(raw_adc_cube)));
    
    % G. DSP Pipeline
    for ch = 1:N_virt
        raw_adc_cube(:,:,ch) = raw_adc_cube(:,:,ch) .* window_1d .* window_2d;
    end
    range_fft = fft(raw_adc_cube, N_fast, 1);
    doppler_fft = fftshift(fft(range_fft, N_slow, 2), 2);
    rd_map_mag = sum(abs(doppler_fft), 3);
    
    threshold = max(rd_map_mag(:)) * 0.10; 
    [r_indices, d_indices] = find(rd_map_mag > threshold);
    num_dets = min(length(r_indices), max_detections);
    
    for k = 1:num_dets
        r_idx = r_indices(k);
        d_idx = d_indices(k);
        
        R_val = (r_idx - 1) * (fs / N_fast) * (c / (2 * slope));
        V_val = (d_idx - 1 - N_slow/2) * (lambda / 2) / (N_slow * T_chirp);
        
        spatial_vector = squeeze(doppler_fft(r_idx, d_idx, :)).' .* window_3d;
        angle_fft = fftshift(fft(spatial_vector, 256));
        [~, max_angle_idx] = max(abs(angle_fft));
        Az_val = asind(((max_angle_idx - 1 - 128) / 256) * (lambda / d_virt));
        
        radar_output_array(f, k, 1) = R_val * sind(Az_val); 
        radar_output_array(f, k, 2) = R_val * cosd(Az_val); 
        radar_output_array(f, k, 3) = V_val;                
        radar_output_array(f, k, 4) = Az_val;               
    end
    fprintf('Frame %d done (Tracking %d active cars, %d visible radar voxels)\n', f, length(targets), length(vis_idx));
end
fprintf('Simulation complete. Flattening arrays for CSV...\n');

%% 5. Flatten Arrays and Export to CSV
truth_csv_data = [];
for f = 1:num_frames
    X = squeeze(voxel_truth_array(f, :, 1))';
    Y = squeeze(voxel_truth_array(f, :, 2))';
    V = squeeze(voxel_truth_array(f, :, 3))';
    
    valid = ~isnan(X) & (Y > 0);
    if any(valid)
        frames = repmat(f, sum(valid), 1);
        times  = repmat(time_vector(f), sum(valid), 1);
        truth_csv_data = [truth_csv_data; frames, times, X(valid), Y(valid), V(valid)];
    end
end

radar_csv_data = [];
for f = 1:num_frames
    valid_idx = ~isnan(radar_output_array(f, :, 1)); 
    if any(valid_idx)
        valid_dets = reshape(radar_output_array(f, valid_idx, :), [], 4);
        frames = repmat(f, size(valid_dets, 1), 1);
        times  = repmat(time_vector(f), size(valid_dets, 1), 1);
        radar_csv_data = [radar_csv_data; frames, times, valid_dets];
    end
end

truth_table = array2table(truth_csv_data, 'VariableNames', {'Frame', 'Time_s', 'X_m', 'Y_m', 'Velocity_mps'});
writetable(truth_table, 'voxel_truth_data.csv');

radar_table = array2table(radar_csv_data, 'VariableNames', {'Frame', 'Time_s', 'X_m', 'Y_m', 'Velocity_mps', 'Azimuth_deg'});
writetable(radar_table, 'radar_output_data.csv');
fprintf('Saved CSVs successfully.\n');