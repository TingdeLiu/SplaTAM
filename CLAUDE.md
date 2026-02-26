# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SplaTAM is a Dense RGB-D SLAM system that uses 3D Gaussian Splatting for simultaneous localization and mapping. It combines camera tracking and scene reconstruction using differentiable rendering of 3D Gaussians.

## Environment Setup

### Standard Installation (Recommended)
```bash
conda create -n splatam python=3.10
conda activate splatam
conda install -c "nvidia/label/cuda-11.6.0" cuda-toolkit
conda install pytorch==1.12.1 torchvision==0.13.1 torchaudio==0.12.1 cudatoolkit=11.6 -c pytorch -c conda-forge
pip install -r requirements.txt
```

**Note**: While Torch 1.12.1 & CUDA 11.6 are benchmarked, the code also works with newer versions like Torch 2.3.0 & CUDA 12.1.

### Docker Setup
```bash
docker pull nkeetha/splatam:v1
bash bash_scripts/start_docker.bash
cd /SplaTAM/
pip install virtualenv --user
mkdir venv
cd venv
virtualenv --system-site-packages splatam
source ./splatam/bin/activate
pip install -r venv_requirements.txt
```

## Running SplaTAM

### Main SLAM Pipeline
```bash
# Run SplaTAM on a dataset
python scripts/splatam.py configs/<dataset>/splatam.py

# Examples:
python scripts/splatam.py configs/replica/splatam.py
python scripts/splatam.py configs/tum/splatam.py
python scripts/splatam.py configs/scannet/splatam.py
```

### Visualization
```bash
# Visualize final reconstruction (interactive)
python viz_scripts/final_recon.py configs/<dataset>/splatam.py

# Visualize reconstruction online
python viz_scripts/online_recon.py configs/<dataset>/splatam.py

# Export to PLY format
python scripts/export_ply.py configs/<dataset>/splatam.py
```

### Post-Processing
```bash
# Run 3D Gaussian Splatting optimization on SplaTAM reconstruction
python scripts/post_splatam_opt.py configs/<dataset>/post_splatam_opt.py

# Run 3D Gaussian Splatting with ground truth poses
python scripts/gaussian_splatting.py configs/<dataset>/gaussian_splatting.py

# Evaluate novel view synthesis
python scripts/eval_novel_view.py configs/<dataset>/eval_novel_view.py
```

### iPhone/Online Demo
```bash
# Online demo with NeRFCapture app
bash bash_scripts/online_demo.bash configs/iphone/online_demo.py

# Offline processing of captured dataset
bash bash_scripts/nerfcapture.bash configs/iphone/nerfcapture.py

# Dataset collection only
bash bash_scripts/nerfcapture2dataset.bash configs/iphone/dataset.py
```

## Dataset Setup

Download datasets using provided scripts:
```bash
bash bash_scripts/download_replica.sh
bash bash_scripts/download_tum.sh
bash bash_scripts/download_replicav2.sh
```

Default data directory is `./data`. Update `input_folder` in config files if stored elsewhere.

## Architecture

### Core Pipeline (scripts/splatam.py)

The SLAM system operates in two alternating phases:

**1. Tracking Phase**: Estimates camera pose for current frame
- Uses only camera pose parameters (cam_unnorm_rots, cam_trans) for optimization
- Gaussians remain fixed during tracking
- Renders depth and RGB from estimated pose
- Optimizes pose to minimize photometric and depth errors
- Optional forward propagation using constant velocity model

**2. Mapping Phase**: Updates 3D Gaussian representation
- Optimizes Gaussian parameters (means3D, rgb_colors, unnorm_rotations, logit_opacities, log_scales)
- Uses keyframe-based optimization with overlap-based selection
- Camera poses remain fixed during mapping (unless doing BA)
- Performs densification by adding new Gaussians based on silhouette
- Optional pruning and gradient-based densification

### Key Components

**3D Gaussian Representation** (utils/slam_helpers.py, utils/slam_external.py):
- Each Gaussian has: 3D position (means3D), color (rgb_colors), rotation (unnorm_rotations), opacity (logit_opacities), scale (log_scales)
- Two distributions supported: isotropic (spherical) or anisotropic (ellipsoidal)
- Gaussians are initialized from RGB-D point clouds
- Scale initialized based on projective geometry: `scale = depth / focal_length`

**Differentiable Rendering** (diff-gaussian-rasterization):
- External dependency: custom Gaussian rasterizer with depth output
- Renders RGB, depth, and silhouette from Gaussian representation
- Provides gradients for optimization
- Located in `diff-gaussian-rasterization-w-depth.git` submodule

**Camera Pose Representation**:
- Poses stored relative to first frame
- Parameterized as quaternion rotation + translation
- Single trajectory tensor tracks all frames: `cam_unnorm_rots[..., time_idx]`, `cam_trans[..., time_idx]`

