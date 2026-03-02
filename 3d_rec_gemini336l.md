# Gemini 336L + SplaTAM 在线 3D 高斯重建指南

## 相机规格速览

| 参数 | 数值 |
|------|------|
| 深度技术 | 双目立体视觉（850nm IR） |
| 彩色分辨率 | 1280×720 @ 60fps |
| 深度分辨率 | 848×480 @ 30fps |
| 深度范围 | 0.17–20m（最优 0.25–6m） |
| IMU | 支持（`/camera/gyro_accel/sample`） |
| 接口 | USB 3.0 Type-C |
| 内参 (1280×720) | fx=607.45, fy=607.40, cx=639.19, cy=361.75 |
| 畸变系数 | k1=-0.02966, k2=0.03245, p1=-1.89e-5, p2=-3.20e-4, k3=-0.01113 |

---

## 文件结构

```
SplaTAM/
├── scripts/
│   ├── wheeltec_online_slam.py          # 在线 SLAM 主脚本（支持 IMU）
│   ├── wheeltec_rosbag_to_splatam.py    # ROS2 bag → 数据集转换
│   └── splatam.py                       # 离线 SLAM 主脚本
├── configs/
│   ├── hand/
│   │   └── online_slam_gemini336l.py    # 手持专用配置（独立，开箱即用）
│   └── wheeltec/
│       ├── online_slam_gemini336l.py    # 小车在线配置
│       └── splatam_gemini336l.py        # 离线配置
├── experiments/
│   ├── Handheld_Gemini336L/             # 手持输出目录（自动创建）
│   └── Wheeltec_Gemini336L/             # 小车输出目录（自动创建）
```

---

## 方式一：手持在线建图

专用配置，开箱即用，无需改参数。更换场景只需改 `scene_name` 一行。

### 启动步骤

```bash
# 终端 1：启动相机驱动（确认 IMU 话题正常）
ros2 launch turn_on_wheeltec_robot wheeltec_camera.launch.py
ros2 topic hz /camera/gyro_accel/sample   # 应显示 ~100 Hz

# 终端 2：启动手持 SLAM（--scene_name 指定本次扫描名称，结果自动存入独立目录）
cd VLN/SplaTAM
python scripts/wheeltec_online_slam.py configs/hand/online_slam_gemini336l.py \
    --scene_name handheld_scan_01
```

> **每次扫描换一个 `--scene_name`**，无需修改配置文件，结果自动存入独立目录，不会互相覆盖。

### 输出目录

```
experiments/Handheld_Gemini336L/handheld_scan_01_0/
├── params.npz      # 高斯地图（可视化/导出用）
├── rgb/            # 原始彩色帧
├── depth/          # 原始深度帧（mm，uint16）
├── poses/          # 估计位姿（c2w，.npy）
└── checkpoints/    # 断点（每 50 帧）
```

### 可视化

```bash
# 可视化时同样用 --scene_name 指定要查看的那次扫描
python viz_scripts/final_recon.py configs/hand/online_slam_gemini336l.py
# 注意：final_recon.py 读取配置中的 scene_name，需先确认配置中的默认值或直接用实验路径
```

### 手持操作要点

- 移动速度 ≤ 0.3 m/s，保证帧间重叠
- 转弯时放慢，不要原地快速旋转
- 优先扫有纹理区域，避免大面积白墙
- Ctrl+C 结束后自动保存，无需等待

### 重建结果后处理

```bash
SCENE=handheld_scan_01   # 替换为实际的扫描名称

# 导出 3DGS 格式点云 → experiments/Handheld_Gemini336L/${SCENE}_0/splat.ply
python scripts/export_ply.py configs/hand/online_slam_gemini336l.py \
    --scene_name $SCENE

# 导出标准 RGB 点云（CloudCompare / MeshLab 可直接打开）
# → experiments/Handheld_Gemini336L/${SCENE}_0/splat_rgb.ply
python scripts/export_ply_cloudcompare.py configs/hand/online_slam_gemini336l.py \
    --scene_name $SCENE

# 调整透明度阈值过滤噪点（默认 0.5，越大越干净但点越少）
python scripts/export_ply_cloudcompare.py configs/hand/online_slam_gemini336l.py \
    --scene_name $SCENE --opacity_threshold 0.3
```

| 文件 | 格式 | 颜色属性 | 查看工具 |
|------|------|----------|----------|
| `splat.ply` | 3DGS | `f_dc_0/1/2` (球谐系数) | 3DGS Viewer, SuperSplat |
| `splat_rgb.ply` | 标准点云 | `red/green/blue` (uint8) | CloudCompare, MeshLab, Open3D |

---

## 方式二：小车在线建图

