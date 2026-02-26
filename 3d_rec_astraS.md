# Wheeltec + SplaTAM 3D 重建指南 (Astra S)

车型：senior_4wd_bs | 相机：Orbbec Astra S | 主控：Jetson Orin NX 16GB | ROS2 Humble

## 模式对比

| 特性 | 在线模式 | 离线模式 |
|------|----------|----------|
| 数据来源 | ROS2 实时订阅 | 磁盘上的图片文件 |
| 采集+重建 | 同时进行 | 先采集后处理 |
| 帧率 | ~1-2 FPS (Jetson) | 不受限 |
| 重建质量 | 较低 (迭代数少) | 较高 |
| 适用场景 | 实时预览、快速扫描 | 最终高质量重建 |

**推荐工作流**: 先用在线模式快速扫描预览，确认覆盖完整后，用保存的 RGB-D 数据 + 离线模式精细重建。

---

## 在线模式

### 架构

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

### 环境依赖

```bash
# 确认 rclpy 可用
python3 -c "import rclpy; print('rclpy OK')"

# 额外依赖
pip install message_filters  # 如果没有随 ros2 安装
pip install -r requirements.txt
```

### 操作步骤

#### 1. 启动小车和相机

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

ros2 topic hz /camera/color/image_raw  # 应 ~30 Hz
```

#### 2. 启动在线 SLAM

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

#### 3. 采集过程

- 缓慢移动小车（线速度 < 0.3 m/s），避免纯旋转
- 每帧处理时间约 0.5-1.5s（取决于高斯数量）
- `Ctrl+C` 随时停止，自动保存

#### 4. 输出目录

```
experiments/Wheeltec_Online/online_office_0/
├── params.npz          # 最终 3D 高斯模型
├── splat.ply           # 3DGS 格式 PLY
├── splat_rgb.ply       # 标准 RGB 点云 PLY
├── config.py           # 运行配置备份
├── checkpoints/        # 中间检查点
├── rgb/                # 保存的 RGB 帧（可用于离线精细重建）
├── depth/              # 保存的深度帧
└── poses/              # 估计的相机位姿 (.npy)
```

### 离线精细重建（使用在线采集的数据）

```bash
# 修改 splatam.py 配置中的数据路径后运行
# data.basedir = "./experiments/Wheeltec_Online"
# data.sequence = "online_office_0"
python scripts/splatam.py configs/wheeltec/splatam.py

```

---

## 离线模式

### 工作流程

```
小车采集 rosbag → 转换格式 → 运行 SplaTAM → 可视化
```

### 1. 数据采集

#### 启动节点

```bash
# 终端 1：启动导航节点
ros2 launch wheeltec_nav2 wheeltec_nav2.launch.py

# 终端 2：启动相机
ros2 launch turn_on_wheeltec_robot wheeltec_camera.launch.py
```

#### 检查话题

```bash
ros2 topic list
ros2 topic hz /camera/rgb/image_raw
ros2 topic hz /camera/depth/image
```

#### 录制（推荐带里程计）

```bash
ros2 bag record \
    /camera/rgb/image_raw \
    /camera/depth/image \
    /camera/rgb/camera_info \
    /odom \
    /tf \
    -o ~/splatam_data/scene_01
```

#### 验证

```bash
ros2 bag info ~/splatam_data/scene_01
```

#### 采集要点

- **速度**：直线 < 0.3 m/s（推荐 0.15-0.25），转弯角速度 < 30 deg/s
- **深度范围**：保持物体在 0.4-4.0m 内（最佳 0.6-4.0m）
- **环境**：充足均匀光照，丰富纹理，平坦地面
- **轨迹**：平滑弧线，保持 30-50% 视角重叠，关键位置停留 1-2 秒
- **避免**：急转弯、玻璃/镜子/白墙、过暗过亮环境

### 2. 数据转换

#### 安装依赖

```bash
pip install rosbags opencv-python tqdm
```

#### 转换

```bash
# 不使用里程计
python scripts/wheeltec_rosbag_to_splatam.py \
    ~/splatam_data/scene_01 \
    ./data/wheeltec/wheeltec_scene_01

# 使用里程计（推荐）
python scripts/wheeltec_rosbag_to_splatam.py \
    ~/splatam_data/scene_01 \
    ./data/wheeltec/wheeltec_scene_01 \
    --use_odom