**Dataset Loaders** (datasets/gradslam_datasets/):
- Base class: `GradSLAMDataset`
- Supported datasets: Replica, ReplicaV2, TUM-RGBD, ScanNet, ScanNet++, ICL, Azure Kinect, RealSense, Record3D, NeRFCapture, Ai2Thor
- Datasets return: (color, depth, intrinsics, pose) tuples
- Support for different resolutions for tracking vs. densification

**Keyframe Selection** (utils/keyframe_selection.py):
- Overlap-based selection for mapping optimization
- Maintains sliding window of most relevant keyframes
- Current frame always included in mapping

**Loss Functions** (scripts/splatam.py:get_loss):
- Tracking: L1 depth + L1 RGB (with optional silhouette masking)
- Mapping: L1 depth + (0.8 * L1 + 0.2 * SSIM) RGB
- Optional outlier depth rejection using median-based thresholding
- Silhouette thresholding to handle empty space

### Configuration System

Configs are Python files (not YAML) located in `configs/<dataset>/`:
- Scene selection and parameters
- Tracking/mapping iteration counts and learning rates
- Loss weights
- Densification/pruning parameters
- WandB logging settings
- Separate resolution settings for tracking/mapping/densification

Example config structure:
```python
config = dict(
    workdir="./experiments/<group_name>",
    run_name="<scene>_<seed>",
    primary_device="cuda:0",
    map_every=1,  # Mapping frequency
    keyframe_every=5,  # Keyframe selection frequency
    mapping_window_size=24,  # Number of keyframes for mapping
    tracking=dict(
        num_iters=40,
        use_gt_poses=False,
        lrs=dict(cam_unnorm_rots=0.0004, cam_trans=0.002, ...),
        loss_weights=dict(im=0.5, depth=1.0),
    ),
    mapping=dict(
        num_iters=60,
        add_new_gaussians=True,
        prune_gaussians=True,
        lrs=dict(means3D=0.0001, rgb_colors=0.0025, ...),
    ),
    data=dict(
        basedir="./data/<Dataset>",
        sequence="<scene_name>",
        desired_image_height=680,
        desired_image_width=1200,
    ),
)
```

### Helper Modules

**utils/slam_helpers.py**: Transform operations, loss functions, quaternion math
**utils/slam_external.py**: Build rotation matrices, pruning, densification
**utils/recon_helpers.py**: Camera setup for Gaussian rasterization
**utils/eval_helpers.py**: Trajectory evaluation, rendering metrics, progress reporting
**utils/common_utils.py**: Seeding, parameter saving/loading
**utils/gs_helpers.py**: Gaussian Splatting-specific helpers (for scripts/gaussian_splatting.py)

## Checkpointing

```python
# Enable checkpointing in config
config['save_checkpoints'] = True
config['checkpoint_interval'] = 100  # Save every 100 frames

# Load from checkpoint
config['load_checkpoint'] = True
config['checkpoint_time_idx'] = 300  # Resume from frame 300
```

Checkpoints saved as: `experiments/<run_name>/params<time_idx>.npz`

## WandB Integration

Configure in config file:
```python
config['use_wandb'] = True
config['wandb'] = dict(
    entity="<your_entity>",
    project="SplaTAM",
    group="<dataset_name>",
    name="<run_name>",
    save_qual=False,  # Save qualitative results during run
    eval_save_qual=True,  # Save qualitative results at evaluation
)
```

## Important Implementation Details

### Coordinate Systems
- World coordinates relative to first frame
- Camera poses are world-to-camera (w2c) transformations
- Intrinsics follow OpenCV convention: [fx, fy, cx, cy]

### Gaussian Initialization
- Initial Gaussians created from first frame RGB-D data
- Mask out invalid depth values (depth > 0)
- Mean squared distance computed using projective geometry
- New Gaussians added when: silhouette < threshold OR depth_error > threshold

### Tracking Initialization
- Frame 0: Identity pose
- Frame 1+: Copy previous pose or use constant velocity model (if forward_prop=True)
- Velocity model: `new_pose = prev_pose + (prev_pose - prev_prev_pose)`

### Optimization Details
- Separate optimizers for tracking (camera only) and mapping (Gaussians)
- Learning rates specified per parameter type in config
- Tracking keeps best candidate pose across iterations (minimum loss)
- Mapping randomly samples from selected keyframes each iteration

### Resolution Handling
- Can use different resolutions for tracking, mapping, and densification
- Set `tracking_image_height/width`, `densification_image_height/width` in data config
- Useful for balancing speed vs. quality

## Batch Processing

Use bash scripts in `configs/<dataset>/` for running multiple scenes:
```bash
bash configs/replica/replica.bash
bash configs/tum/tum.bash
bash configs/scannet/scannet.bash
bash configs/scannetpp/scannetpp.bash
```

## Code Style Notes

- Dataset loaders extend `GradSLAMDataset` base class
- All optimization uses PyTorch Adam optimizer
- Parameters stored as `torch.nn.Parameter` objects
- Use `.detach()` when parameters shouldn't receive gradients
- Configs loaded via `SourceFileLoader` to execute Python config files
