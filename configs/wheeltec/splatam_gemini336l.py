import os
from os.path import join as p_join

# ============================================================
# Wheeltec + Orbbec Gemini 336L — Offline SLAM Config
# Use after converting a ROS2 bag with wheeltec_rosbag_to_splatam.py
#
# Camera specs:
#   - Stereo depth, 850nm IR
#   - Depth range: 0.17–20m (optimal 0.25–6m)
#   - Max resolution: 1280×800
# ============================================================

# Scene name: must match subdirectory under basedir
scene_name = "gemini_scene_01"

primary_device = "cuda:0"
seed = 0

map_every = 1
keyframe_every = 5
mapping_window_size = 24  # Larger window for offline (more GPU memory available)
tracking_iters = 50
mapping_iters = 60

group_name = "Wheeltec_Gemini336L"
run_name = f"{scene_name}_{seed}"

config = dict(
    workdir=f"./experiments/{group_name}",
    run_name=run_name,
    seed=seed,
    primary_device=primary_device,
    map_every=map_every,
    keyframe_every=keyframe_every,
    mapping_window_size=mapping_window_size,
    report_global_progress_every=50,
    eval_every=5,
    scene_radius_depth_ratio=3,
    mean_sq_dist_method="projective",
    gaussian_distribution="isotropic",
    report_iter_progress=False,
    load_checkpoint=False,
    checkpoint_time_idx=0,
    save_checkpoints=True,
    checkpoint_interval=100,
    use_wandb=False,
    wandb=dict(
        entity="your_entity",
        project="SplaTAM_Wheeltec",
        group=group_name,
        name=run_name,
        save_qual=False,
        eval_save_qual=True,
    ),
    data=dict(
        basedir="./data/wheeltec_gemini",
        gradslam_data_cfg="./configs/data/wheeltec.yaml",
        sequence=scene_name,
        # Color: 1280×720; Depth: 848×480 (upsampled to 1280×720 for densification)
        # Tracking at 640×360 (color ÷2) keeps intrinsics scaling exact.
        desired_image_height=360,
        desired_image_width=640,
        start=0,
        end=-1,
        stride=1,
        num_frames=-1,
    ),
    tracking=dict(
        use_gt_poses=False,
        forward_prop=True,
        num_iters=tracking_iters,
        use_sil_for_loss=True,
        sil_thres=0.99,
        use_l1=True,
        ignore_outlier_depth_loss=True,
        loss_weights=dict(
            im=0.5,
            depth=1.0,
        ),
        lrs=dict(
            means3D=0.0,
            rgb_colors=0.0,
            unnorm_rotations=0.0,
            logit_opacities=0.0,
            log_scales=0.0,
            cam_unnorm_rots=0.0005,
            cam_trans=0.002,
        ),
    ),
    mapping=dict(
        num_iters=mapping_iters,
        add_new_gaussians=True,
        sil_thres=0.5,
        use_l1=True,
        use_sil_for_loss=False,
        ignore_outlier_depth_loss=True,
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
        viz_w=640, viz_h=360,
        viz_near=0.01, viz_far=20.0,
        view_scale=2,
        viz_fps=5,
        enter_interactive_post_online=True,
    ),
)
