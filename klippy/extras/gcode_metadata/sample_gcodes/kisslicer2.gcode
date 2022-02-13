; KISSlicer - FREE
; Linux
; version 2 a 2.0.6 Linux64
; Built: Jul 22 2020, 08:28:07
; Running on 4 cores
;
; Saved: 2020-10-22 17:05:31
; 'kisslicer2.gcode'
;
; Anti-shrink gain x=1.000000, y=1.000000, z=1.000000
;
; *** Printer Settings ***
;
; printer_name = sample printer
; profile_date = 2020-10-22 17:05:17
; bed_STL_filename = 
; extension = gcode
; cost_per_hour = 0
; g_code_prefix = 3B205B6D6D5D206D6F64650A4732310A3B206162736F
; ^   6C757465206D6F64650A4739300A3B206162736F6C75746520457874
; ^   7275646572206D6F64650A4D38320A3B20686F6D6520746865206178
; ^   65730A4732380A3B206865617420746865206265640A4D3134302053
; ^   3C4245443E0A
; > Decoded
; >   ; [mm] mode
; >   G21
; >   ; absolute mode
; >   G90
; >   ; absolute Extruder mode
; >   M82
; >   ; home the axes
; >   G28
; >   ; heat the bed
; >   M140 S<BED>
; g_code_preheat = 3B20686561742074686520657874727564657220776
; ^   974686F75742077616974696E670A3B4D31303420533C54454D503E2
; ^   0543C4558542B303E0A3B204C65617665207468697320626C616E6B2
; ^   0746F2064697361626C6520707265686561740A
; > Decoded
; >   ; heat the extruder without waiting
; >   ;M104 S<TEMP> T<EXT+0>
; >   ; Leave this blank to disable preheat
; g_code_warm = 3B2053656C6563742065787472756465722C207761726D
; ^   2C2070757267650A0A3B204266422D7374796C650A4D3C4558542B31
; ^   3E303420533C54454D503E0A4D3534320A4D35353C4558542B313E20
; ^   50333230303020533930300A4D3534330A0A3B2035442D7374796C65
; ^   0A543C4558542B303E0A4D31303420533C54454D503E0A473120583C
; ^   4E455854583E20593C4E455854593E2046363030300A4D3130392053
; ^   3C54454D503E0A
; > Decoded
; >   ; Select extruder, warm, purge
; >   ; BfB-style
; >   M<EXT+1>04 S<TEMP>
; >   M542
; >   M55<EXT+1> P32000 S900
; >   M543
; >   ; 5D-style
; >   T<EXT+0>
; >   M104 S<TEMP>
; >   G1 X<NEXTX> Y<NEXTY> F6000
; >   M109 S<TEMP>
; g_code_same_warm = NULL
; > Decoded
; g_code_same_cool = NULL
; > Decoded
; g_code_cool = 3B2047756172616E746565642073616D65206578747275
; ^   6465722C206275742061626F757420746F20646573656C6563742C20
; ^   6D617962652072657472616374206265666F726520636F6F6C696E67
; ^   20646F776E0A0A3B204266422D7374796C650A4D3C4558542B313E30
; ^   3420533C54454D503E0A0A3B2035442D7374796C650A4D3130342053
; ^   3C54454D503E0A
; > Decoded
; >   ; Guaranteed same extruder, but about to deselect, maybe
; >    retract before cooling down
; >   ; BfB-style
; >   M<EXT+1>04 S<TEMP>
; >   ; 5D-style
; >   M104 S<TEMP>
; g_code_N_layers = 3B204D617962652072652D686F6D65205820262059
; ^   3F
; > Decoded
; >   ; Maybe re-home X & Y?
; g_code_postfix = 3B20416C6C207573656420657874727564657273206
; ^   1726520616C72656164792027436F6F6C65642720746F20300A3B207
; ^   475726E206F666620746865206265642026206368616D6265720A4D3
; ^   134302053300A
; > Decoded
; >   ; All used extruders are already 'Cooled' to 0
; >   ; turn off the bed & chamber
; >   M140 S0
; g_code_pause = 3B205061757365207468656E20526573756D650A3B207
; ^   57375616C6C79204D3020287479706963616C29206F72204D3120286
; ^   C65737320636F6D6D6F6E29206F72204D32323620286C65617374207
; ^   06F727461626C65290A
; > Decoded
; >   ; Pause then Resume
; >   ; usually M0 (typical) or M1 (less common) or M226 (leas
; >   t portable)
; post_process = NULL
; > Decoded
; printer_ID_string = NULL
; > Decoded
; every_N_layers = 0
; num_extruders = 1
; firmware_type = 2
; add_comments = 1
; enable_equation_parser = 0
; g4p_uses_seconds = 0
; fan_on = M106
; fan_off = M107
; fan_pwm = 1
; arc_export_mode = 0
; add_m101_g10 = 0
; z_speed_mm_per_s = 5
; z_settle_mm = 0
; final_z_min_mm = 0
; bed_size_x_mm = 100
; bed_size_y_mm = 100
; bed_size_z_mm = 100
; ext_radius = 0
; bed_offset_x_mm = 0
; bed_offset_y_mm = 0
; bed_offset_z_mm = 0
; bed_roughness_mm = 0
; round_bed = 0
; slant_Z_angle = -1
; travel_speed_mm_per_s = 150
; rim_speed_mm_per_s = 150
; first_layer_speed_mm_per_s = 20
; dmax_per_layer_mm_per_s = 15
; xy_accel_mm_per_s_per_s = 1500
; xy_steps_per_mm = 150
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
; default_ironing_speed_mm_per_s = 15
; ext_1_mat_name = sample material
; ext_axis_1 = 0
; ext_gain_1 = 1
; ext_Xoff_1 = 0
; ext_Yoff_1 = 0
; heat_time_coef_1 = 0.0015
; nozzle_dia_1 = 0.4
; nozzle_len_1 = 0.6
; drive_len_1 = 0
; ext_2_mat_name = sample material
; ext_axis_2 = 0
; ext_gain_2 = 1
; ext_Xoff_2 = 0
; ext_Yoff_2 = 0
; heat_time_coef_2 = 0.0015
; nozzle_dia_2 = 0.4
; nozzle_len_2 = 0.6
; drive_len_2 = 0
; ext_3_mat_name = sample material
; ext_axis_3 = 0
; ext_gain_3 = 1
; ext_Xoff_3 = 0
; ext_Yoff_3 = 0
; heat_time_coef_3 = 0.0015
; nozzle_dia_3 = 0.4
; nozzle_len_3 = 0.6
; drive_len_3 = 0
; ext_4_mat_name = sample material
; ext_axis_4 = 0
; ext_gain_4 = 1
; ext_Xoff_4 = 0
; ext_Yoff_4 = 0
; heat_time_coef_4 = 0.0015
; nozzle_dia_4 = 0.4
; nozzle_len_4 = 0.6
; drive_len_4 = 0
; ext_5_mat_name = sample material
; ext_axis_5 = 0
; ext_gain_5 = 1
; ext_Xoff_5 = 0
; ext_Yoff_5 = 0
; heat_time_coef_5 = 0.0015
; nozzle_dia_5 = 0.4
; nozzle_len_5 = 0.6
; drive_len_5 = 0
; ext_6_mat_name = sample material
; ext_axis_6 = 0
; ext_gain_6 = 1
; ext_Xoff_6 = 0
; ext_Yoff_6 = 0
; heat_time_coef_6 = 0.0015
; nozzle_dia_6 = 0.4
; nozzle_len_6 = 0.6
; drive_len_6 = 0
; ext_7_mat_name = sample material
; ext_axis_7 = 0
; ext_gain_7 = 1
; ext_Xoff_7 = 0
; ext_Yoff_7 = 0
; heat_time_coef_7 = 0.0015
; nozzle_dia_7 = 0.4
; nozzle_len_7 = 0.6
; drive_len_7 = 0
; ext_8_mat_name = sample material
; ext_axis_8 = 0
; ext_gain_8 = 1
; ext_Xoff_8 = 0
; ext_Yoff_8 = 0
; heat_time_coef_8 = 0.0015
; nozzle_dia_8 = 0.4
; nozzle_len_8 = 0.6
; drive_len_8 = 0
; ext_9_mat_name = sample material
; ext_axis_9 = 0
; ext_gain_9 = 1
; ext_Xoff_9 = 0
; ext_Yoff_9 = 0
; heat_time_coef_9 = 0.0015
; nozzle_dia_9 = 0.4
; nozzle_len_9 = 0.6
; drive_len_9 = 0
; ext_10_mat_name = sample material
; ext_axis_10 = 0
; ext_gain_10 = 1
; ext_Xoff_10 = 0
; ext_Yoff_10 = 0
; heat_time_coef_10 = 0.0015
; nozzle_dia_10 = 0.4
; nozzle_len_10 = 0.6
; drive_len_10 = 0
; ext_11_mat_name = sample material
; ext_axis_11 = 0
; ext_gain_11 = 1
; ext_Xoff_11 = 0
; ext_Yoff_11 = 0
; heat_time_coef_11 = 0.0015
; nozzle_dia_11 = 0.4
; nozzle_len_11 = 0.6
; drive_len_11 = 0
; ext_12_mat_name = sample material
; ext_axis_12 = 0
; ext_gain_12 = 1
; ext_Xoff_12 = 0
; ext_Yoff_12 = 0
; heat_time_coef_12 = 0.0015
; nozzle_dia_12 = 0.4
; nozzle_len_12 = 0.6
; drive_len_12 = 0
; model_ext = 0
; support_ext = 0
; support_body_ext = 0
; raft_ext = 0
; ext_order_optimize = 0
; solid_loop_overlap_fraction = 0.1
; min_seg_len_mm = 0
; z_step_mm = 0
; max_nodes_per_s = 0
; disable_bookend_destring = 0
; cool_purge_vol_mm3 = 0
; cool_purge_dC = 10
;
; *** Material Settings for Extruder 1 ***
;
; material_name = sample material
; profile_date = 2020-10-22 17:05:17
; g_code_matl = 3B204D617962652073657420736F6D65206D6174657269
; ^   616C2D737065636966696320472D636F64653F
; > Decoded
; >   ; Maybe set some material-specific G-code?
; g_code_matl_custom = 3C534F4D455F435553544F4D5F544F4B454E3E3
; ^   D5B3B20536F6D6520637573746F6D20472D636F64655D0A3C534F4D4
; ^   55F4F544845525F435553544F4D5F544F4B454E3E3D5B0A3B20536F6
; ^   D65206F7468657220637573746F6D20472D636F64650A3B205468697
; ^   3206F6E65206973206D756C74692D6C696E650A5D
; > Decoded
; >   <SOME_CUSTOM_TOKEN>=[; Some custom G-code]
; >   <SOME_OTHER_CUSTOM_TOKEN>=[
; >   ; Some other custom G-code
; >   ; This one is multi-line
; >   ]
; matl_user_notes = NULL
; > Decoded
; fan_Z_mm = 0
; fan_loops_percent = 100
; fan_inside_percent = 0
; fan_cool_percent = 100
; temperature_C = 250
; keep_warm_C = 180
; first_layer_C = 255
; bed_C = 80
; chamber_C = 50
; preheat_strategy = 1
; flow_min_mm3_per_s = 0.01
; flow_max_mm3_per_s = 10
; flow_cool_mm3_per_s = 1
; destring_length = 1
; preload_factor = 0
; matl_viscosity_over_elasticity_us = 0
; last_mm_at_perim_speed = 25
; destring_min_mm = 1
; destring_trigger_mm = 100
; preload_speed_mm_per_s = 20
; destring_speed_mm_per_s = 20
; Z_lift_mm = 0
; Z_lift_arc = 0
; min_layer_time_s = 10
; wipe_mm = 10
; cost_per_cm3 = 0
; flowrate_tweak = 1
; fiber_dia_mm = 3
; shrink_percent_xy = 0
; shrink_percent_y = 0
; shrink_percent_z = 0
; purge_vol_mm3 = 42
; purge_color_strength = 0.5
; color = 0
;
; *** Style Settings ***
;
; style_name = sample style
; profile_date = 2020-10-22 17:05:17
; quality_percentage = 50
; layer_thickness_mm = 0.25
; max_layer_thickness_mm = 0
; first_layer_thickness_mm = 0
; unsupported_stepover_mm = 0.25
; supported_stepover_mm = 0.25
; extrusion_width_mm = 0.5
; num_loops = 3
; skin_thickness_mm = 0.8
; infill_extrusion_width = 0.5
; infill_density_denominator = 4
; stacked_layers = 1
; use_corners = 1
; force_joint_layers = 0
; ironing_mode = 0
; loops_insideout = 0
; join_perimeter_loop = 1
; infill_st_oct_rnd = 1
; travel_mode = 1
; inset_surface_xy_mm = 0
; seam_jitter_degrees = 0
; seam_depth_scaler = 1
; seam_gap_scaler = 1
; seam_angle_degrees = 45
; crowning_threshold_mm = 1
; wipe_offset_mm = 0
; open_base = 0
; monotonic_sweep = 0
;
; *** Support Settings ***
;
; support_name = sample support
; profile_date = 2020-10-22 17:05:17
; support_sheathe = 0
; support_density = 3
; use_lower_interface = 1
; solid_interface = 0
; support_inflate_mm = 0
; support_gap_mm = -100
; interface_gap_mm = -75
; support_angle_deg = 45
; support_z_max_mm = -1
; support_z_min_mm = 0
; sheathe_z_max_mm = -1
; purge_width_gain = 1.5
; raft_mode = 0
; prime_pillar_mode = 0
; pillar_placement = 3
; raft_inflate_mm = 2
; raft_hi_stride_mm = 1.5
; raft_hi_thick_mm = 0.25
; raft_hi_width_mm = 0.35
; raft_lo_stride_mm = 2.5
; raft_lo_thick_mm = 0.25
; raft_lo_width_mm = 0.5
; brim_mm = 0
; brim_ht_mm = 0
; brim_gap_mm = 0
; brim_fillet = 1
; interface_band_mm = 2
; interface_Z_gap_mm = 0
; first_Z_gap_mm = 0
; raft_interface_layers = 0
; raft_interface_bond = 0
; brim_latch = 0
; interface_angle_deg = 30
; interface_stride_mm = 1
; interface_width_mm = 0.5
; interface_1st_layer_width_mm = 0.5
;
; *** Actual Slicing Settings As Used ***
;
; layer_thickness_mm = 0.25
; max_layer_thickness_mm = 0
; first_layer_thickness_mm = 0
; unsupported_stepover_mm = 0.25
; supported_stepover_mm = 0.25
; extrusion_width = 0.5
; num_ISOs = 3
; wall_thickness = 0.8
; infill_style = 5
; support_style = 3
; use_lower_interface = 1
; solid_interface = 0
; support_angle = 44.9
; destring_min_mm = 1
; stacked_infill_layers = 1
; raft_style = 0
; raft_sees_prime_paths = 0
; raft_extra_interface_layers = 0
; raft_extra_interface_bond = 0
; brim_latch = 0
; raft_hi_stride_mm = 0
; raft_lo_stride_mm = 0
; oversample_res_mm = 0.125
; crowning_threshold_mm = 1
; wipe_offset_mm = 0
; loops_insideout = 0
; join_perimeter_loop = 1
; solid_loop_overlap_fraction = 0.1
; inflate_raft_mm = 0
; inflate_support_mm = 0
; model_support_gap_mm = 0.5
; model_interface_gap_mm = 0.375
; brim_mm = 0
; brim_ht_mm = 0
; brim_gap_mm = 0
; infill_st_oct_rnd = 1
; travel_mode = 1
; support_Z_max_mm = 1e+20
; support_Z_min_mm = 0
; support_sheathe_off_main_both_int = 0
; inset_surface_xy_mm = 0
; seam_jitter_degrees = 0
; seam_depth_scaler = 1
; seam_gap_scaler = 1
; seam_angle_degrees = 45
; seam_use_corners = 1
; force_joint_layers = 0
; ironing_mode = 0
; interface_band_mm = 2
; skip_N_support_layers = 0
; interface_angle_deg = 30
; interface_stride_mm = 1
; printer_z_step_mm = 0
; model_and_int_share_ext = 1
; Speed vs Quality = 0.50
; Top Surface Speed = 11.25
; Perimeter Speed = 15.00
; Loops Speed = 30.00
; Solid Speed = 37.50
; Sparse Speed = 45.00
;
; *** Estimate all extruders at 0.5 [s], Slowing 0.050x to 9.7 [s] ***
; *** G-code Prefix ***
;
; [mm] mode
G21
; absolute mode
G90
; absolute Extruder mode
M82
; home the axes
G28
; heat the bed
M140 S80
;
; *** Main G-code ***
;
; Reset extruder pos
G92 E0
; BEGIN_LAYER_OBJECT z=0.250 z_thickness=0.250
;
; *** Selecting and Warming Extruder 1 to 255 C ***
; Select extruder, warm, purge
; BfB-style
M104 S255
M542
M551 P32000 S900
M543
; 5D-style
T0
M104 S255
G1 X0.033 Y0.230 F6000
M109 S255
;
G92 E0
;
; Perimeter Length = 1.405379
; fan %*255
M106 S255
;
; 'Perimeter Path', 0.0 [feed mm/s], 0.8 [head mm/s]
G1 X0.033 Y0.23 Z0.25 E0 F9000
; 'Destring Prime'
G1 E1 F1200
; Path end 25.00 [mm] slowed to Perim speed
; head speed 0.750000, filament speed 0.013263, preload 0.000000
G1 X-0.053 Y0.23 E1.00153 F45
G1 X-0.178 Y0.232 E1.00375
G1 X-0.21 Y0.223 E1.00433
G1 X-0.234 Y0.2 E1.00491
G1 X-0.242 Y0.168 E1.0055
G1 X-0.237 Y-0.172 E1.01151
G1 X-0.229 Y-0.203 E1.01208
G1 X-0.205 Y-0.225 E1.01266
G1 X-0.174 Y-0.233 E1.01323
G1 X-0.083 Y-0.231 E1.01483
G1 X0.185 Y-0.237 E1.01958
G1 X0.21 Y-0.231 E1.02002
G1 X0.228 Y-0.213 E1.02047
G1 X0.234 Y-0.189 E1.02092
G1 X0.233 Y-0.12 E1.02213
G1 X0.23 Y-0.053 E1.02332
G1 X0.23 Y0.033 E1.02485
;
; 'Destring/Wipe/Jump Path', 0.0 [feed mm/s], 1.0 [head mm/s]
; 'Destring Suck'
G1 E0.02485 F1200
; head speed 1.000000, filament speed 0.000000, preload 0.000000
; Prepare for End-Of-Layer
G1 X-0.053 Y0.23 E0.02485 F60
G1 X-0.178 Y0.232 E0.02485
G1 X-0.21 Y0.223 E0.02485
G1 X-0.234 Y0.2 E0.02485
G1 X-0.242 Y0.168 E0.02485
G1 X-0.237 Y-0.172 E0.02485
G1 X-0.229 Y-0.203 E0.02485
G1 X-0.205 Y-0.225 E0.02485
G1 X-0.174 Y-0.233 E0.02485
G1 X-0.083 Y-0.231 E0.02485
G1 X0.185 Y-0.237 E0.02485
G1 X0.21 Y-0.231 E0.02485
G1 X0.228 Y-0.213 E0.02485
G1 X0.234 Y-0.189 E0.02485
G1 X0.233 Y-0.12 E0.02485
G1 X0.23 Y-0.053 E0.02485
G1 X0.23 Y0.033 E0.02485
;
; 'Travel/Ironing Path', 0.0 [feed mm/s], 150.0 [head mm/s]
G1 X0 Y0 E0.02485 F9000
; head speed 150.000000, filament speed 0.000000, preload 0.000000
; time estimate: pre = 3.670541, post = 3.661706
; Dwell time remaining = 6.338294
;
; Post-layer lift
G1 X0 Y0 Z0.5 E0.02485 F300
; END_LAYER_OBJECT z=0.250
; *** Estimate all extruders at 0.4 [s], Slowing 0.050x to 9.8 [s] ***
; Reset extruder pos
G92 E0
; BEGIN_LAYER_OBJECT z=0.500 z_thickness=0.250
;
; *** Cooling Same Extruder (1) to 250 C ***
; Guaranteed same extruder, but about to deselect, maybe retract before cooling down
; BfB-style
M104 S250
; 5D-style
M104 S250
;
G92 E0
;
; Perimeter Length = 1.405379
;
; 'Perimeter Path', 0.0 [feed mm/s], 0.8 [head mm/s]
G1 X0.033 Y0.23 Z0.5 E0 F9000
; 'Destring Prime'
G1 E1 F1200
; Path end 25.00 [mm] slowed to Perim speed
; head speed 0.750000, filament speed 0.013263, preload 0.000000
G1 X-0.053 Y0.23 E1.00153 F45
G1 X-0.178 Y0.232 E1.00375
G1 X-0.21 Y0.223 E1.00433
G1 X-0.234 Y0.2 E1.00491
G1 X-0.242 Y0.168 E1.0055
G1 X-0.237 Y-0.172 E1.01151
G1 X-0.229 Y-0.203 E1.01208
G1 X-0.205 Y-0.225 E1.01266
G1 X-0.174 Y-0.233 E1.01323
G1 X-0.083 Y-0.231 E1.01483
G1 X0.185 Y-0.237 E1.01958
G1 X0.21 Y-0.231 E1.02002
G1 X0.228 Y-0.213 E1.02047
G1 X0.234 Y-0.189 E1.02092
G1 X0.233 Y-0.12 E1.02213
G1 X0.23 Y-0.053 E1.02332
G1 X0.23 Y0.033 E1.02485
;
; 'Destring/Wipe/Jump Path', 0.0 [feed mm/s], 1.8 [head mm/s]
; 'Destring Suck'
G1 E0.02485 F1200
; head speed 1.750000, filament speed 0.000000, preload 0.000000
; Prepare for End-Of-Layer
G1 X-0.053 Y0.23 E0.02485 F105
G1 X-0.178 Y0.232 E0.02485
G1 X-0.21 Y0.223 E0.02485
G1 X-0.234 Y0.2 E0.02485
G1 X-0.242 Y0.168 E0.02485
G1 X-0.237 Y-0.172 E0.02485
G1 X-0.229 Y-0.203 E0.02485
G1 X-0.205 Y-0.225 E0.02485
G1 X-0.174 Y-0.233 E0.02485
G1 X-0.083 Y-0.231 E0.02485
G1 X0.185 Y-0.237 E0.02485
G1 X0.21 Y-0.231 E0.02485
G1 X0.228 Y-0.213 E0.02485
G1 X0.234 Y-0.189 E0.02485
G1 X0.233 Y-0.12 E0.02485
G1 X0.23 Y-0.053 E0.02485
G1 X0.23 Y0.033 E0.02485
;
; 'Travel/Ironing Path', 0.0 [feed mm/s], 150.0 [head mm/s]
G1 X0 Y0 E0.02485 F9000
; head speed 150.000000, filament speed 0.000000, preload 0.000000
; time estimate: pre = 2.961831, post = 2.948999
; Dwell time remaining = 7.051001
;
; Post-layer lift
G1 X0 Y0 Z0.75 E0.02485 F300
; END_LAYER_OBJECT z=0.500
; *** Estimate all extruders at 0.4 [s], Slowing 0.050x to 10.4 [s] ***
; Reset extruder pos
G92 E0
; BEGIN_LAYER_OBJECT z=0.750 z_thickness=0.250
; Perimeter Length = 1.405379
;
; 'Perimeter Path', 0.0 [feed mm/s], 0.8 [head mm/s]
G1 X0.033 Y0.23 Z0.75 E0 F9000
; 'Destring Prime'
G1 E1 F1200
; Path end 25.00 [mm] slowed to Perim speed
; head speed 0.750000, filament speed 0.013263, preload 0.000000
G1 X-0.053 Y0.23 E1.00153 F45
G1 X-0.178 Y0.232 E1.00375
G1 X-0.21 Y0.223 E1.00433
G1 X-0.234 Y0.2 E1.00491
G1 X-0.242 Y0.168 E1.0055
G1 X-0.237 Y-0.172 E1.01151
G1 X-0.229 Y-0.203 E1.01208
G1 X-0.205 Y-0.225 E1.01266
G1 X-0.174 Y-0.233 E1.01323
G1 X-0.083 Y-0.231 E1.01483
G1 X0.185 Y-0.237 E1.01958
G1 X0.21 Y-0.231 E1.02002
G1 X0.228 Y-0.213 E1.02047
G1 X0.234 Y-0.189 E1.02092
G1 X0.233 Y-0.12 E1.02213
G1 X0.23 Y-0.053 E1.02332
G1 X0.23 Y0.033 E1.02485
;
; 'Destring/Wipe/Jump Path', 0.0 [feed mm/s], 2.2 [head mm/s]
; 'Destring Suck'
G1 E0.02485 F1200
; head speed 2.250000, filament speed 0.000000, preload 0.000000
; Prepare for End-Of-Layer
G1 X-0.053 Y0.23 E0.02485 F135
G1 X-0.178 Y0.232 E0.02485
G1 X-0.21 Y0.223 E0.02485
G1 X-0.234 Y0.2 E0.02485
G1 X-0.242 Y0.168 E0.02485
G1 X-0.237 Y-0.172 E0.02485
G1 X-0.229 Y-0.203 E0.02485
G1 X-0.205 Y-0.225 E0.02485
G1 X-0.174 Y-0.233 E0.02485
G1 X-0.083 Y-0.231 E0.02485
G1 X0.185 Y-0.237 E0.02485
G1 X0.21 Y-0.231 E0.02485
G1 X0.228 Y-0.213 E0.02485
G1 X0.234 Y-0.189 E0.02485
G1 X0.233 Y-0.12 E0.02485
G1 X0.23 Y-0.053 E0.02485
G1 X0.23 Y0.033 E0.02485
;
; 'Travel/Ironing Path', 0.0 [feed mm/s], 150.0 [head mm/s]
G1 X0 Y0 E0.02485 F9000
; head speed 150.000000, filament speed 0.000000, preload 0.000000
; time estimate: pre = 2.753324, post = 2.737825
; Dwell time remaining = 7.262175
;
; Post-layer lift
G1 X0 Y0 Z1 E0.02485 F300
; END_LAYER_OBJECT z=0.750
; *** Estimate all extruders at 0.4 [s], Slowing 0.050x to 10.4 [s] ***
; Reset extruder pos
G92 E0
; BEGIN_LAYER_OBJECT z=1.000 z_thickness=0.250
; Perimeter Length = 1.405379
;
; 'Perimeter Path', 0.0 [feed mm/s], 0.8 [head mm/s]
G1 X0.033 Y0.23 Z1 E0 F9000
; 'Destring Prime'
G1 E1 F1200
; Path end 25.00 [mm] slowed to Perim speed
; head speed 0.750000, filament speed 0.013263, preload 0.000000
G1 X-0.053 Y0.23 E1.00153 F45
G1 X-0.178 Y0.232 E1.00375
G1 X-0.21 Y0.223 E1.00433
G1 X-0.234 Y0.2 E1.00491
G1 X-0.242 Y0.168 E1.0055
G1 X-0.237 Y-0.172 E1.01151
G1 X-0.229 Y-0.203 E1.01208
G1 X-0.205 Y-0.225 E1.01266
G1 X-0.174 Y-0.233 E1.01323
G1 X-0.083 Y-0.231 E1.01483
G1 X0.185 Y-0.237 E1.01958
G1 X0.21 Y-0.231 E1.02002
G1 X0.228 Y-0.213 E1.02047
G1 X0.234 Y-0.189 E1.02092
G1 X0.233 Y-0.12 E1.02213
G1 X0.23 Y-0.053 E1.02332
G1 X0.23 Y0.033 E1.02485
;
; 'Destring/Wipe/Jump Path', 0.0 [feed mm/s], 2.2 [head mm/s]
; 'Destring Suck'
G1 E0.02485 F1200
; head speed 2.250000, filament speed 0.000000, preload 0.000000
; Prepare for End-Of-Layer
G1 X-0.053 Y0.23 E0.02485 F135
G1 X-0.178 Y0.232 E0.02485
G1 X-0.21 Y0.223 E0.02485
G1 X-0.234 Y0.2 E0.02485
G1 X-0.242 Y0.168 E0.02485
G1 X-0.237 Y-0.172 E0.02485
G1 X-0.229 Y-0.203 E0.02485
G1 X-0.205 Y-0.225 E0.02485
G1 X-0.174 Y-0.233 E0.02485
G1 X-0.083 Y-0.231 E0.02485
G1 X0.185 Y-0.237 E0.02485
G1 X0.21 Y-0.231 E0.02485
G1 X0.228 Y-0.213 E0.02485
G1 X0.234 Y-0.189 E0.02485
G1 X0.233 Y-0.12 E0.02485
G1 X0.23 Y-0.053 E0.02485
G1 X0.23 Y0.033 E0.02485
;
; 'Travel/Ironing Path', 0.0 [feed mm/s], 150.0 [head mm/s]
G1 X0 Y0 E0.02485 F9000
; head speed 150.000000, filament speed 0.000000, preload 0.000000
; time estimate: pre = 2.753324, post = 2.737825
; Dwell time remaining = 7.262175
;
; Post-layer lift
G1 X0 Y0 Z1.5 E0.02485 F300
; END_LAYER_OBJECT z=1.000
;
; *** Cooling Extruder 1 to 0 C and Retiring ***
; Guaranteed same extruder, but about to deselect, maybe retract before cooling down
; BfB-style
M104 S0
; 5D-style
M104 S0
;
; fan off
M107
; *** G-code Postfix ***
;
; All used extruders are already 'Cooled' to 0
; turn off the bed & chamber
M140 S0
;
;
;
; Calculated-during-export Build Time: 1.83 minutes
; Estimated-in-GUI Build Time:         2.23 minutes
; Estimated-in-GUI Build Cost:         $0.00
;
; Filament used per extruder:
;    Ext #1  =     0.10 mm  (0.001 cm^3)
;
; *** Extrusion Time Breakdown ***
; * estimated time in [s]
; * before possibly slowing down for 'cool'
; * not including Z-travel
;
;	| Ext #1  | Path Type
;	========================================
;	| 0.0995153 | Jump Path                  |
;	| 0       | Pillar Path                |
;	> 0       > Raft Path                  >
;	| 0       | Support Interface Path     |
;	| 0       | Support (may Stack) Path   |
;	| 0.618176 | Perimeter Path             |
;	> 0       > Loop Path                  >
;	| 0       | Solid Path                 |
;	| 0       | Sparse Infill Path         |
;	| 0       | Stacked Sparse Infill Path |
;	> 1.08045 > Destring/Wipe/Jump Path    >
;	| 0       | Crown Path                 |
;	| 0       | Prime Pillar Path          |
;	| 0       | Purge Path                 |
;	> 0       > Travel/Ironing Path        >
;	| 0       | Pause Point                |
;	| 93.75   | Extruder Warm-Up           |
;	========================================
; Total estimated (pre-cool) minutes: 1.59
