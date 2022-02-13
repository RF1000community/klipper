; KISSlicer - FREE
; Linux
; version 1.6.3 Release Linux64
; Built: May  4 2018, 18:10:35
; Running on 4 cores
;
; Saved: 2020-10-22 16:42:35
; 'kisslicer.gcode'
;
; Anti-shrink gain x=1.000000, y=1.000000, z=1.000000
;
; *** Printer Settings ***
;
; printer_name = something
; profile_date = 2020-10-22 16:40:02
; bed_STL_filename = 
; extension = gcode
; cost_per_hour = 0
; g_code_prefix = 3B205B6D6D5D206D6F64650A4732310A3B204162736F
; ^   6C75746520706F736974696F6E206D6F64650A4739300A3B20537461
; ^   72742068656174696E6720746865204265640A4D31343020533C4245
; ^   443E0A3B20486F6D652074686520617865730A4732380A3B20576169
; ^   742074696C6C2074686520426564206973206865617465640A4D3139
; ^   3020533C4245443E0A3B20486561746564206368616D62657220472D
; ^   636F6465206973206E6F7420756E6976657273616C0A3B4D31343120
; ^   533C424F583E0A3B4D31393120533C424F583E0A
; > Decoded
; >   ; [mm] mode
; >   G21
; >   ; Absolute position mode
; >   G90
; >   ; Start heating the Bed
; >   M140 S<BED>
; >   ; Home the axes
; >   G28
; >   ; Wait till the Bed is heated
; >   M190 S<BED>
; >   ; Heated chamber G-code is not universal
; >   ;M141 S<BOX>
; >   ;M191 S<BOX>
; g_code_preheat = NULL
; > Decoded
; g_code_warm = 3B2053656C6563742065787472756465722C207761726D
; ^   20616E6420776169742C2070757267650A47342050300A4D3C455854
; ^   2B313E303420533C54454D503E0A4D3534320A4D35353C4558542B31
; ^   3E2050333230303020533930300A4D3534330A
; > Decoded
; >   ; Select extruder, warm and wait, purge
; >   G4 P0
; >   M<EXT+1>04 S<TEMP>
; >   M542
; >   M55<EXT+1> P32000 S900
; >   M543
; g_code_same_warm = 3B2053616D652065787472756465722C207761726
; ^   D0A47342050300A4D3C4558542B313E303420533C54454D503E0A
; > Decoded
; >   ; Same extruder, warm
; >   G4 P0
; >   M<EXT+1>04 S<TEMP>
; g_code_same_cool = 3B2053616D652065787472756465722C20636F6F6
; ^   C696E6720646F776E0A47342050300A4D3C4558542B313E303420533
; ^   C54454D503E0A
; > Decoded
; >   ; Same extruder, cooling down
; >   G4 P0
; >   M<EXT+1>04 S<TEMP>
; g_code_cool = 3B2053616D652065787472756465722C2061626F757420
; ^   746F20646573656C6563742C2072657472616374206265666F726520
; ^   636F6F6C696E6720646F776E0A4D3534320A4D35363C4558542B313E
; ^   20503634303020533930300A4D3534330A3B20436F6F6C0A47342050
; ^   300A4D3C4558542B313E303420533C54454D503E0A
; > Decoded
; >   ; Same extruder, about to deselect, retract before cooli
; >   ng down
; >   M542
; >   M56<EXT+1> P6400 S900
; >   M543
; >   ; Cool
; >   G4 P0
; >   M<EXT+1>04 S<TEMP>
; g_code_N_layers = NULL
; > Decoded
; g_code_postfix = 3B20416C6C206578747275646572732061726520726
; ^   574697265640A3B204D6F7665207468652068656164207570202F206
; ^   2656420646F776E0A4739310A4731205A2B31300A4739300A3B20747
; ^   5726E206F666620746865206265642026206368616D62657220286D6
; ^   16368696E65207370656369666963290A4D3134302053300A3B4D313
; ^   4312053300A3B2046494C4C205448495320494E204153204E4545444
; ^   544
; > Decoded
; >   ; All extruders are retired
; >   ; Move the head up / bed down
; >   G91
; >   G1 Z+10
; >   G90
; >   ; turn off the bed & chamber (machine specific)
; >   M140 S0
; >   ;M141 S0
; >   ; FILL THIS IN AS NEEDED
; g_code_pause = 3B205061757365207468656E20526573756D650A3B207
; ^   57375616C6C79204D3020287479706963616C29206F72204D3120286
; ^   C65737320636F6D6D6F6E29206F72204D32323620286C65617374207
; ^   06F727461626C65290A4D300A
; > Decoded
; >   ; Pause then Resume
; >   ; usually M0 (typical) or M1 (less common) or M226 (leas
; >   t portable)
; >   M0
; post_process = NULL
; > Decoded
; every_N_layers = 0
; num_extruders = 1
; firmware_type = 0
; add_comments = 1
; g4p_uses_seconds = 1
; fan_on = M106
; fan_off = M107
; fan_pwm = 0
; add_m101_g10 = 0
; z_speed_mm_per_s = 5
; z_settle_mm = 0
; bed_size_x_mm = 100
; bed_size_y_mm = 100
; bed_size_z_mm = 100
; ext_radius = 0
; bed_offset_x_mm = 50
; bed_offset_y_mm = 50
; bed_offset_z_mm = 0
; bed_roughness_mm = 0
; round_bed = 0
; travel_speed_mm_per_s = 150
; rim_speed_mm_per_s = 150
; first_layer_speed_mm_per_s = 20
; dmax_per_layer_mm_per_s = 15
; xy_accel_mm_per_s_per_s = 1500
; xy_steps_per_mm = 200
; lo_speed_top_mm_per_s = 7.5
; lo_speed_perim_mm_per_s = 10
; lo_speed_loops_mm_per_s = 20
; lo_speed_solid_mm_per_s = 25
; lo_speed_sparse_mm_per_s = 30
; hi_speed_top_mm_per_s = 15
; hi_speed_perim_mm_per_s = 20
; hi_speed_loops_mm_per_s = 40
; hi_speed_solid_mm_per_s = 50
; hi_speed_sparse_mm_per_s = 60
; top_raft_speed_mm_per_s = 20
; bottom_raft_speed_mm_per_s = 10
; ext_gain_1 = 1
; ext_1_mat_name = standard
; ext_axis_1 = 0
; ext_gain_2 = 1
; ext_2_mat_name = standard
; ext_axis_2 = 0
; ext_Xoff_2 = 0
; ext_Yoff_2 = 0
; ext_gain_3 = 1
; ext_3_mat_name = standard
; ext_axis_3 = 0
; ext_Xoff_3 = 0
; ext_Yoff_3 = 0
; ext_gain_4 = 1
; ext_4_mat_name = standard
; ext_axis_4 = 0
; ext_Xoff_4 = 0
; ext_Yoff_4 = 0
; heat_time_coef_1 = 0.0015
; nozzle_dia_1 = 0.4
; nozzle_len_1 = 0
; drive_len_1 = 0
; heat_time_coef_2 = 0.0015
; nozzle_dia_2 = 0.4
; nozzle_len_2 = 0
; drive_len_2 = 0
; heat_time_coef_3 = 0.0015
; nozzle_dia_3 = 0.4
; nozzle_len_3 = 0
; drive_len_3 = 0
; heat_time_coef_4 = 0.0015
; nozzle_dia_4 = 0.4
; nozzle_len_4 = 0
; drive_len_4 = 0
; model_ext = 0
; support_ext = 0
; support_body_ext = 0
; raft_ext = 0
; ext_order_optimize = 0
; solid_loop_overlap_fraction = 0.1
; min_seg_len_mm = 0
; z_step_mm = 0
; max_nodes_per_s = 0
;
; *** Material Settings for Extruder 1 ***
;
; material_name = standard
; profile_date = 2020-10-22 16:40:02
; g_code_matl = NULL
; > Decoded
; g_code_matl_custom = NULL
; > Decoded
; matl_user_notes = 4D6174657269616C2050726F66696C652057697A61
; ^   72640A3E204D6174657269616C3A20504C410A3E2046696C616D656E
; ^   74206469616D65746572203D20322E3435205B6D6D5D0A3E20457874
; ^   727573696F6E2074656D7065726174757265203D20313935205B435D
; ^   0A
; > Decoded
; >   Material Profile Wizard
; >   > Material: PLA
; >   > Filament diameter = 2.45 [mm]
; >   > Extrusion temperature = 195 [C]
; fan_Z_mm = 1.5
; fan_loops_percent = 40
; fan_inside_percent = 40
; fan_cool_percent = 50
; temperature_C = 195
; keep_warm_C = 146
; first_layer_C = 195
; bed_C = 43
; chamber_C = 0
; preheat_strategy = 3
; flow_min_mm3_per_s = 0.1
; flow_max_mm3_per_s = 10
; flow_cool_mm3_per_s = 1
; destring_length = 1
; preload_factor = 0
; matl_viscosity_over_elasticity_us = 0.75
; destring_min_mm = 2.5
; destring_trigger_mm = 10
; preload_speed_mm_per_s = 25
; destring_speed_mm_per_s = 31.25
; Z_lift_mm = 0.05
; min_layer_time_s = 10
; wipe_mm = 0
; cost_per_cm3 = 0.04
; flowrate_tweak = 1
; fiber_dia_mm = 2.45
; shrink_percent_xy = 0
; shrink_percent_y = 0
; shrink_percent_z = 0
; purge_vol_mm3 = 42
; purge_color_strength = 0.5
; color = 0
;
; *** Style Settings ***
;
; style_name = def
; profile_date = 2020-10-22 16:40:02
; quality_percentage = 50
; layer_thickness_mm = -33
; max_layer_thickness_mm = -67
; first_layer_thickness_mm = -50
; unsupported_stepover_mm = -50
; supported_stepover_mm = -50
; extrusion_width_mm = 0.4
; num_loops = 2.5
; skin_thickness_mm = 0.7
; infill_extrusion_width = 0.5
; infill_density_denominator = 4
; stacked_layers = 1
; use_corners = 1
; force_joint_layers = 0
; loops_insideout = 1
; join_perimeter_loop = 1
; infill_st_oct_rnd = 2
; travel_mode = 1
; inset_surface_xy_mm = 0
; seam_jitter_degrees = 0
; seam_depth_scaler = 1
; seam_gap_scaler = 0
; seam_angle_degrees = 45
; crowning_threshold_mm = 0.8
;
; *** Support Settings ***
;
; support_name = arghh
; profile_date = 2020-10-22 16:40:02
; support_sheathe = 0
; support_density = 0
; use_lower_interface = 0
; solid_interface = 0
; support_inflate_mm = 0.4
; support_gap_mm = -100
; interface_gap_mm = -100
; support_angle_deg = 50
; support_z_max_mm = -1
; sheathe_z_max_mm = 2
; raft_mode = 0
; prime_pillar_mode = 4
; pillar_placement = 3
; raft_inflate_mm = 0.8
; raft_hi_stride_mm = 0.8
; raft_hi_thick_mm = 0.2
; raft_hi_width_mm = 0.4
; raft_lo_stride_mm = 1.6
; raft_lo_thick_mm = 0.4
; raft_lo_width_mm = 0.8
; brim_mm = 0
; brim_ht_mm = 0
; brim_gap_mm = 0
; brim_fillet = 0
; interface_band_mm = 0.8
; interface_Z_gap_mm = 0
; first_Z_gap_mm = 0
; raft_interface_layers = 1
; raft_interface_bond = 0
; brim_latch = 0
; interface_angle_deg = 30
; interface_stride_mm = 0.4
; interface_width_mm = 0.42
; interface_1st_layer_width_mm = 0.63
;
; *** Actual Slicing Settings As Used ***
;
; layer_thickness_mm = 0.132
; max_layer_thickness_mm = 0.268
; first_layer_thickness_mm = 0.2
; unsupported_stepover_mm = 0.2
; supported_stepover_mm = 0.2
; extrusion_width = 0.4
; num_ISOs = 2.5
; wall_thickness = 0.7
; infill_style = 5
; support_style = 0
; use_lower_interface = 0
; solid_interface = 0
; support_angle = 49.9
; destring_min_mm = 2.5
; stacked_infill_layers = 1
; raft_style = 0
; raft_sees_prime_paths = 0
; raft_extra_interface_layers = 0
; raft_extra_interface_bond = 0
; brim_latch = 0
; raft_hi_stride_mm = 0
; raft_lo_stride_mm = 0
; oversample_res_mm = 0.125
; crowning_threshold_mm = 0.8
; loops_insideout = 1
; join_perimeter_loop = 1
; solid_loop_overlap_fraction = 0.1
; inflate_raft_mm = 0.8
; inflate_support_mm = 0
; model_support_gap_mm = 0.4
; model_interface_gap_mm = 0.4
; brim_mm = 0
; brim_ht_mm = -0
; brim_gap_mm = 0
; infill_st_oct_rnd = 2
; travel_mode = 1
; support_Z_max_mm = 1e+20
; support_sheathe_off_main_both_int = 0
; inset_surface_xy_mm = 0
; seam_jitter_degrees = 0
; seam_depth_scaler = 1
; seam_gap_scaler = 0
; seam_angle_degrees = 45
; seam_use_corners = 1
; force_joint_layers = 0
; interface_band_mm = 0.8
; skip_N_support_layers = 0
; interface_angle_deg = 30
; interface_stride_mm = 0.4
; printer_z_step_mm = 0
; model_and_int_share_ext = 1
; Speed vs Quality = 0.50
; Top Surface Speed = 11.25
; Perimeter Speed = 15.00
; Loops Speed = 30.00
; Solid Speed = 37.50
; Sparse Speed = 45.00
;
; *** G-code Prefix ***
;
; [mm] mode
G21
; Absolute position mode
G90
; Start heating the Bed
M140 S43
; Home the axes
G28
; Wait till the Bed is heated
M190 S43
; Heated chamber G-code is not universal
;M141 S0
;M191 S0
;
; *** Main G-code ***
;
; BEGIN_LAYER_OBJECT z=0.250 z_thickness=0.250
;
; *** Selecting and Warming Extruder 1 to 195 C ***
; Select extruder, warm and wait, purge
G4 P0
M104 S195
M542
M551 P32000 S900
M543
;
;
; *** Estimate 1.232934 [s], Slowing (0.089x) to 10.1 [s] ***
; Fan set to Cool value 50%
;
; 'Prime Pillar Path', 3.1 [RPM], 1.8 [head mm/s]
G1 X51.2 Y51.674 Z0.3 F9000
G1 X51.2 Y51.674 Z0.25 F300
; enable auto-destring
M227 S2963 P2963
; extruder deciRPM
M108 S0
; extruder on
M101
; head speed 1.780007, filament speed 0.056636, preload 0.000000
M108 S31
G1 X51.095 Y51.701 Z0.25 F105.2
G1 X50.779 Y51.78 Z0.25 F105.2
G1 X50.253 Y51.911 Z0.25 F105.2
G1 X49.673 Y51.867 Z0.25 F105.2
G1 X48.958 Y51.812 Z0.25 F105.2
G1 X48.156 Y51.017 Z0.25 F105.2
G1 X48.156 Y50.059 Z0.25 F105.2
G1 X48.156 Y48.983 Z0.25 F105.2
G1 X48.983 Y48.156 Z0.25 F105.2
G1 X50.051 Y48.156 Z0.25 F105.2
G1 X51.017 Y48.156 Z0.25 F105.2
G1 X51.844 Y48.983 Z0.25 F105.2
G1 X51.843 Y50.13 Z0.25 F105.2
G1 X51.843 Y50.996 Z0.25 F105.2
G1 X51.486 Y51.373 Z0.25 F105.2
G1 X51.271 Y51.599 Z0.25 F105.2
G1 X51.2 Y51.674 Z0.25 F105.2
; extruder(s) off
M103
; Fan set to Cool value 50%
;
; 'Destring/Wipe/Jump Path', 0.0 [RPM], 1.8 [head mm/s]
; enable auto-destring
M227 S2963 P2963
; head speed 1.780000, filament speed 0.000000, preload 0.000000
M108 S0
G1 X50.4 Y51.9 Z0.25 F106.8
G1 X50 Y51.9 Z0.25 F106.8
G1 X50 Y51.9 Z0.25 F106.8
G1 X50 Y51.9 Z0.3 F300
; Perimeter Length = 2.740860
; Fan set to Cool value 50%
;
; 'Perimeter Path', 1.6 [RPM], 1.3 [head mm/s]
G1 X50.197 Y50.061 Z0.3 F9000
G1 X50.197 Y50.061 Z0.25 F300
; enable auto-destring
M227 S2963 P2963
; extruder deciRPM
M108 S0
; extruder on
M101
; head speed 1.331368, filament speed 0.028241, preload 0.000000
; Prepare for End-Of-Layer
M108 S16
G1 X50.228 Y50.137 Z0.25 F81.5
G1 X50.271 Y50.247 Z0.25 F81.5
G1 X50.273 Y50.283 Z0.25 F81.5
G1 X50.252 Y50.313 Z0.25 F81.5
G1 X50.217 Y50.323 Z0.25 F81.5
G1 X49.766 Y50.303 Z0.25 F81.5
G1 X49.733 Y50.292 Z0.25 F81.5
G1 X49.71 Y50.267 Z0.25 F81.5
G1 X49.702 Y50.233 Z0.25 F81.5
G1 X49.706 Y50.137 Z0.25 F81.5
G1 X49.698 Y49.77 Z0.25 F81.5
G1 X49.706 Y49.735 Z0.25 F81.5
G1 X49.732 Y49.71 Z0.25 F81.5
G1 X49.766 Y49.702 Z0.25 F81.5
G1 X49.863 Y49.706 Z0.25 F81.5
G1 X50.23 Y49.698 Z0.25 F81.5
G1 X50.265 Y49.706 Z0.25 F81.5
G1 X50.29 Y49.732 Z0.25 F81.5
G1 X50.298 Y49.766 Z0.25 F81.5
G1 X50.294 Y49.863 Z0.25 F81.5
G1 X50.302 Y50.22 Z0.25 F81.5
G1 X50.292 Y50.25 Z0.25 F81.5
G1 X50.266 Y50.269 Z0.25 F81.5
G1 X50.234 Y50.267 Z0.25 F81.5
G1 X50.137 Y50.228 Z0.25 F81.5
G1 X50.061 Y50.197 Z0.25 F81.5
; extruder(s) off
M103
; time estimate: pre = 10.072948, post = 9.988504
; Dwell time remaining = 0.011496
;
; Post-layer lift
M108 S0
G1 X50.061 Y50.197 Z0.55 F300
; END_LAYER_OBJECT z=0.250
; BEGIN_LAYER_OBJECT z=0.500 z_thickness=0.250
; *** Estimate 0.279250 [s], Slowing (0.001x) to 2.8 [s] ***
; Perimeter Length = 2.740860
; Fan set to Cool value 50%
;
; 'Perimeter Path', 1.2 [RPM], 1.0 [head mm/s]
G1 X50.197 Y50.061 Z0.55 F9000
G1 X50.197 Y50.061 Z0.5 F300
; enable auto-destring
M227 S2963 P2963
; extruder deciRPM
M108 S0
; extruder on
M101
; head speed 0.996707, filament speed 0.021142, preload 0.000000
; Prepare for End-Of-Layer
M108 S12
G1 X50.228 Y50.137 Z0.5 F61.1
G1 X50.271 Y50.247 Z0.5 F61.1
G1 X50.273 Y50.283 Z0.5 F61.1
G1 X50.252 Y50.313 Z0.5 F61.1
G1 X50.217 Y50.323 Z0.5 F61.1
G1 X49.766 Y50.303 Z0.5 F61.1
G1 X49.733 Y50.292 Z0.5 F61.1
G1 X49.71 Y50.267 Z0.5 F61.1
G1 X49.702 Y50.233 Z0.5 F61.1
G1 X49.706 Y50.137 Z0.5 F61.1
G1 X49.698 Y49.77 Z0.5 F61.1
G1 X49.706 Y49.735 Z0.5 F61.1
G1 X49.732 Y49.71 Z0.5 F61.1
G1 X49.766 Y49.702 Z0.5 F61.1
G1 X49.863 Y49.706 Z0.5 F61.1
G1 X50.23 Y49.698 Z0.5 F61.1
G1 X50.265 Y49.706 Z0.5 F61.1
G1 X50.29 Y49.732 Z0.5 F61.1
G1 X50.298 Y49.766 Z0.5 F61.1
G1 X50.294 Y49.863 Z0.5 F61.1
G1 X50.302 Y50.22 Z0.5 F61.1
G1 X50.292 Y50.25 Z0.5 F61.1
G1 X50.266 Y50.269 Z0.5 F61.1
G1 X50.234 Y50.267 Z0.5 F61.1
G1 X50.137 Y50.228 Z0.5 F61.1
G1 X50.061 Y50.197 Z0.5 F61.1
; extruder(s) off
M103
; time estimate: pre = 2.757224, post = 2.749915
; Dwell time remaining = 7.250085
;
; Post-layer lift
M108 S0
G1 X50.061 Y50.197 Z0.8 F300
; END_LAYER_OBJECT z=0.500
; BEGIN_LAYER_OBJECT z=0.750 z_thickness=0.250
; *** Estimate 0.279250 [s], Slowing (0.001x) to 2.8 [s] ***
; Perimeter Length = 2.740860
; Fan set to Cool value 50%
;
; 'Perimeter Path', 1.2 [RPM], 1.0 [head mm/s]
G1 X50.197 Y50.061 Z0.8 F9000
G1 X50.197 Y50.061 Z0.75 F300
; enable auto-destring
M227 S2963 P2963
; extruder deciRPM
M108 S0
; extruder on
M101
; head speed 0.996707, filament speed 0.021142, preload 0.000000
; Prepare for End-Of-Layer
M108 S12
G1 X50.228 Y50.137 Z0.75 F61.1
G1 X50.271 Y50.247 Z0.75 F61.1
G1 X50.273 Y50.283 Z0.75 F61.1
G1 X50.252 Y50.313 Z0.75 F61.1
G1 X50.217 Y50.323 Z0.75 F61.1
G1 X49.766 Y50.303 Z0.75 F61.1
G1 X49.733 Y50.292 Z0.75 F61.1
G1 X49.71 Y50.267 Z0.75 F61.1
G1 X49.702 Y50.233 Z0.75 F61.1
G1 X49.706 Y50.137 Z0.75 F61.1
G1 X49.698 Y49.77 Z0.75 F61.1
G1 X49.706 Y49.735 Z0.75 F61.1
G1 X49.732 Y49.71 Z0.75 F61.1
G1 X49.766 Y49.702 Z0.75 F61.1
G1 X49.863 Y49.706 Z0.75 F61.1
G1 X50.23 Y49.698 Z0.75 F61.1
G1 X50.265 Y49.706 Z0.75 F61.1
G1 X50.29 Y49.732 Z0.75 F61.1
G1 X50.298 Y49.766 Z0.75 F61.1
G1 X50.294 Y49.863 Z0.75 F61.1
G1 X50.302 Y50.22 Z0.75 F61.1
G1 X50.292 Y50.25 Z0.75 F61.1
G1 X50.266 Y50.269 Z0.75 F61.1
G1 X50.234 Y50.267 Z0.75 F61.1
G1 X50.137 Y50.228 Z0.75 F61.1
G1 X50.061 Y50.197 Z0.75 F61.1
; extruder(s) off
M103
; time estimate: pre = 2.757225, post = 2.749915
; Dwell time remaining = 7.250085
;
; Post-layer lift
M108 S0
G1 X50.061 Y50.197 Z1.05 F300
; END_LAYER_OBJECT z=0.750
; BEGIN_LAYER_OBJECT z=1.000 z_thickness=0.250
; *** Estimate 0.343250 [s], Slowing (0.001x) to 2.8 [s] ***
; Perimeter Length = 2.740860
; Fan set to Cool value 50%
;
; 'Perimeter Path', 1.2 [RPM], 1.0 [head mm/s]
G1 X50.197 Y50.061 Z1.05 F9000
G1 X50.197 Y50.061 Z1 F300
; enable auto-destring
M227 S2963 P2963
; extruder deciRPM
M108 S0
; extruder on
M101
; head speed 0.996707, filament speed 0.021142, preload 0.000000
; Prepare for End-Of-Layer
M108 S12
G1 X50.228 Y50.137 Z1 F61.1
G1 X50.271 Y50.247 Z1 F61.1
G1 X50.273 Y50.283 Z1 F61.1
G1 X50.252 Y50.313 Z1 F61.1
G1 X50.217 Y50.323 Z1 F61.1
G1 X49.766 Y50.303 Z1 F61.1
G1 X49.733 Y50.292 Z1 F61.1
G1 X49.71 Y50.267 Z1 F61.1
G1 X49.702 Y50.233 Z1 F61.1
G1 X49.706 Y50.137 Z1 F61.1
G1 X49.698 Y49.77 Z1 F61.1
G1 X49.706 Y49.735 Z1 F61.1
G1 X49.732 Y49.71 Z1 F61.1
G1 X49.766 Y49.702 Z1 F61.1
G1 X49.863 Y49.706 Z1 F61.1
G1 X50.23 Y49.698 Z1 F61.1
G1 X50.265 Y49.706 Z1 F61.1
G1 X50.29 Y49.732 Z1 F61.1
G1 X50.298 Y49.766 Z1 F61.1
G1 X50.294 Y49.863 Z1 F61.1
G1 X50.302 Y50.22 Z1 F61.1
G1 X50.292 Y50.25 Z1 F61.1
G1 X50.266 Y50.269 Z1 F61.1
G1 X50.234 Y50.267 Z1 F61.1
G1 X50.137 Y50.228 Z1 F61.1
G1 X50.061 Y50.197 Z1 F61.1
; extruder(s) off
M103
; Fan set to Cool value 50%
;
; 'Destring/Wipe/Jump Path', 0.0 [RPM], 0.0 [head mm/s]
; enable auto-destring
M227 S2963 P2963
; head speed 0.045000, filament speed 0.000000, preload 0.000000
; Prepare for End-Of-Layer
; time estimate: pre = 2.821224, post = 2.749915
; Dwell time remaining = 7.250085
;
; Post-layer lift
M108 S0
G1 X50.061 Y50.197 Z1.314 F300
; END_LAYER_OBJECT z=1.000
;
; *** Cooling Extruder 1 to 0 C and Retiring ***
; Same extruder, about to deselect, retract before cooling down
M542
M561 P6400 S900
M543
; Cool
G4 P0
M104 S0
;
; *** G-code Postfix ***
;
; All extruders are retired
; Move the head up / bed down
G91
G1 Z+10
G90
; turn off the bed & chamber (machine specific)
M140 S0
;M141 S0
; FILL THIS IN AS NEEDED
;
;
;
; Estimated Build Time:   1.62 minutes
; Estimated Build Cost:   $0.00
;
; *** Extrusion Time Breakdown ***
; * estimated time in [s]
; * before possibly slowing down for 'cool'
; * not including Z-travel
;	......................................................................................
;	: Extruder #1 : Extruder #2 : Extruder #3 : Extruder #4 : Path Type                  :
;	:.............:.............:.............:.............:............................:
;	: 0.0702323   : 0           : 0           : 0           : Jump Path                  :
;	: 0           : 0           : 0           : 0           : Pillar Path                :
;	: 0           : 0           : 0           : 0           : Raft Path                  :
;	: 0           > 0           > 0           > 0           > Support Interface Path     :
;	: 0           : 0           : 0           : 0           : Support (may Stack) Path   :
;	: 1.117       : 0           : 0           : 0           : Perimeter Path             :
;	: 0           : 0           : 0           : 0           : Loop Path                  :
;	: 0           > 0           > 0           > 0           > Solid Path                 :
;	: 0           : 0           : 0           : 0           : Sparse Infill Path         :
;	: 0           : 0           : 0           : 0           : Stacked Sparse Infill Path :
;	: 0.202894    : 0           : 0           : 0           : Destring/Wipe/Jump Path    :
;	: 0           > 0           > 0           > 0           > Crown Path                 :
;	: 0.744558    : 0           : 0           : 0           : Prime Pillar Path          :
;	: 0           : 0           : 0           : 0           : Travel Path                :
;	: 0           : 0           : 0           : 0           : Pause Point                :
;	: 57.0375     > 0           > 0           > 0           > Extruder Warm-Up           :
;	:.............:.............:.............:.............:............................:
 Total estimated (pre-cool) minutes: 0.99