相机安装在 Wheeltec 小车上，随车实时重建。

### 启动步骤

```bash
# 终端 1：启动相机驱动
ros2 launch turn_on_wheeltec_robot wheeltec_camera.launch.py

# 确认话题正常
ros2 topic hz /camera/color/image_raw
ros2 topic hz /camera/depth/image_raw
ros2 topic hz /camera/gyro_accel/sample

# 终端 2：启动小车 SLAM（--scene_name 指定本次扫描名称）
cd VLN/SplaTAM
python scripts/wheeltec_online_slam.py configs/wheeltec/online_slam_gemini336l.py \
    --scene_name office_scan_01

# 可选：同时指定最大帧数
python scripts/wheeltec_online_slam.py configs/wheeltec/online_slam_gemini336l.py \
    --scene_name office_scan_01 \
    --num_frames 500
```

> **每次扫描换一个 `--scene_name`**，结果自动存入 `experiments/Wheeltec_Gemini336L/<scene_name>_0/`，不会覆盖之前的数据。

### 运行时输出说明

```
Frame 123/500 | Gaussians: 45821
[DEBUG] RGB msgs: 123, Depth msgs: 123, Synced frames: 122
Camera intrinsics received: fx=649.2, fy=648.8, cx=638.1, cy=361.4
```

- **Gaussians**：当前高斯点数，随建图增加
- 内参自动从 `/camera/color/camera_info` 读取，无需手动填写

### 结束与输出

```
Ctrl+C → 当前帧处理完毕后安全退出

输出：experiments/Wheeltec_Gemini336L/office_scan_01_0/
├── params.npz           # 高斯地图参数
├── rgb/                 # 原始彩色帧
├── depth/               # 原始深度帧（mm，uint16）
├── poses/               # 估计位姿（c2w，.npy）
└── checkpoints/         # 中间检查点（每 50 帧）
```

### 可视化重建结果

```bash
python viz_scripts/final_recon.py configs/wheeltec/online_slam_gemini336l.py
```

### 重建结果后处理

```bash
SCENE=office_scan_01   # 替换为实际的扫描名称

# 导出 3DGS 格式点云 → experiments/Wheeltec_Gemini336L/${SCENE}_0/splat.ply
python scripts/export_ply.py configs/wheeltec/online_slam_gemini336l.py \
    --scene_name $SCENE

# 导出标准 RGB 点云（CloudCompare / MeshLab 可直接打开）
# → experiments/Wheeltec_Gemini336L/${SCENE}_0/splat_rgb.ply
python scripts/export_ply_cloudcompare.py configs/wheeltec/online_slam_gemini336l.py \
    --scene_name $SCENE

# 调整透明度阈值过滤噪点（默认 0.5，越大越干净但点越少）
python scripts/export_ply_cloudcompare.py configs/wheeltec/online_slam_gemini336l.py \
    --scene_name $SCENE --opacity_threshold 0.3

# 在线可视化（建图时同步查看）
python viz_scripts/online_recon.py configs/wheeltec/online_slam_gemini336l.py
```

| 文件 | 格式 | 颜色属性 | 查看工具 |
|------|------|----------|----------|
| `splat.ply` | 3DGS | `f_dc_0/1/2` (球谐系数) | 3DGS Viewer, SuperSplat |
| `splat_rgb.ply` | 标准点云 | `red/green/blue` (uint8) | CloudCompare, MeshLab, Open3D |

---

## 方式三：离线建图（先录 bag，后重建）

先录制 ROS2 bag，再在算力更强的设备上离线处理，重建质量更好。

### 第一步：录制 ROS2 bag

cd VLN/SplaTAM

```bash
# 只录需要的话题，减小文件体积
ros2 bag record \
    /camera/color/image_raw \
    /camera/depth/image_raw \
    /camera/color/camera_info \
    /camera/depth/camera_info \
    /camera/gyro_accel/sample \
    -o data/my_scene_bag
```

> **建议**：录制时保持相机 30fps，存储需约 200MB/分钟（1280×720 彩色 + 848×480 深度）。

### 第二步：转换为 SplaTAM 数据集格式

```bash
python scripts/wheeltec_rosbag_to_splatam.py \
    data/my_scene_bag/          \   # ROS2 bag 目录
    data/wheeltec_gemini/my_scene
```

转换后目录结构：

```
data/wheeltec_gemini/my_scene/
├── rgb/        # 000000.jpg, 000001.jpg, ...
├── depth/      # 000000.png, 000001.png, ... (uint16, mm)
└── poses/      # 可选，如录了 /odom
```

### 第三步：运行离线 SLAM

