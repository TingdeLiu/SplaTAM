import os

# ============================================================
# 手持模式 — Orbbec Gemini 336L + SplaTAM 在线 3D 高斯重建
#
# 使用方式：
#   python scripts/wheeltec_online_slam.py configs/hand/online_slam_gemini336l.py
#
# 手持操作建议：
#   - 移动速度 ≤ 0.3 m/s，保证帧间重叠
#   - 转弯时放慢，不要原地快速旋转
#   - 优先扫有纹理区域，避免大面积白墙
#   - Ctrl+C 结束后自动保存
# ============================================================

primary_device = "cuda:0"
seed = 0

scene_name = "handheld_scan_01"   # 修改此处区分不同次扫描
num_frames = -1                    # 不限帧数，Ctrl+C 手动结束

# ---- 分辨率 ----
# 彩色：1280×720（内参基准）
# 深度：848×480（双目原生，自动最近邻插值到 1280×720）
# 跟踪：640×360（彩色 ÷2，内参精确缩放）
# 建图：1280×720（彩色原生，全质量）
full_res_width           = 1280
full_res_height          = 720
downscale_factor         = 2.0    # 跟踪分辨率：640×360   2.0 
densify_downscale_factor = 1.0    # 建图分辨率：1280×720

# ---- SLAM 频率 ----
map_every            = 1    # 每帧建图
keyframe_every       = 5    # 每 5 帧选一个关键帧
mapping_window_size  = 20   # 手持视角变化大，窗口稍大
tracking_iters       = 40   # 手持抖动需更多迭代（小车用 25）
mapping_iters        = 25   # 略低保实时性

group_name = "Handheld_Gemini336L"
run_name   = f"{scene_name}_{seed}"

config = dict(
    workdir  = f"./experiments/{group_name}",
    run_name = run_name,
    overwrite = True,
    num_frames = num_frames,
    seed = seed,
    primary_device = primary_device,
    map_every           = map_every,
    keyframe_every      = keyframe_every,
    mapping_window_size = mapping_window_size,
    report_global_progress_every = 50,
    eval_every = 1,
    # 手持室内小场景：scene_radius = depth_far / ratio = 20/4 = 5m
    # 大空间（走廊/大厅）可改为 2（radius ≈ 10m）
    scene_radius_depth_ratio = 4,
    mean_sq_dist_method      = "projective",
    gaussian_distribution    = "isotropic",
    report_iter_progress     = False,
    load_checkpoint      = False,
    checkpoint_time_idx  = 0,
    save_checkpoints     = True,
    checkpoint_interval  = 50,   # 每 50 帧存一次断点
    use_wandb = False,

    # ---- 相机参数（内参由 camera_info 自动覆盖）----
    # 实测标定值 @ 1280×720（2025-12 wheeltec 小车实机）
    camera = dict(
        fx = 607.4463,
        fy = 607.3991,
        cx = 639.1863,
        cy = 361.7548,
        png_depth_scale = 1000.0,  # Orbbec 驱动深度单位：mm
        depth_near = 0.17,         # Gemini 336L 最近有效深度
        depth_far  = 20.0,         # 最大深度范围
    ),

    # ---- ROS2 话题 ----
    ros2 = dict(
        rgb_topic          = "/camera/color/image_raw",
        depth_topic        = "/camera/depth/image_raw",
        camera_info_topic  = "/camera/color/camera_info",
        odom_topic         = "/odom",
        queue_size         = 10,
        use_odom_init      = False,           # 手持无轮式里程计
        use_imu_for_propagation = True,       # IMU 辅助旋转初始化（手持必开）
        imu_topic          = "/camera/gyro_accel/sample",
    ),
    use_imu_for_propagation = True,

    # ---- 数据尺寸 ----
    data = dict(
        dataset_name  = "wheeltec",
        basedir       = f"./experiments/Handheld_Gemini336L",
        sequence      = scene_name,
        downscale_factor         = downscale_factor,
        densify_downscale_factor = densify_downscale_factor,
        desired_image_height = int(full_res_height // downscale_factor),           # 360
        desired_image_width  = int(full_res_width  // downscale_factor),           # 640
        densification_image_height = int(full_res_height // densify_downscale_factor),  # 720
        densification_image_width  = int(full_res_width  // densify_downscale_factor),  # 1280
        start = 0,
        end   = -1,
        stride = 1,
        num_frames = num_frames,
    ),

    # ---- 跟踪 ----
    tracking = dict(
        use_gt_poses = False,
        forward_prop = True,              # 常速度模型 + IMU 共同初始化
        visualize_tracking_loss = False,
        num_iters = tracking_iters,
        use_sil_for_loss = True,
        sil_thres  = 0.99,
        use_l1     = True,
        use_depth_loss_thres    = True,
        depth_loss_thres        = 20000,
        ignore_outlier_depth_loss = True,  # 双目远距噪声大，必开
        use_uncertainty_for_loss_mask = False,
        use_uncertainty_for_loss      = False,
        use_chamfer = False,
        loss_weights = dict(
            im    = 0.5,
            depth = 1.0,   # 双目噪声比结构光大，不宜过高
        ),
        lrs = dict(
            means3D         = 0.0,
            rgb_colors      = 0.0,
            unnorm_rotations= 0.0,
            logit_opacities = 0.0,
            log_scales      = 0.0,
            cam_unnorm_rots = 0.0015,  # 手持旋转快，步长稍大
            cam_trans       = 0.005,   # 手持平移快，步长稍大
        ),
    ),

    # ---- 建图 ----
    mapping = dict(
        num_iters          = mapping_iters,
        add_new_gaussians  = True,
        sil_thres          = 0.5,
        use_l1             = True,
        use_sil_for_loss   = False,
        ignore_outlier_depth_loss     = True,
        use_uncertainty_for_loss_mask = False,
        use_uncertainty_for_loss      = False,
        use_chamfer = False,
        loss_weights = dict(
            im    = 0.5,
            depth = 1.0,
        ),
        lrs = dict(
            means3D          = 0.0001,
            rgb_colors       = 0.0025,
            unnorm_rotations = 0.001,
            logit_opacities  = 0.05,
            log_scales       = 0.001,
            cam_unnorm_rots  = 0.0,
            cam_trans        = 0.0,
        ),
        prune_gaussians = True,
        pruning_dict = dict(
            start_after                   = 0,
            remove_big_after              = 0,
            stop_after                    = 15,
            prune_every                   = 15,
            removal_opacity_threshold     = 0.01,
            final_removal_opacity_threshold = 0.01,
            reset_opacities               = False,
            reset_opacities_every         = 500,
        ),
        use_gaussian_splatting_densification = False,
        densify_dict = dict(
            start_after                   = 500,
            remove_big_after              = 3000,
            stop_after                    = 5000,
            densify_every                 = 100,
            grad_thresh                   = 0.0002,
            num_to_split_into             = 2,
            removal_opacity_threshold     = 0.01,
            final_removal_opacity_threshold = 0.01,
            reset_opacities_every         = 3000,
        ),
    ),

    # ---- 可视化 ----
    viz = dict(
        render_mode  = 'color',
        offset_first_viz_cam = True,
        show_sil     = False,
        visualize_cams = True,
        viz_w = 640, viz_h = 360,
        viz_near = 0.01, viz_far = 20.0,
        view_scale = 2,
        viz_fps    = 5,
        enter_interactive_post_online = True,
    ),
)
