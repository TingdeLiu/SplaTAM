# Wheeltec 小车 + SplaTAM 离线 3D 重建指南

车型：senior_4wd_bs | 相机：Astra S | 主控：Jetson Orin NX 16GB | ROS2 Humble

## 工作流程

```
小车采集 rosbag → 转换格式 → 运行 SplaTAM → 可视化
```

---

## 1. 数据采集

### 启动节点

```bash
# 终端 1：启动导航节点
ros2 launch wheeltec_nav2 wheeltec_nav2.launch.py

# 终端 2：启动相机
ros2 launch turn_on_wheeltec_robot wheeltec_camera.launch.py
```

### 检查话题

```bash
ros2 topic list
ros2 topic hz /camera/rgb/image_raw
ros2 topic hz /camera/depth/image
```

### 录制（推荐带里程计）

```bash
ros2 bag record \
    /camera/rgb/image_raw \
    /camera/depth/image \
    /camera/rgb/camera_info \
    /odom \
    /tf \
    -o ~/splatam_data/scene_01
```

### 验证

```bash
ros2 bag info ~/splatam_data/scene_01
```

### 采集要点

- **速度**：直线 < 0.3 m/s（推荐 0.15-0.25），转弯角速度 < 30 deg/s
- **深度范围**：保持物体在 0.4-4.0m 内（最佳 0.6-4.0m）
- **环境**：充足均匀光照，丰富纹理，平坦地面
- **轨迹**：平滑弧线，保持 30-50% 视角重叠，关键位置停留 1-2 秒
- **避免**：急转弯、玻璃/镜子/白墙、过暗过亮环境

---

## 2. 数据转换

### 安装依赖

```bash
pip install rosbags opencv-python tqdm
```

### 转换

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

### 输出格式

```
wheeltec_scene_01/
├── rgb/          # 0000.jpg, 0001.jpg, ...
├── depth/        # 0000.png, 0001.png, ... (uint16, mm)
├── poses/        # 0000.npy, ... (可选，轮式里程计)
└── camera_intrinsics.txt
```

---

## 3. 运行 SplaTAM

```bash
# 修改 configs/wheeltec/splatam.py 中的 scene_name 为你的场景目录名
python scripts/splatam.py configs/wheeltec/splatam.py
```

输出在 `./experiments/Wheeltec/<scene_name>_0/params.npz`

---

## 4. 可视化

### 输出目录结构

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
python scripts/export_ply.py configs/wheeltec/splatam.py

# 方式 2: 标准 RGB 点云 (red/green/blue 顶点颜色，用于 CloudCompare / MeshLab)
python scripts/export_ply_cloudcompare.py configs/wheeltec/splatam.py

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

## 5. 常见问题

| 问题 | 解决方法 |
|------|---------|
| 深度质量差 | 保持 0.6-4.0m 范围，启用 `ignore_outlier_depth_loss=True`，增大 `depth` 权重 |
| 跟踪失败 | 降速 < 0.25 m/s，增加 `tracking_iters=80`，`keyframe_every=3` |
| GPU 内存不足 | 降分辨率 320x240，减小 `mapping_window_size=12`，`map_every=5` |
| 深度单位错误 | 检查 depth 图：应为 uint16, 范围 400-4000 (mm)。调整 `depth_scale` |
| 里程计漂移 | 正常，SplaTAM 会自行修正。严重时用纯视觉：`use_gt_poses=False` |

---

## 6. 性能优化

### Jetson Orin NX 上运行

```python
# configs/wheeltec/splatam.py 中调整
desired_image_height=320, desired_image_width=240,
tracking_iters=20, mapping_iters=30,
map_every=5, mapping_window_size=12,
```

预期：320x240 约 1-3 FPS

### PC 离线处理（推荐）

640x480 全分辨率，RTX 3080 约 2 FPS，质量最高。

---

## 7. 已创建的文件

| 文件 | 说明 |
|------|------|
| `configs/data/wheeltec.yaml` | Astra S 相机参数 |
| `configs/wheeltec/splatam.py` | SLAM 配置 |
| `datasets/gradslam_datasets/wheeltec.py` | 数据加载器 |
| `scripts/wheeltec_rosbag_to_splatam.py` | ROS bag 转换 |
| `scripts/compare_trajectories.py` | 轨迹对比可视化 |

硬件规格详见 `reference_wheeltec/`。
