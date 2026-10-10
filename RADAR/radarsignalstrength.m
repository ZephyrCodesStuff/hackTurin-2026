% 1D FMCW Radar Simulation: Range and Velocity (Doppler) Processing
clear; clc; close all;

%% 1. Radar System Specifications (77 GHz)
fc = 77e9;              % Carrier frequency (77 GHz)
c = 3e8;                % Speed of light (m/s)
lambda = c / fc;        % Wavelength

% Sweep parameters
max_range = 150;        % Radar maximum detection range (m)
range_res = 1;          % Desired range resolution (m)
max_vel = 30;           % Maximum unambiguous velocity (m/s)

B = c / (2 * range_res);          % Bandwidth needed for 1m resolution (150 MHz)
T_chirp = 5.5 * 2 * max_range / c;% Chirp duration (rule of thumb: 5.5 times round trip time)
slope = B / T_chirp;              % Frequency sweep rate (Hz/s)

% Sampling parameters
Nd = 128;               % Number of chirps in one frame (Slow time / Velocity dimension)
Nr = 512;               % Number of samples per chirp (Fast time / Range dimension)
Fs = Nr / T_chirp;      % ADC Sampling frequency

%% 2. Target Definition
% Define the target's horizontal location and speed
target_range = 65;      % Target distance in meters
target_vel = -15;       % Target speed in m/s (negative means moving towards radar)

%% 3. Signal Generation (Beat Signal / IF Signal)
t = linspace(0, Nd * T_chirp, Nr * Nd); % Total time vector for the frame
Tx = zeros(1, length(t));               % Transmit signal placeholder
Rx = zeros(1, length(t));               % Receive signal placeholder
Mix = zeros(1, length(t));              % Mixed (IF) signal placeholder

% Time vectors for 2D matrix mapping
t_fast = linspace(0, T_chirp, Nr);      % Fast time (within one chirp)

% Generate the IF signal directly (to avoid memory crashing from 77GHz sampling)
IF_matrix = zeros(Nr, Nd);

for chirp_idx = 1:Nd
    % Slow time: elapsed time at the start of the current chirp
    t_slow = (chirp_idx - 1) * T_chirp; 
    
    % Instantaneous range of the target for this specific chirp
    R_t = target_range + target_vel * t_slow; 
    
    % Time delay of the received signal
    tau = 2 * R_t / c; 
    
    % IF signal phase calculation
    % Phase = 2*pi * (beat_frequency * fast_time + doppler_shift * slow_time)
    f_beat = (2 * slope * target_range) / c;
    f_doppler = (2 * fc * target_vel) / c;
    
    phase = 2 * pi * (f_beat .* t_fast + f_doppler * t_slow);
    
    % Populate the matrix (rows = range samples, cols = chirps)
    IF_matrix(:, chirp_idx) = cos(phase); 
end

%% 4. Range Processing (1D FFT across Fast Time)
% Apply windowing to reduce sidelobes
window_1d = hamming(Nr);
IF_matrix_win = IF_matrix .* window_1d;

% Perform 1D FFT on the columns (fast time)
sig_fft1 = fft(IF_matrix_win, Nr, 1);
sig_fft1 = abs(sig_fft1 / Nr);
sig_fft1 = sig_fft1(1:Nr/2, :); % Keep only positive frequencies

% Range axis calculation
beat_freq = linspace(0, Fs/2, Nr/2);
range_axis = (c * beat_freq) / (2 * slope);

%% 5. Velocity Processing (2D FFT across Slow Time)
% Apply windowing across the chirps
window_2d = hamming(Nd)';
sig_fft2 = fft(IF_matrix .* window_1d .* window_2d, Nd, 2);

% Shift the zero-frequency component to the center of the spectrum
sig_fft2 = fftshift(sig_fft2, 2);
RDM = abs(sig_fft2 / (Nr * Nd)); % Range-Doppler Map magnitude

% Convert to dB for better visualization
RDM_dB = 10 * log10(RDM);
RDM_dB = RDM_dB(1:Nr/2, :); % Keep only positive ranges

% Velocity axis calculation
doppler_freq = linspace(-1/(2*T_chirp), 1/(2*T_chirp), Nd);
velocity_axis = (c * doppler_freq) / (2 * fc);

%% 6. Plotting the Range-Doppler Map
figure('Name', '1D Radar Range-Doppler Map');
surf(velocity_axis, range_axis, RDM_dB, 'EdgeColor', 'none');
colorbar;
colormap('jet');
view(0, 90); % 2D view from above
title('Range-Doppler Map (Distance vs. Speed)');
xlabel('Speed (m/s) [Negative = Approaching]');
ylabel('Horizontal Location / Range (m)');
axis([-max_vel max_vel 0 max_range]);
grid on;