```

脚本同时支持 ROS1（.bag）和 ROS2（mcap/sqlite3）格式。

#### 输出格式

```
wheeltec_scene_01/
├── rgb/          # 0000.jpg, 0001.jpg, ...
├── depth/        # 0000.png, 0001.png, ... (uint16, mm)
├── poses/        # 0000.npy, ... (可选，轮式里程计)
└── camera_intrinsics.txt
```

### 3. 运行 SplaTAM

```bash
# 修改 configs/wheeltec/splatam.py 中的 scene_name 为你的场景目录名
python scripts/splatam.py configs/wheeltec/splatam.py
```

输出在 `./experiments/Wheeltec/<scene_name>_0/params.npz`

---

## 可视化与导出

### 输出目录结构（离线模式）

```
experiments/Wheeltec/<scene_name>_0/
├── params.npz          # 最终 3D 高斯模型
├── splat.ply           # 3DGS 格式 PLY (给 3DGS Viewer)
├── splat_rgb.ply       # 标准 RGB 点云 PLY (给 CloudCompare)
└── config.py           # 运行配置备份
```

### 导出 PLY 点云

```bash
# 方式 1: 3DGS 格式 (f_dc_0/1/2 球谐系数，用于 3DGS Viewer / 后续优化)
python scripts/export_ply.py configs/wheeltec/splatam.py          # 离线
python scripts/export_ply.py configs/wheeltec/online_slam.py      # 在线

# 方式 2: 标准 RGB 点云 (red/green/blue 顶点颜色，用于 CloudCompare / MeshLab)
python scripts/export_ply_cloudcompare.py configs/wheeltec/splatam.py
python scripts/export_ply_cloudcompare.py configs/wheeltec/online_slam.py

# 调整透明度阈值过滤噪点 (默认 0.5，越大越干净但点越少)
python scripts/export_ply_cloudcompare.py configs/wheeltec/splatam.py --opacity_threshold 0.3
```

| 文件 | 格式 | 颜色属性 | 查看工具 |
|------|------|----------|----------|
| `splat.ply` | 3DGS | `f_dc_0/1/2` (球谐系数) | 3DGS Viewer, SuperSplat |
| `splat_rgb.ply` | 标准点云 | `red/green/blue` (uint8) | CloudCompare, MeshLab, Open3D |

### 交互式可视化

```bash
# SplaTAM 内置交互式可视化
python viz_scripts/final_recon.py configs/wheeltec/splatam.py

# 用 CloudCompare 打开 (需要先导出 splat_rgb.ply)
cloudcompare splat_rgb.ply
```

### 轨迹对比（如果有里程计）

```bash
python scripts/compare_trajectories.py \
    ./experiments/Wheeltec/<scene>_0/params.npz \
    --odom_dir ./data/wheeltec/<scene>/poses
```

---

## 配置调优

### Jetson Orin NX 性能参数对比

| 参数 | 在线值 | 离线值 | 说明 |
|------|--------|--------|------|
| `tracking_iters` | 30 | 50 | 减少迭代加速 |
| `mapping_iters` | 30 | 60 | 减少迭代加速 |
| `mapping_window_size` | 16 | 20 | 减少显存占用 |
| `downscale_factor` | 2.0 | 1.0 | Tracking 用 320x240 |
| `densify_downscale_factor` | 1.0 | 1.0 | 稠密化用原始分辨率 |

预期：320x240 约 1-3 FPS（在线）；640x480 RTX 3080 约 2 FPS（离线质量最高）

### 如果显存不足 (OOM)

```python
# 在 configs/wheeltec/online_slam.py 中调整:
mapping_window_size = 12      # 减少关键帧窗口
tracking_iters = 20
mapping_iters = 20
downscale_factor = 4.0        # 进一步降低分辨率 → 160x120
densify_downscale_factor = 2.0
```

### 如果跟踪丢失

```python
tracking_iters = 60
config['tracking']['lrs']['cam_unnorm_rots'] = 0.002
config['tracking']['lrs']['cam_trans'] = 0.008
config['tracking']['depth_loss_thres'] = 50000
```

---

## 常见问题

| 问题 | 解决方法 |
|------|---------|
| 深度质量差 | 保持 0.6-4.0m 范围，启用 `ignore_outlier_depth_loss=True`，增大 `depth` 权重 |
| 跟踪失败 | 降速 < 0.25 m/s，增加 `tracking_iters=80`，`keyframe_every=3` |
| GPU 内存不足 | 降分辨率 320x240，减小 `mapping_window_size=12`，`map_every=5` |
| 深度单位错误 | 检查 depth 图：应为 uint16, 范围 400-4000 (mm)。调整 `depth_scale` |
| 里程计漂移 | 正常，SplaTAM 会自行修正。严重时用纯视觉：`use_gt_poses=False` |

---

## 已创建的文件

| 文件 | 说明 |
|------|------|
| `configs/data/wheeltec.yaml` | Astra S 相机参数 |
| `configs/wheeltec/splatam.py` | 离线 SLAM 配置 |
| `configs/wheeltec/online_slam.py` | 在线 SLAM 配置（针对 Jetson 优化） |
| `datasets/gradslam_datasets/wheeltec.py` | 数据加载器 |
| `scripts/wheeltec_online_slam.py` | 在线 SLAM 主脚本（ROS2 订阅 + SLAM 循环） |
| `scripts/wheeltec_rosbag_to_splatam.py` | ROS bag 转换 |
| `scripts/compare_trajectories.py` | 轨迹对比可视化 |

硬件规格详见 `reference_wheeltec/`。
