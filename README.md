<!-- PROJECT LOGO -->

<p align="center">
  <h1 align="center">SplaTAM 实机部署指南 / Real-World Deployment Guide</h1>
  <p align="center">
    <a href="https://tingdeliu.github.io/"><strong>Tingde Liu</strong></a> · <a href="https://arxiv.org/pdf/2312.02126.pdf">Paper</a> · <a href="https://youtu.be/jWLI-OFp3qU">Video</a> · <a href="https://spla-tam.github.io/">Project Page</a>
  </p>
</p>

<p align="center">
  原项目地址：https://github.com/spla-tam/SplaTAM
</p>

<p align="center">
  <img src="./assets/1.gif" alt="SplaTAM demo" width="100%">
</p>

---

<details open style='padding: 10px; border-radius: 5px 30px 30px 5px; border: 1px solid #ddd;'>
  <summary>目录</summary>
  <ol>
    <li><a href="#概览">概览</a></li>
    <li><a href="#安装">安装</a></li>
    <li><a href="#演示">演示</a></li>
    <li><a href="#使用">使用</a></li>
    <li><a href="#数据下载">数据下载</a></li>
    <li><a href="#基准测试">基准测试</a></li>
    <li><a href="#致谢">致谢</a></li>
    <li><a href="#引用">引用</a></li>
    <li><a href="#开发者">开发者</a></li>
  </ol>
</details>

## 概览

本仓库是 SplaTAM (CVPR 2024) 在真实平台上的部署复现，在原版代码基础上扩展了多传感器与多场景支持。

**支持的传感器 / 平台**

| 传感器 | 平台 | 模式 | 指南 |
|--------|------|------|------|
| Orbbec Astra S | Wheeltec 小车（Jetson Orin NX）| 在线 / 离线 | [3d_rec_AstraS.md](./3d_rec_AstraS.md) |
| Orbbec Gemini 336L | 手持 / Wheeltec 小车 | 在线 / 离线 | [3d_rec_gemini336l.md](./3d_rec_gemini336l.md) |
| iPhone LiDAR | iPhone 12 Pro 及以上（NeRFCapture App）| 在线 / 离线 | [3d_rec_iphone.md](./3d_rec_iphone.md) |

**硬件平台**

- 机器人：Wheeltec senior_4wd_bs，Jetson Orin NX 16GB，ROS2 Humble
- 深度相机：Astra S（结构光 0.4–4m）、Gemini 336L（双目 0.17–20m）
- 手持：iPhone Pro 系列 LiDAR（NeRFCapture App 通过 WiFi）

**新增功能**

- 在线 SLAM：实时订阅 ROS2 话题，边采集边重建（`scripts/wheeltec_online_slam.py`）
- 离线 SLAM：录制 ROS2 bag → 转换 → 高质量重建
- ROS2 bag 转换：支持 ROS1/ROS2，自动提取 RGB-D 帧（`scripts/wheeltec_rosbag_to_splatam.py`）
- CloudCompare 点云导出：标准 RGB PLY（`scripts/export_ply_cloudcompare.py`）
- 多相机配置：`configs/wheeltec/`（小车）、`configs/hand/`（手持）、`configs/iphone/`（iPhone）

---

## 安装

推荐环境：Python 3.10，Torch 1.12.1 + CUDA 11.6（也兼容 Torch 2.3 + CUDA 12.1）。

```bash
conda create -n splatam python=3.10
conda activate splatam
conda install -c "nvidia/label/cuda-11.6.0" cuda-toolkit
conda install pytorch==1.12.1 torchvision==0.13.1 torchaudio==0.12.1 cudatoolkit=11.6 -c pytorch -c conda-forge
pip install -r requirements.txt
```

