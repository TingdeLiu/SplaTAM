import os
from os.path import join as p_join

# ============================================================
# Wheeltec + Orbbec Gemini 336L — Online (Real-time) SLAM Config
# Optimized for Jetson Orin NX 16GB
#
# Camera specs:
#   - Stereo depth, 850nm IR
#   - Depth range: 0.17–20m (optimal 0.25–6m)
#   - Max resolution: 1280×800 @ 30fps (depth), 1280×800 @ 60fps (RGB)
#   - ROS2 topics identical to Astra S driver
# ============================================================

primary_device = "cuda:0"
seed = 0

scene_name = "online_office"
num_frames = 500  # Set to -1 for unlimited

# Color: 1280×720 (intrinsics reference resolution)
# Depth: 848×480 (stereo native, upsampled to color res for densification)
# Tracking at half color-res (640×360) keeps intrinsics scaling exact.
# Densification at full color-res (1280×720); depth is nearest-neighbor
# upsampled from 848×480 — no interpolation artifacts.
full_res_width = 1280
full_res_height = 720
downscale_factor = 2.0          # Tracking at 640×360
densify_downscale_factor = 2.0  # Densification at 640×360 (was 1.0 @ 1280×720, 4x fewer gaussians)

# SLAM frequency
map_every = 5         # was 2 → less frequent mapping
keyframe_every = 5
mapping_window_size = 16  # Keep small for Jetson memory
tracking_iters = 10   # was 30 → 3x faster tracking
mapping_iters = 10    # was 30 → 3x faster mapping

group_name = "Wheeltec_Gemini336L"
run_name = f"{scene_name}_{seed}"

config = dict(
    workdir=f"./experiments/{group_name}",
    run_name=run_name,
    overwrite=True,
    num_frames=num_frames,
    seed=seed,
    primary_device=primary_device,
    map_every=map_every,
    keyframe_every=keyframe_every,
    mapping_window_size=mapping_window_size,
    report_global_progress_every=50,
    eval_every=1,
    # Stereo depth at 20m: scene radius = 20/3 ≈ 6.7m.
    # Decrease to 2 for large outdoor/corridor scenes (radius ≈ 10m).
    scene_radius_depth_ratio=3,
    mean_sq_dist_method="projective",
    gaussian_distribution="isotropic",
    report_iter_progress=False,
    load_checkpoint=False,
    checkpoint_time_idx=0,
    save_checkpoints=True,
    checkpoint_interval=50,
    use_wandb=False,
    # Gemini 336L calibrated intrinsics at 1280×720 (measured on wheeltec unit, 2025-12).
    # Overridden automatically by /camera/color/camera_info in online mode.
    camera=dict(
        fx=607.4463,
        fy=607.3991,
        cx=639.1863,
        cy=361.7548,
        png_depth_scale=1000.0,  # Orbbec driver: depth in mm
        depth_near=0.17,         # Gemini 336L minimum depth
        depth_far=20.0,          # Maximum usable range
    ),
    # ROS2 topics (Orbbec standard, identical to Astra S for RGB-D)
    ros2=dict(
        rgb_topic="/camera/color/image_raw",
        depth_topic="/camera/depth/image_raw",
        camera_info_topic="/camera/color/camera_info",
        odom_topic="/odom",
        queue_size=10,
        use_odom_init=True,
        # Gemini 336L IMU — gyroscope-aided rotation initialization
        use_imu_for_propagation=True,
        imu_topic="/camera/gyro_accel/sample",
    ),
    use_imu_for_propagation=True,
    data=dict(
        dataset_name="wheeltec",
        basedir=f"./experiments/{group_name}",
        sequence=scene_name,
        downscale_factor=downscale_factor,
        densify_downscale_factor=densify_downscale_factor,
        desired_image_height=int(full_res_height // downscale_factor),       # 360
        desired_image_width=int(full_res_width // downscale_factor),          # 640
        densification_image_height=int(full_res_height // densify_downscale_factor),  # 360
        densification_image_width=int(full_res_width // densify_downscale_factor),    # 640
        start=0,
        end=-1,
        stride=1,
        num_frames=num_frames,
    ),
    tracking=dict(
        use_gt_poses=False,
        forward_prop=True,
        visualize_tracking_loss=False,
        num_iters=tracking_iters,
        use_sil_for_loss=True,
        sil_thres=0.99,
        use_l1=True,
        use_depth_loss_thres=True,
        depth_loss_thres=50000,  # was 20000 → easier to satisfy, avoids iter doubling
        # Stereo depth noise grows with distance; outlier rejection is important
        # at long range (beyond ~6m optimal).
        ignore_outlier_depth_loss=True,
        use_uncertainty_for_loss_mask=False,
        use_uncertainty_for_loss=False,
        use_chamfer=False,
        loss_weights=dict(
            im=0.5,
            # Slightly lower depth weight than structured-light (was 1.5):
            # stereo noise increases quadratically with depth.
            depth=1.0,
        ),
        lrs=dict(
            means3D=0.0,
            rgb_colors=0.0,
            unnorm_rotations=0.0,
            logit_opacities=0.0,
            log_scales=0.0,
            cam_unnorm_rots=0.001,
            cam_trans=0.004,
        ),
    ),
    mapping=dict(
        num_iters=mapping_iters,
        add_new_gaussians=True,
        sil_thres=0.9,  # was 0.5 → stricter threshold, fewer spurious gaussians added
        use_l1=True,
        use_sil_for_loss=False,
        ignore_outlier_depth_loss=True,
        use_uncertainty_for_loss_mask=False,
        use_uncertainty_for_loss=False,
        use_chamfer=False,
        loss_weights=dict(
            im=0.5,
            depth=1.0,
        ),
        lrs=dict(
            means3D=0.0001,
            rgb_colors=0.0025,
            unnorm_rotations=0.001,
            logit_opacities=0.05,
            log_scales=0.001,
            cam_unnorm_rots=0.0000,
            cam_trans=0.0000,
        ),
        prune_gaussians=True,
        pruning_dict=dict(
            start_after=0,
            remove_big_after=0,
            stop_after=100000,           # was 15 → never stop pruning
            prune_every=5,               # was 15 → prune more frequently
            removal_opacity_threshold=0.05,        # was 0.01 → remove more low-quality gaussians
            final_removal_opacity_threshold=0.05,  # was 0.01
            reset_opacities=False,
            reset_opacities_every=500,
        ),
        use_gaussian_splatting_densification=False,
        densify_dict=dict(
            start_after=500,
            remove_big_after=3000,
            stop_after=5000,
            densify_every=100,
            grad_thresh=0.0002,
            num_to_split_into=2,
            removal_opacity_threshold=0.01,
            final_removal_opacity_threshold=0.01,
            reset_opacities_every=3000,
        ),
    ),
    viz=dict(
        render_mode='color',
        offset_first_viz_cam=True,
        show_sil=False,
        visualize_cams=True,
        viz_w=640, viz_h=360,
        viz_near=0.01, viz_far=20.0,
        view_scale=2,
        viz_fps=5,
        enter_interactive_post_online=True,
    ),
)
