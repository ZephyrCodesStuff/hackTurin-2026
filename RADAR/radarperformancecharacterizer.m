% Antenna Calculator for Lane Separation at 77 GHz
clear; clc;

% --- Scenario Parameters ---
max_range = 50;            % Maximum radar range (m)
eval_distance = max_range / 2; % Minimum detection distance for this spec (75m)
lane_width = 3.5;           % Standard highway lane width (m)
fov_deg = 120;              % Required Field of View / Beaming Angle (degrees)

% --- Universal Constants ---
c = 3e8;                    % Speed of light
fc = 77e9;                  % Frequency
lambda = c / fc;            % Wavelength

% --- 1. Calculate Required Angular Resolution ---
% Angle subtended by one lane width at the evaluation distance
theta_req_rad = 2 * asin((lane_width / 2) / eval_distance);
theta_req_deg = theta_req_rad * (180 / pi);

% --- 2. Calculate Required Virtual Antennas ---
% Assuming antenna spacing d = lambda/2 for maximum unambiguous FoV
% Resolution (radians) = 2 / N_virtual
N_virtual_req = ceil(2 / theta_req_rad);

% --- 3. Determine TX / RX Combinations ---
% Find reasonable physical antenna combinations that meet the virtual requirement
fprintf('--- Antenna Array Requirements ---\n');
fprintf('Evaluation Distance : %.1f meters\n', eval_distance);
fprintf('Lane Spacing        : %.1f meters\n', lane_width);
fprintf('Required Resolution : %.2f degrees\n\n', theta_req_deg);

fprintf('Minimum Virtual Antennas Required: %d\n', N_virtual_req);
fprintf('Possible Physical Configurations (TX x RX):\n');

% Iterate to find practical combinations (TX is usually lower than RX to save cost)
for tx = 2:12
    rx = ceil(N_virtual_req / tx);
    if rx <= 16 && tx <= rx % Keep limits realistic for modern radar chips
        fprintf('  %d TX and %d RX (Yields %d virtual antennas)\n', tx, rx, tx * rx);
    end
end

% --- 4. Field of View & Element Spacing ---
% To achieve the requested FoV without grating lobes (ghost targets), 
% the element spacing 'd' must be constrained.
max_spacing = lambda / (1 + sin(deg2rad(fov_deg/2)));
fprintf('\n--- Hardware Constraints ---\n');
fprintf('To support a %d-degree FOV, antenna element spacing must be <= %.2f mm\n', fov_deg, max_spacing * 1000);
fprintf('(Standard half-wavelength spacing is %.2f mm)\n', (lambda/2) * 1000);