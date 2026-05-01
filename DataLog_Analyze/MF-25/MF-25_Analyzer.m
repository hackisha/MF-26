% dashboard_fixed.m
close all; clc;

%% ==================== 데이터 로드 ====================
% 파일명이 정확한지 다시 한번 확인해주세요.
try
    data = readtable('datalog_20250928_072417.csv');
catch
    error('파일을 찾을 수 없습니다. CSV 파일이 현재 폴더에 있는지 확인하세요.');
end

%% ==================== 변수 추출 ====================
lat          = data.Latitude;
lon          = data.Longitude;
spd_gps      = data.GPS_Speed_KPH;
ax_raw       = data.ax_g;
ay_raw       = data.ay_g;
rpm          = data.RPM;
vss          = data.VSS_kmh;
gear         = data.Gear;
batt         = data.Batt_V;
roll_rate    = data.ADU_ax_g;
pitch_rate   = data.ADU_ay_g;
yaw_rate     = data.ADU_az_g;
eot_in       = data.OilTemp_C;
eot_out      = data.EOT_OUT;
clt          = data.CLT_C;
fuel_temp    = data.fuelPumpTemp;
egt1         = data.EGT1_C;
egt2         = data.EGT2_C;
lambda       = data.WBO_Lambda;

%% ==================== 가속도 보정 ====================
SCALE = 1/8;
ax = ax_raw * SCALE;
ay = ay_raw * SCALE;
N = length(ax);
t = 1:N;

%% ==================== GPS 유효 구간 ====================
valid     = lon ~= 0 & lat ~= 0 & ~isnan(lon) & ~isnan(lat) & lon > 100;
lon_v     = lon(valid);
lat_v     = lat(valid);
N_gps     = length(lon_v);
valid_idx = find(valid);

%% ==================== Figure 설정 ====================
fig = figure(1);
set(fig, 'Position', [50 50 1500 1000], 'Color', 'w');
set(fig, 'Name', 'Racing Dashboard - Fixed Layout');

%% ==================== GPS 궤적 (범례 위치 조정) ====================
sp_gps = subplot(8, 2, [1 3]);
plot(lon_v, lat_v, 'g-', 'LineWidth', 1.2, 'DisplayName', '궤적'); hold on;
plot(lon_v(1),   lat_v(1),   'bs', 'MarkerSize', 6, 'MarkerFaceColor', 'b', 'DisplayName', '시작');
plot(lon_v(end), lat_v(end), 'r^', 'MarkerSize', 6, 'MarkerFaceColor', 'r', 'DisplayName', '끝');
h_gps = plot(lon_v(1), lat_v(1), 'yo', 'MarkerSize', 10, 'LineWidth', 1.5, ...
    'MarkerFaceColor', 'y', 'MarkerEdgeColor', 'k', 'DisplayName', '현재');
legend('Location', 'northeastoutside', 'FontSize', 8); % 범례를 밖으로 이동
axis equal; grid on; title('GPS 궤적');
hold off;

%% ==================== GPS 속도 ====================
sp_spd = subplot(8, 2, 5);
plot(t, spd_gps, 'g-', 'LineWidth', 0.8);
ylabel('kph'); title('GPS 속도'); grid on;
hl_spd = xline(1, 'r-', 'LineWidth', 1.2, 'Alpha', 0.4);

%% ==================== G-G 다이어그램 (여백 확보) ====================
sp_gg = subplot(8, 2, [7 9 11 13 15]);
hold on;
vg = ~isnan(ax) & ~isnan(ay);
scatter(ay(vg), ax(vg), 1, 'b', 'filled', 'MarkerFaceAlpha', 0.1, 'DisplayName', 'G data');
max_g = max(sqrt(ax(vg).^2 + ay(vg).^2));
th = linspace(0, 2*pi, 100);
plot(max_g*cos(th), max_g*sin(th), 'r--', 'LineWidth', 1.5, 'DisplayName', 'Limit');
h_gg = plot(0, 0, 'yo', 'MarkerSize', 12, 'MarkerFaceColor', 'y', 'MarkerEdgeColor', 'k', 'DisplayName', '현재');
xline(0, 'k-'); yline(0, 'k-');
axis equal; grid on;
legend('Location', 'northeastoutside', 'FontSize', 8);
xlabel('횡G ay [g]'); ylabel('종G ax [g]'); title('G-G 다이어그램');
hold off;

%% ==================== 가속도 ====================
sp_g = subplot(8, 2, 2);
plot(t, ax, 'b', 'DisplayName', '종G'); hold on;
plot(t, ay, 'r', 'DisplayName', '횡G');
legend('Location', 'northeastoutside', 'FontSize', 7);
title('가속도 [g]'); grid on;
hl_g = xline(1, 'r-', 'LineWidth', 1.2, 'Alpha', 0.4);

%% ==================== RPM / VSS ====================
sp_rpm = subplot(8, 2, 4);
rpm_norm = rpm / max(rpm(~isnan(rpm)));
vss_norm = vss / max(vss(~isnan(vss)));
plot(t, rpm_norm, 'b', 'DisplayName', 'RPM'); hold on;
plot(t, vss_norm, 'r', 'DisplayName', 'VSS');
legend('Location', 'northeastoutside', 'FontSize', 7);
title('RPM / VSS (정규화)'); grid on;
hl_rpm = xline(1, 'r-', 'LineWidth', 1.2, 'Alpha', 0.4);

