# Wheeltec + SplaTAM 在线 3D 高斯重建指南

## 概述

实时从 Wheeltec 小车 (Jetson Orin NX) + Orbbec Astra S 深度相机接收 RGB-D 帧，边采集边运行 SplaTAM SLAM，完成在线 3D 高斯重建。

## 架构

```
Wheeltec 小车 (ROS2 Humble)
├── Astra S 相机 → /camera/color/image_raw, /camera/depth/image_raw
├── 底盘里程计   → /odom
└── wheeltec_online_slam.py
    ├── ROS2FrameReceiver (后台线程: rclpy 订阅 + 时间同步)
    └── online_slam_loop (主线程: Tracking → Mapping → 循环)
```

**SLAM 循环 (每帧)**:
1. 接收同步的 RGB + Depth 帧
2. **Tracking**: 固定高斯，优化当前帧相机位姿
3. **Mapping**: 固定位姿，优化高斯参数 + 添加新高斯
4. 关键帧选择 + 检查点保存

## 文件说明

| 文件 | 作用 |
|------|------|
| `scripts/wheeltec_online_slam.py` | 在线 SLAM 主脚本 (ROS2 订阅 + SLAM 循环) |
| `configs/wheeltec/online_slam.py` | 在线模式配置 (针对 Jetson 优化) |
| `configs/wheeltec/splatam.py` | 离线模式配置 (对比用) |
| `scripts/export_ply.py` | 导出 3DGS 格式 PLY (球谐系数颜色) |
| `scripts/export_ply_cloudcompare.py` | 导出标准 RGB 点云 PLY (CloudCompare 可直接显示颜色) |

## 环境依赖

```bash
# ROS2 (Jetson 上应已安装)
# 确认 rclpy 可用:
python3 -c "import rclpy; print('rclpy OK')"

# 额外 ROS2 Python 依赖
pip install message_filters  # 如果没有随 ros2 安装

# SplaTAM 依赖 (在 splatam conda 环境中)
pip install -r requirements.txt
```

## 操作步骤

### 1. 启动小车和相机

```bash
# 终端 1: 启动导航
ros2 launch wheeltec_nav2 wheeltec_nav2.launch.py

# 终端 2: 启动相机
ros2 launch turn_on_wheeltec_robot wheeltec_camera.launch.py
```

验证话题:
```bash
ros2 topic list | grep camera
# 应看到:
#   /camera/color/image_raw
#   /camera/depth/image_raw
#   /camera/color/camera_info

ros2 topic hz /camera/color/image_raw
# 应 ~30 Hz
```

### 2. 启动在线 SLAM

```bash
cd /path/to/SplaTAM
conda activate splatam

# 默认配置 (500帧)
python scripts/wheeltec_online_slam.py configs/wheeltec/online_slam.py

# 自定义参数
python scripts/wheeltec_online_slam.py configs/wheeltec/online_slam.py \
    --num_frames 300 \
    --rgb_topic /camera/color/image_raw \
    --depth_topic /camera/depth/image_raw
```

### 3. 采集过程

- 缓慢移动小车（线速度 < 0.3 m/s）
- 避免纯旋转，保持平移
- 每帧处理时间约 0.5-1.5s（取决于高斯数量）
- `Ctrl+C` 随时停止，自动保存

### 4. 查看结果

```bash
# 输出目录结构:
experiments/Wheeltec_Online/online_office_0/
├── params.npz          # 最终 3D 高斯模型
├── splat.ply           # 3DGS 格式 PLY (给 3DGS Viewer)
├── splat_rgb.ply       # 标准 RGB 点云 PLY (给 CloudCompare)
├── config.py           # 运行配置备份
├── checkpoints/        # 中间检查点
├── rgb/                # 保存的 RGB 帧
├── depth/              # 保存的深度帧
└── poses/              # 估计的相机位姿 (.npy)
```

#### 导出 PLY 点云

```bash
# 方式 1: 3DGS 格式 (f_dc_0/1/2 球谐系数，用于 3DGS Viewer / 后续优化)
python scripts/export_ply.py configs/wheeltec/online_slam.py

# 方式 2: 标准 RGB 点云 (red/green/blue 顶点颜色，用于 CloudCompare / MeshLab)
python scripts/export_ply_cloudcompare.py configs/wheeltec/online_slam.py

# 调整透明度阈值过滤噪点 (默认 0.5，越大越干净但点越少)
python scripts/export_ply_cloudcompare.py configs/wheeltec/online_slam.py --opacity_threshold 0.3
```

| 文件 | 格式 | 颜色属性 | 查看工具 |
|------|------|----------|----------|
| `splat.ply` | 3DGS | `f_dc_0/1/2` (球谐系数) | 3DGS Viewer, SuperSplat |
| `splat_rgb.ply` | 标准点云 | `red/green/blue` (uint8) | CloudCompare, MeshLab, Open3D |

#### 可视化

```bash
# SplaTAM 内置交互式可视化
python viz_scripts/final_recon.py configs/wheeltec/online_slam.py

# 用 CloudCompare 打开 (需要先导出 splat_rgb.ply)
cloudcompare splat_rgb.ply
```

## 配置调优

### Jetson Orin NX 性能优化

`configs/wheeltec/online_slam.py` 已针对 Jetson 优化:

| 参数 | 在线值 | 离线值 | 说明 |
|------|--------|--------|------|
| `tracking_iters` | 30 | 50 | 减少迭代加速 |
| `mapping_iters` | 30 | 60 | 减少迭代加速 |
| `mapping_window_size` | 16 | 20 | 减少显存占用 |
| `downscale_factor` | 2.0 | 1.0 | Tracking 用 320x240 |
| `densify_downscale_factor` | 1.0 | 1.0 | 稠密化用原始分辨率 |

### 如果显存不足 (OOM)

```python
# 在 configs/wheeltec/online_slam.py 中调整:
mapping_window_size = 12      # 减少关键帧窗口
tracking_iters = 20           # 减少迭代
mapping_iters = 20
downscale_factor = 4.0        # 进一步降低分辨率 → 160x120
densify_downscale_factor = 2.0  # 稠密化也降低 → 320x240
```

### 如果跟踪丢失

```python
# 增加跟踪迭代和学习率
tracking_iters = 60
config['tracking']['lrs']['cam_unnorm_rots'] = 0.002
config['tracking']['lrs']['cam_trans'] = 0.008
config['tracking']['depth_loss_thres'] = 50000  # 允许更多额外迭代
```

## 在线 vs 离线对比

| 特性 | 在线 (`wheeltec_online_slam.py`) | 离线 (`splatam.py`) |
|------|----------------------------------|---------------------|
| 数据来源 | ROS2 实时订阅 | 磁盘上的图片文件 |
| 采集+重建 | 同时进行 | 先采集后处理 |
| 帧率 | ~1-2 FPS (Jetson) | 不受限 |
| 重建质量 | 较低 (迭代数少) | 较高 |
| 适用场景 | 实时预览、快速扫描 | 最终高质量重建 |

**推荐工作流**: 先用在线模式快速扫描预览，确认覆盖完整后，用保存的 RGB-D 数据 + 离线模式精细重建。

## 离线精细重建 (使用在线采集的数据)

在线 SLAM 会自动保存所有帧到 `rgb/` 和 `depth/` 目录，可直接用于离线重建:

```bash
# 用在线采集的数据跑离线 SLAM
python scripts/splatam.py configs/wheeltec/splatam.py

# 需要修改 splatam.py 配置中的数据路径:
# data.basedir = "./experiments/Wheeltec_Online"
# data.sequence = "online_office_0"
```