```bash
# 通过命令行参数指定场景名和数据目录（无需修改配置文件）
python scripts/splatam.py configs/wheeltec/splatam_gemini336l.py \
    --scene_name my_scene \
    --basedir ./data/wheeltec_gemini

# 如果数据已放在配置文件默认目录（./data/wheeltec_gemini），只需指定场景名：
python scripts/splatam.py configs/wheeltec/splatam_gemini336l.py \
    --scene_name my_scene

# 也可以完全不加参数，使用配置文件中的默认值：
python scripts/splatam.py configs/wheeltec/splatam_gemini336l.py
```

> **参数说明**：`--scene_name` 覆盖配置中的 `sequence` 和 `run_name`；`--basedir` 覆盖数据根目录。两者不指定时使用配置文件中的默认值。

离线模式迭代次数更多（tracking=50, mapping=60），重建质量优于在线模式。

### 可视化

```bash
python viz_scripts/final_recon.py configs/wheeltec/splatam_gemini336l.py
```

### 重建结果后处理

```bash
# 导出 3DGS 格式点云 → experiments/Wheeltec_Gemini336L/<scene_name>_0/splat.ply
python scripts/export_ply.py configs/wheeltec/splatam_gemini336l.py

# 导出标准 RGB 点云（CloudCompare / MeshLab 可直接打开）
# → experiments/Wheeltec_Gemini336L/<scene_name>_0/splat_rgb.ply
python scripts/export_ply_cloudcompare.py configs/wheeltec/splatam_gemini336l.py

# 调整透明度阈值过滤噪点（默认 0.5，越大越干净但点越少）
python scripts/export_ply_cloudcompare.py configs/wheeltec/splatam_gemini336l.py --opacity_threshold 0.3

# 后处理优化（可选，进一步提升渲染质量）
python scripts/post_splatam_opt.py configs/wheeltec/post_splatam_opt_gemini336l.py
```

| 文件 | 格式 | 颜色属性 | 查看工具 |
|------|------|----------|----------|
| `splat.ply` | 3DGS | `f_dc_0/1/2` (球谐系数) | 3DGS Viewer, SuperSplat |
| `splat_rgb.ply` | 标准点云 | `red/green/blue` (uint8) | CloudCompare, MeshLab, Open3D |

---

## 参数调整：手持模式 vs 小车模式

### 核心区别

| 特性 | 手持 | 小车 |
|------|------|------|
| 运动自由度 | 6DOF（全自由） | 近似平面（x, y, yaw） |
| 运动速度 | 慢速（人手节奏） | 可配置（0.1–0.5 m/s） |
| 旋转速度 | 快（可能突然转） | 慢（电机限速） |
| 计算设备 | 笔记本（接 USB） | Jetson Orin NX（随车） |
| 里程计 | 无 | 有（`/odom`） |
| 抖动 | 高 | 低 |

---

### 手持模式参数

> 手持模式已有专用配置文件 `configs/hand/online_slam_gemini336l.py`，
> 下方列出关键参数说明供参考，无需手动修改小车配置。

```python
# configs/hand/online_slam_gemini336l.py 中的关键差异

scene_name = "handheld_scan_01"
num_frames = -1              # 不限帧数，手动 Ctrl+C 结束

# 手持运动更不规则，给跟踪更多迭代余量
tracking_iters = 40          # 默认 30 → 40
mapping_iters  = 25          # 略降保实时性

mapping_window_size = 20     # 稍大，应对视角变化多

config = dict(
    ...
    scene_radius_depth_ratio=4,   # 手持室内场景较小，半径收紧

    ros2=dict(
        ...
        use_odom_init=False,          # 手持无轮式里程计，关闭避免警告
        use_imu_for_propagation=True, # IMU 辅助旋转，手持必开
        imu_topic="/camera/gyro_accel/sample",
    ),
    use_imu_for_propagation=True,

    tracking=dict(
        ...
        num_iters=40,
        forward_prop=True,            # 常速度模型 + IMU 共同初始化
        lrs=dict(
            ...
            cam_unnorm_rots=0.0015,   # 稍大，应对快速旋转
            cam_trans=0.005,          # 稍大，应对快速平移
        ),
    ),
    mapping=dict(
        ...
        num_iters=25,
        sil_thres=0.5,
        ...
    ),
    ...
)
```

**手持操作建议：**
- 移动速度 ≤ 0.3 m/s，保证帧间重叠 ≥ 60%
- 转弯时放慢，不要原地快速旋转
- 从中心向外扫，回到起点提升闭环质量
- 优先扫有纹理的区域（白墙会造成深度/色彩歧义）

---

### 小车模式参数