%% ==================== IMU Rates (Roll/Pitch/Yaw) ====================
sp_roll = subplot(8, 2, 6);
plot(t, roll_rate, 'r'); title('Roll rate [dps]'); grid on;
hl_roll = xline(1, 'r-', 'Alpha', 0.4);

sp_pitch = subplot(8, 2, 8);
plot(t, pitch_rate, 'g'); title('Pitch rate [dps]'); grid on;
hl_pitch = xline(1, 'r-', 'Alpha', 0.4);

sp_yaw = subplot(8, 2, 10);
plot(t, yaw_rate, 'b'); title('Yaw rate [dps]'); grid on;
hl_yaw = xline(1, 'r-', 'Alpha', 0.4);

%% ==================== EGT / Lambda (축 겹침 방지) ====================
sp_egt = subplot(8, 2, 12);
yyaxis left;
plot(t, egt1, 'r-', 'DisplayName', 'EGT1'); hold on;
plot(t, egt2, 'm-', 'DisplayName', 'EGT2');
ylabel('Temp [°C]');
yyaxis right;
plot(t, lambda, 'b-', 'DisplayName', 'λ');
ylabel('Lambda'); ylim([0.7 1.3]);
legend('Location', 'northeastoutside', 'FontSize', 7);
title('배기온도 / 공연비'); grid on;
hl_egt = xline(1, 'r-', 'LineWidth', 1.2, 'Alpha', 0.4);

%% ==================== 오일/냉각수 온도 ====================
sp_temp = subplot(8, 2, 14);
plot(t, eot_in, 'r', 'DisplayName', 'Oil In'); hold on;
plot(t, eot_out, 'b', 'DisplayName', 'Oil Out');
plot(t, clt, 'g', 'DisplayName', 'Coolant');
legend('Location', 'northeastoutside', 'FontSize', 7);
title('온도 [°C]'); grid on;
hl_temp = xline(1, 'r-', 'LineWidth', 1.2, 'Alpha', 0.4);

%% ==================== 기어/배터리 ====================
sp_gear = subplot(8, 2, 16);
yyaxis left;
stairs(t, gear, 'k', 'LineWidth', 1.2, 'DisplayName', 'Gear');
ylabel('Gear');
yyaxis right;
plot(t, batt, 'b', 'DisplayName', 'Batt');
ylabel('Volt');
legend('Location', 'northeastoutside', 'FontSize', 7);
title('기어 / 배터리'); grid on;
hl_gear = xline(1, 'r-', 'LineWidth', 1.2, 'Alpha', 0.4);

%% ==================== 전체 레이아웃 미세 조정 ====================
% 서브플롯 간의 간격 조정 (글자 짤림 방지)
all_axes = findobj(fig, 'type', 'axes');
for i = 1:length(all_axes)
    set(all_axes(i), 'FontName', 'Malgun Gothic', 'FontSize', 8);
end

%% ==================== 핸들 배열 ====================
sp_all = [sp_spd, sp_g, sp_rpm, sp_roll, sp_pitch, sp_yaw, sp_egt, sp_temp, sp_gear];
hl_all = [hl_spd, hl_g, hl_rpm, hl_roll, hl_pitch, hl_yaw, hl_egt, hl_temp, hl_gear];

%% ==================== 애니메이션 ====================
ANIM_STEP = 100; % 속도 향상을 위해 스텝 증가
for i = 1:ANIM_STEP:N
    for k = 1:length(hl_all)
        set(hl_all(k), 'Value', i);
    end
    [~, gps_i] = min(abs(valid_idx - i));
    set(h_gps, 'XData', lon_v(gps_i), 'YData', lat_v(gps_i));
    if ~isnan(ay(i)) && ~isnan(ax(i))
        set(h_gg, 'XData', ay(i), 'YData', ax(i));
    end
    drawnow limitrate;
end

%% ==================== hover 등록 ====================
set(fig, 'WindowButtonMotionFcn', ...
    @(src, ~) hoverFcn(src, sp_all, hl_all, h_gps, h_gg, lon_v, lat_v, valid_idx, N, ax, ay));

%% ==================== hover 콜백 함수 (기존 로직 유지) ====================
function hoverFcn(fig, sp_list, hl_list, h_gps, h_gg, lon_v, lat_v, valid_idx, N, ax, ay)
    cur_ax = get(fig, 'CurrentAxes');
    if isempty(cur_ax), return; end
    found = any(sp_list == cur_ax);
    if ~found, return; end
    
    cp = get(cur_ax, 'CurrentPoint');
    x  = round(cp(1, 1));
    if x < 1 || x > N, return; end
    
    for k = 1:length(hl_list)
        set(hl_list(k), 'Value', x);
    end
    [~, gps_i] = min(abs(valid_idx - x));
    set(h_gps, 'XData', lon_v(gps_i), 'YData', lat_v(gps_i));
    if ~isnan(ay(x)) && ~isnan(ax(x))
        set(h_gg, 'XData', ay(x), 'YData', ax(x));
    end
    drawnow limitrate;
end
