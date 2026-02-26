# iPhone + SplaTAM 3D 高斯重建指南

## 概述

使用带 LiDAR 的 iPhone（12 Pro 及以上）通过 NeRFCapture App 采集 RGB-D 数据，经 WiFi 实时传输到 PC，运行 SplaTAM 进行 3D 高斯重建。

## 前提条件

- **iPhone**: 12 Pro / 13 Pro / 14 Pro / 15 Pro 或 iPad Pro（需 LiDAR）
- **App**: [NeRFCapture](https://apps.apple.com/au/app/nerfcapture/id6446518379)（App Store 免费下载）
- **PC**: NVIDIA GPU（≥6GB 显存），安装好 SplaTAM 环境
- **网络**: iPhone 和 PC 在同一 WiFi 局域网

## 架构

```
iPhone (NeRFCapture App)
  ↓  CycloneDDS over WiFi
PC (iphone_demo.py / nerfcapture2dataset.py)
  ├── 接收 RGB + Depth + ARKit 位姿
  ├── 保存数据到 rgb/ depth/ transforms.json
  └── 运行 SplaTAM SLAM (可选在线/离线)
```

## 环境依赖

```bash
conda activate splatam
pip install cyclonedds  # DDS 通信库
```

## 三种使用模式

### 模式 A: 在线实时建图（边采边建）

iPhone 发帧 → PC 实时做 SLAM。

```bash
# 修改配置
vim configs/iphone/online_demo.py
# 关键参数:
#   num_frames = 100        # 采集帧数
#   scene_name = "my_room"  # 场景名称

# 启动（需 sudo 设置网络缓冲区）
bash bash_scripts/online_demo.bash configs/iphone/online_demo.py
```

操作步骤:
1. PC 终端出现 "Waiting for frames..."
2. iPhone 打开 NeRFCapture App
3. 确认 App 右上角显示 "Depth Supported"
4. 点 "Send" 开始逐帧发送（或连续发送）
5. 达到 `num_frames` 后自动停止，弹出 3D 可视化

### 模式 B: 先采集后处理（推荐高质量重建）

先只存数据，之后离线跑 SLAM，质量更高。

```bash
# 步骤 1: 采集数据
bash bash_scripts/nerfcapture2dataset.bash configs/iphone/dataset.py

# 步骤 2: 离线跑 SplaTAM
python scripts/splatam.py configs/iphone/splatam.py

# 步骤 3: 可视化
python viz_scripts/final_recon.py configs/iphone/splatam.py
```

### 模式 C: 采集 + 离线 SLAM 一键完成

```bash
bash bash_scripts/nerfcapture.bash configs/iphone/nerfcapture.py
```

## 配置文件说明

| 文件 | 模式 | 说明 |
|------|------|------|
| `configs/iphone/online_demo.py` | 在线 | 实时 SLAM 配置 |
| `configs/iphone/dataset.py` | 采集 | 仅采集数据，不跑 SLAM |
| `configs/iphone/nerfcapture.py` | 离线 | 采集后离线 SLAM |
| `configs/iphone/splatam.py` | 离线 | 在已有数据上跑 SLAM |
| `configs/iphone/post_splatam_opt.py` | 后处理 | 3DGS 精细优化 |
| `configs/iphone/gaussian_splatting.py` | 后处理 | GT 位姿 + 3DGS |

## 关键参数调整

```python
# configs/iphone/online_demo.py

scene_name = "office"     # 场景名
num_frames = 100          # 采集帧数（按需调整）
depth_scale = 10.0        # 深度保存缩放因子

# 分辨率（iPhone LiDAR 原始 1920x1440）
full_res_width = 1920
full_res_height = 1440
downscale_factor = 2.0        # Tracking 用 960x720
densify_downscale_factor = 4.0  # 稠密化用 480x360

# SLAM 迭代次数
tracking_iters = 60
mapping_iters = 60
mapping_window_size = 32
keyframe_every = 5
```

## 输出目录结构

```
experiments/iPhone_Captures/{scene_name}/
├── params.npz          # 最终 3D 高斯模型
├── transforms.json     # NeRFStudio 格式元数据 (内参 + 位姿)
├── rgb/                # RGB 帧
│   ├── 0.png
│   └── ...
├── depth/              # 深度帧
│   ├── 0.png
│   └── ...
└── checkpoints/        # 中间检查点
```

## 查看结果

```bash
# SplaTAM 内置可视化
python viz_scripts/final_recon.py configs/iphone/online_demo.py

# 导出 3DGS 格式 PLY
python scripts/export_ply.py configs/iphone/online_demo.py

# 导出标准 RGB 点云 (CloudCompare 可直接看颜色)
python scripts/export_ply_cloudcompare.py configs/iphone/online_demo.py

# 后处理精细优化（可选，显著提升质量）
python scripts/post_splatam_opt.py configs/iphone/post_splatam_opt.py
```

## 采集技巧

- **移动速度**: 缓慢平稳，避免运动模糊
- **覆盖范围**: 多角度覆盖，确保有足够重叠
- **避免**: 纯旋转、快速运动、镜面/透明物体
- **帧数建议**: 小场景 50-100 帧，大房间 200-500 帧
- **光照**: 保持稳定光照，避免过暗区域

## 常见问题

### App 右上角没显示 "Depth Supported"
设备不支持 LiDAR。需要 iPhone 12 Pro 或更新的 Pro 系列。

### PC 收不到帧
1. 确认 iPhone 和 PC 在同一 WiFi
2. 检查防火墙是否阻止 DDS 通信
3. 确认已执行 `sudo sysctl -w net.core.rmem_max=2147483647`

### 重建质量不好
1. 用模式 B（先采后处理）代替模式 A
2. 增加 `tracking_iters` 和 `mapping_iters`
3. 运行后处理优化: `python scripts/post_splatam_opt.py configs/iphone/post_splatam_opt.py`