Windows 安装（Git Bash）：参考 [Issue#9 说明](https://github.com/spla-tam/SplaTAM/issues/9#issuecomment-1848348403)。

**Docker / Singularity**

```bash
docker pull nkeetha/splatam:v1
bash bash_scripts/start_docker.bash
cd /SplaTAM/
pip install virtualenv --user
mkdir venv && cd venv
virtualenv --system-site-packages splatam
source ./splatam/bin/activate
pip install -r venv_requirements.txt
```

Singularity 类似：

```bash
cd </path/to/singularity/folder/>
singularity pull splatam.sif docker://nkeetha/splatam:v1
singularity instance start --nv splatam.sif splatam
singularity run --nv instance://splatam
cd <path/to/SplaTAM/>
pip install virtualenv --user
mkdir venv && cd venv
virtualenv --system-site-packages splatam
source ./splatam/bin/activate
pip install -r venv_requirements.txt
```

---

## 演示

- 在线：iPhone/Apple LiDAR + NeRFCapture
  ```bash
  bash bash_scripts/online_demo.bash configs/iphone/online_demo.py
  ```
- 离线：采集后离线重建
  ```bash
  bash bash_scripts/nerfcapture.bash configs/iphone/nerfcapture.py
  ```
- 仅采集：只采集 iPhone 数据集
  ```bash
  bash bash_scripts/nerfcapture2dataset.bash configs/iphone/dataset.py
  ```

<p align="center">
  <img src="./assets/collage.gif" alt="examples" width="75%">
</p>

---

## 使用

以 iPhone 数据集为例（其他数据集同理修改路径）：

- 运行 SLAM
  ```bash
  python scripts/splatam.py configs/iphone/splatam.py
  ```
- 可视化最终重建
  ```bash
  python viz_scripts/final_recon.py configs/iphone/splatam.py
  ```
- 在线可视化
  ```bash
  python viz_scripts/online_recon.py configs/iphone/splatam.py
  ```
- 导出 PLY
  ```bash
  python scripts/export_ply.py configs/iphone/splatam.py
  ```
- 3D Gaussian Splatting 优化
  ```bash
  python scripts/post_splatam_opt.py configs/iphone/post_splatam_opt.py
  ```
- 使用真值位姿的 Splatting
  ```bash
  python scripts/gaussian_splatting.py configs/iphone/gaussian_splatting.py
  ```

---

## 数据下载

DATAROOT 默认为 `./data`，如存放在其他位置请在对应 config 中调整 `input_folder`。

- Replica
  ```bash
  bash bash_scripts/download_replica.sh
  ```
- TUM-RGBD
  ```bash
  bash bash_scripts/download_tum.sh
  ```
- ScanNet：官网申请下载，用官方脚本解出 color/depth/intrinsic/pose
- ScanNet++：按官网流程并使用我们的变体去畸变 [link](https://github.com/Nik-V9/scannetpp)
- Replica-V2：从 [vMAP](https://github.com/kxhit/vMAP) 获取

---

## 基准测试

- 建议开启 Weights & Biases：在 config 中设置 `wandb=True` 并填写 `entity`、`wandb_folder`
- 运行示例：
  - Replica `room0`
    ```bash
    python scripts/splatam.py configs/replica/splatam.py
    ```
  - TUM `freiburg1_desk`
    ```bash
    python scripts/splatam.py configs/tum/splatam.py
    ```
  - ScanNet `scene0000_00`
    ```bash
    python scripts/splatam.py configs/scannet/splatam.py
    ```
  - ScanNet++ `8b5caf3398`
    ```bash
    python scripts/splatam.py configs/scannetpp/splatam.py
    python scripts/eval_novel_view.py configs/scannetpp/eval_novel_view.py
    ```
  - ReplicaV2 `room0`
    ```bash
    python scripts/splatam.py configs/replica_v2/splatam.py
    python scripts/eval_novel_view.py configs/replica_v2/eval_novel_view.py
    ```

---

## 致谢

- 3D Gaussians: [Dynamic 3D Gaussians](https://github.com/JonathonLuiten/Dynamic3DGaussians), [3D Gaussian Splatting](https://github.com/graphdeco-inria/gaussian-splatting)
- Dataloaders: [GradSLAM & ConceptFusion](https://github.com/gradslam/gradslam/tree/conceptfusion)
- Baselines: [Nice-SLAM](https://github.com/cvg/nice-slam), [Point-SLAM](https://github.com/eriksandstroem/Point-SLAM)

## 引用

```bib
@inproceedings{keetha2024splatam,
        title={SplaTAM: Splat, Track & Map 3D Gaussians for Dense RGB-D SLAM},
        author={Keetha, Nikhil and Karhade, Jay and Jatavallabhula, Krishna Murthy and Yang, Gengshan and Scherer, Sebastian and Ramanan, Deva and Luiten, Jonathon},
        booktitle={Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition},
        year={2024}
      }
```

## 开发者

- [Nik-V9](https://github.com/Nik-V9) (Nikhil Keetha)
- [JayKarhade](https://github.com/JayKarhade) (Jay Karhade)

---
---

<details open style='padding: 10px; border-radius: 5px 30px 30px 5px; border: 1px solid #ddd;'>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#overview">Overview</a></li>
    <li><a href="#installation">Installation</a></li>
    <li><a href="#demo">Demo</a></li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#downloads">Downloads</a></li>
    <li><a href="#benchmarking">Benchmarking</a></li>
    <li><a href="#acknowledgement">Acknowledgement</a></li>
    <li><a href="#citation">Citation</a></li>
    <li><a href="#developers">Developers</a></li>
  </ol>
</details>

## Overview

This repo reproduces SplaTAM (CVPR 2024) on real platforms with extra sensor and scenario support.

**Supported sensors / platforms**

| Sensor | Platform | Mode | Guide |
|--------|----------|------|-------|
| Orbbec Astra S | Wheeltec rover (Jetson Orin NX) | Online / Offline | [3d_rec_AstraS.md](./3d_rec_AstraS.md) |
| Orbbec Gemini 336L | Handheld / Wheeltec rover | Online / Offline | [3d_rec_gemini336l.md](./3d_rec_gemini336l.md) |
| iPhone LiDAR | iPhone 12 Pro+ (NeRFCapture App) | Online / Offline | [3d_rec_iphone.md](./3d_rec_iphone.md) |

**Hardware**

- Rover: Wheeltec senior_4wd_bs, Jetson Orin NX 16GB, ROS2 Humble
- Depth: Astra S (structured 0.4–4m), Gemini 336L (stereo 0.17–20m)
- Handheld: iPhone Pro LiDAR via NeRFCapture over WiFi

**Extras**

- Online SLAM: ROS2 topics to live reconstruction (`scripts/wheeltec_online_slam.py`)
- Offline SLAM: ROS bag → format conversion → high-quality mapping
- ROS bag conversion: ROS1/ROS2 RGB-D extraction (`scripts/wheeltec_rosbag_to_splatam.py`)
- CloudCompare PLY export: color PLY (`scripts/export_ply_cloudcompare.py`)
- Multi-camera configs: `configs/wheeltec/` (rover), `configs/hand/` (handheld), `configs/iphone/`

---

## Installation

Recommended: Python 3.10, Torch 1.12.1 + CUDA 11.6 (tested with Torch 2.3 + CUDA 12.1 too).

```bash
conda create -n splatam python=3.10
conda activate splatam
conda install -c "nvidia/label/cuda-11.6.0" cuda-toolkit
conda install pytorch==1.12.1 torchvision==0.13.1 torchaudio==0.12.1 cudatoolkit=11.6 -c pytorch -c conda-forge
pip install -r requirements.txt
```

Windows (Git Bash): follow [Issue#9 note](https://github.com/spla-tam/SplaTAM/issues/9#issuecomment-1848348403).

**Docker / Singularity**

```bash
docker pull nkeetha/splatam:v1
bash bash_scripts/start_docker.bash
cd /SplaTAM/
pip install virtualenv --user
mkdir venv && cd venv
virtualenv --system-site-packages splatam
source ./splatam/bin/activate
pip install -r venv_requirements.txt
```

Singularity is similar:

```bash
cd </path/to/singularity/folder/>
singularity pull splatam.sif docker://nkeetha/splatam:v1
singularity instance start --nv splatam.sif splatam
singularity run --nv instance://splatam
cd <path/to/SplaTAM/>
pip install virtualenv --user
mkdir venv && cd venv
virtualenv --system-site-packages splatam
source ./splatam/bin/activate
pip install -r venv_requirements.txt
```

---

## Demo

- Online (iPhone / Apple LiDAR + NeRFCapture)
  ```bash
  bash bash_scripts/online_demo.bash configs/iphone/online_demo.py
  ```
- Offline reconstruction
  ```bash
  bash bash_scripts/nerfcapture.bash configs/iphone/nerfcapture.py
  ```
- Capture only
  ```bash
  bash bash_scripts/nerfcapture2dataset.bash configs/iphone/dataset.py
  ```

<p align="center">
  <img src="./assets/collage.gif" alt="examples" width="75%">
</p>

---

## Usage

Example with iPhone configs (swap paths for other datasets):

- Run SLAM
  ```bash
  python scripts/splatam.py configs/iphone/splatam.py
  ```
- Visualize final reconstruction
  ```bash
  python viz_scripts/final_recon.py configs/iphone/splatam.py
  ```
- Online visualization
  ```bash
  python viz_scripts/online_recon.py configs/iphone/splatam.py
  ```
- Export PLY
  ```bash
  python scripts/export_ply.py configs/iphone/splatam.py
  ```
- 3D Gaussian Splatting optimization
  ```bash
  python scripts/post_splatam_opt.py configs/iphone/post_splatam_opt.py
  ```
- Splatting with GT poses
  ```bash
  python scripts/gaussian_splatting.py configs/iphone/gaussian_splatting.py
  ```

---

## Downloads

DATAROOT is `./data` by default; adjust `input_folder` per config if stored elsewhere.

- Replica
  ```bash
  bash bash_scripts/download_replica.sh
  ```
- TUM-RGBD
  ```bash
  bash bash_scripts/download_tum.sh
  ```
- ScanNet: request data on website and extract frames with the official script
- ScanNet++: follow official pipeline and our undistortion variant [link](https://github.com/Nik-V9/scannetpp)
- Replica-V2: grab pre-generated sequences from [vMAP](https://github.com/kxhit/vMAP)

---

## Benchmarking

- Enable Weights & Biases via `wandb=True`, set `entity` and `wandb_folder` in configs.
- Example runs:
  - Replica `room0`
    ```bash
    python scripts/splatam.py configs/replica/splatam.py
    ```
  - TUM `freiburg1_desk`
    ```bash
    python scripts/splatam.py configs/tum/splatam.py
    ```
  - ScanNet `scene0000_00`
    ```bash
    python scripts/splatam.py configs/scannet/splatam.py
    ```
  - ScanNet++ `8b5caf3398`
    ```bash
    python scripts/splatam.py configs/scannetpp/splatam.py
    python scripts/eval_novel_view.py configs/scannetpp/eval_novel_view.py
    ```
  - ReplicaV2 `room0`
    ```bash
    python scripts/splatam.py configs/replica_v2/splatam.py
    python scripts/eval_novel_view.py configs/replica_v2/eval_novel_view.py
    ```

---

## Acknowledgement

- 3D Gaussians: [Dynamic 3D Gaussians](https://github.com/JonathonLuiten/Dynamic3DGaussians), [3D Gaussian Splatting](https://github.com/graphdeco-inria/gaussian-splatting)
- Dataloaders: [GradSLAM & ConceptFusion](https://github.com/gradslam/gradslam/tree/conceptfusion)
- Baselines: [Nice-SLAM](https://github.com/cvg/nice-slam), [Point-SLAM](https://github.com/eriksandstroem/Point-SLAM)

## Citation

```bib
@inproceedings{keetha2024splatam,
        title={SplaTAM: Splat, Track & Map 3D Gaussians for Dense RGB-D SLAM},
        author={Keetha, Nikhil and Karhade, Jay and Jatavallabhula, Krishna Murthy and Yang, Gengshan and Scherer, Sebastian and Ramanan, Deva and Luiten, Jonathon},
        booktitle={Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition},
        year={2024}
      }
```

## Developers

- [Nik-V9](https://github.com/Nik-V9) (Nikhil Keetha)
- [JayKarhade](https://github.com/JayKarhade) (Jay Karhade)