```python
# ---- 小车模式关键调整 ----

scene_name = "robot_map_01"
num_frames = 1000            # 按实际场景大小估算

# 小车运动平稳，可以用更少跟踪迭代换取实时性
tracking_iters = 25          # 默认 30 → 25（平稳运动收敛快）
mapping_iters  = 35          # 可略提高建图质量

mapping_window_size = 16     # Jetson 内存限制，保持默认

config = dict(
    ...
    scene_radius_depth_ratio=2,   # 小车场景通常较大（走廊/房间）

    ros2=dict(
        ...
        use_odom_init=True,           # 有轮式里程计，开启
        odom_topic="/odom",
        use_imu_for_propagation=True, # IMU 补充旋转，仍建议开启
        imu_topic="/camera/gyro_accel/sample",
    ),
    use_imu_for_propagation=True,

    camera=dict(
        ...
        depth_near=0.25,   # 小车安装位置通常离障碍物 >0.25m
        depth_far=10.0,    # 室内走廊通常不超过 10m，减少远距噪声
    ),

    tracking=dict(
        ...
        num_iters=25,
        forward_prop=True,
        lrs=dict(
            ...
            cam_unnorm_rots=0.0008,   # 保守，小车旋转变化小
            cam_trans=0.003,
        ),
    ),
    mapping=dict(
        ...
        num_iters=35,
        ...
    ),
    ...
)
```

**小车操作建议：**
- 速度控制在 0.2–0.4 m/s，避免动态模糊
- `map_every=1` 保持每帧建图（小车速度慢，有计算余量）
- 走 S 形或螺旋路径，比单一直线有更好的覆盖
- 返回起点附近时停留 2–3 秒，有助于全局一致性

---

## 参数速查对照表

| 参数 | 手持推荐值 | 小车推荐值 | 说明 |
|------|-----------|-----------|------|
| `tracking_iters` | 40 | 25 | 手持抖动需更多迭代 |
| `mapping_iters` | 25 | 35 | 小车平稳，可提高建图质量 |
| `mapping_window_size` | 20 | 16 | 手持视角变化大，窗口稍大 |
| `scene_radius_depth_ratio` | 4 | 2 | 手持室内小场景 / 小车大场景 |
| `depth_near` | 0.17 | 0.25 | 小车安装位有最近安全距离 |
| `depth_far` | 20.0 | 10.0 | 小车室内减少远距噪声 |
| `cam_unnorm_rots` lr | 0.0015 | 0.0008 | 手持转动快需大步长 |
| `cam_trans` lr | 0.005 | 0.003 | 同上 |
| `use_odom_init` | False | True | 手持无轮式里程计 |
| `use_imu_for_propagation` | True | True | 两种场景都建议开启 |

---

## 常见问题

### Q：跟踪丢失（tracking loss 突然变大）

**手持**：移动太快，帧间重叠不足。放慢速度，回到上一个已建图区域重新扫。

**小车**：速度过快或转弯太急。降低底盘速度，检查 `tracking_iters` 是否足够。

通用处理：
```bash
# 从最近的检查点恢复
# 修改配置：
config['load_checkpoint'] = True
config['checkpoint_time_idx'] = 300  # 改为实际检查点帧号
```

---

### Q：高斯点数增长过快，内存溢出

降低稠密化频率：
```python
mapping=dict(
    sil_thres=0.6,           # 提高阈值，减少新增高斯
    pruning_dict=dict(
        prune_every=10,      # 更频繁剪枝
        removal_opacity_threshold=0.02,
    ),
)
```

---

### Q：深度噪声导致重建有浮点/花斑

Gemini 336L 为双目立体，远距（>6m）噪声较大：
```python
camera=dict(
    depth_far=6.0,            # 只使用最优深度范围
)
tracking=dict(
    ignore_outlier_depth_loss=True,  # 确保开启
)
```

---

### Q：IMU 没有数据（首次启动）

检查 Orbbec 驱动是否开启了 IMU 流：
```bash
ros2 topic hz /camera/gyro_accel/sample
# 正常应显示 ~100 Hz

# 如果没有输出，检查驱动启动参数：
# gemini_336l.launch.py 中需要 enable_sync_output_accel_gyro:=true
```

临时关闭 IMU（回退到常速度模型）：
```python
use_imu_for_propagation=False,
ros2=dict(
    use_imu_for_propagation=False,
)
```

---

### Q：同步失败（synced frames 为 0）

```bash
# 检查 RGB 和深度话题的 QoS
ros2 topic info /camera/color/image_raw --verbose
ros2 topic info /camera/depth/image_raw --verbose

# 如果 reliability 不一致，在 online_slam.py 中调整 slop：
# ApproximateTimeSynchronizer(..., slop=0.15)  # 从 0.1 增加到 0.15
```


