import os
from os.path import join as p_join

# ============================================================
# Wheeltec + Astra S — Online (Real-time) SLAM Config
# Optimized for Jetson Orin NX 16GB
# ============================================================

primary_device = "cuda:0"
seed = 0

scene_name = "online_office"
num_frames = 500  # Maximum frames to process (set -1 for unlimited)

# Astra S native resolution: 640x480
# Tracking uses half-res for speed on Jetson
full_res_width = 640
full_res_height = 480
downscale_factor = 2.0        # Tracking at 320x240
densify_downscale_factor = 1.0  # Densification at 640x480

# SLAM frequency parameters
map_every = 1           # Map every frame
keyframe_every = 5      # Keyframe every 5th frame
mapping_window_size = 16  # Smaller window for Jetson memory
tracking_iters = 30      # Fewer iters for real-time on Jetson
mapping_iters = 30       # Fewer iters for real-time on Jetson

group_name = "Wheeltec_Online"
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
    scene_radius_depth_ratio=3,
    mean_sq_dist_method="projective",
    gaussian_distribution="isotropic",
    report_iter_progress=False,
    load_checkpoint=False,
    checkpoint_time_idx=0,
    save_checkpoints=True,
    checkpoint_interval=50,
    use_wandb=False,
    # Astra S camera intrinsics (will be overridden by camera_info if available)
    camera=dict(
        fx=570.3,
        fy=570.3,
        cx=319.5,
        cy=239.5,
        png_depth_scale=1000.0,  # Astra S depth in mm
        depth_near=0.4,
        depth_far=4.0,
    ),
    # ROS2 topic configuration
    ros2=dict(
        rgb_topic="/camera/color/image_raw",
        depth_topic="/camera/depth/image_raw",
        camera_info_topic="/camera/color/camera_info",
        odom_topic="/odom",
        queue_size=10,
        use_odom_init=True,  # Use odometry for pose initialization
    ),
    data=dict(
        dataset_name="wheeltec",
        basedir=f"./experiments/{group_name}",
        sequence=scene_name,
        downscale_factor=downscale_factor,
        densify_downscale_factor=densify_downscale_factor,
        desired_image_height=int(full_res_height // downscale_factor),
        desired_image_width=int(full_res_width // downscale_factor),
        densification_image_height=int(full_res_height // densify_downscale_factor),
        densification_image_width=int(full_res_width // densify_downscale_factor),
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
        depth_loss_thres=20000,
        ignore_outlier_depth_loss=True,  # Important for noisy Astra S depth
        use_uncertainty_for_loss_mask=False,
        use_uncertainty_for_loss=False,
        use_chamfer=False,
        loss_weights=dict(
            im=0.5,
            depth=1.5,  # Higher depth weight for structured-light sensor
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
        sil_thres=0.5,
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
            stop_after=15,
            prune_every=15,
            removal_opacity_threshold=0.01,
            final_removal_opacity_threshold=0.01,
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
        viz_w=640, viz_h=480,
        viz_near=0.01, viz_far=4.0,
        view_scale=2,
        viz_fps=5,
        enter_interactive_post_online=True,
    ),
)
