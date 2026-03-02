# SplaTAM 项目架构详解

## 目录结构概览

```
SplaTAM/
├── scripts/              # 主要可执行脚本
├── configs/              # 数据集配置文件
├── datasets/             # 数据加载器
├── utils/                # 工具函数和辅助模块
├── viz_scripts/          # 可视化脚本
├── bash_scripts/         # 自动化Shell脚本
├── diff-gaussian-rasterization-w-depth.git/  # 外部Gaussian光栅化库（子模块）
├── requirements.txt      # Python依赖
├── environment.yml       # Conda环境配置
└── README.md             # 项目说明
```

---

## 核心脚本 (scripts/)

### 1. `scripts/splatam.py`
**核心SLAM管道主程序**

这是整个系统的核心，实现了完整的RGB-D SLAM流程。

**主要功能：**
- **初始化**: 从第一帧RGB-D数据创建初始3D Gaussian点云
- **跟踪阶段 (Tracking)**:
  - 固定Gaussians参数，仅优化相机位姿
  - 使用光度损失(RGB)和深度损失
  - 支持前向传播（恒速模型）初始化新帧位姿
  - 保留最小损失的候选位姿
- **建图阶段 (Mapping)**:
  - 固定相机位姿，优化Gaussians参数
  - 基于关键帧的优化（使用重叠选择）
  - 通过轮廓遮罩添加新Gaussians（densification）
  - 可选的剪枝和梯度密集化

**关键函数：**
- `rgbd_slam(config)`: 主SLAM循环
- `get_loss()`: 计算跟踪/建图损失
- `initialize_first_timestep()`: 初始化第一帧参数
- `add_new_gaussians()`: 基于轮廓添加新Gaussians
- `initialize_camera_pose()`: 使用恒速模型初始化相机位姿
- `get_pointcloud()`: 从RGB-D生成点云

**数据流：**
```
RGB-D数据 → 点云生成 → Gaussian初始化 →
  ↓
  循环 {
    跟踪: 优化相机位姿
    建图: 优化Gaussians参数
    密集化: 添加新Gaussians
  }
  ↓
保存参数 → 评估
```

### 2. `scripts/gaussian_splatting.py`
**纯Gaussian Splatting优化（使用真值位姿）**

不进行SLAM，仅使用已知相机位姿进行3D Gaussian Splatting重建。

**用途：**
- 评估场景重建上限
- 与SplaTAM结果对比
- 新视角合成基准测试

**与splatam.py的区别：**
- 使用真值位姿，不进行位姿估计
- 使用`utils/gs_helpers.py`而非`utils/slam_helpers.py`
- 无跟踪阶段，仅优化Gaussians

### 3. `scripts/post_splatam_opt.py`
**SplaTAM后优化**

在SplaTAM生成的重建结果上进行额外的Gaussian Splatting优化。

**流程：**
1. 加载SplaTAM输出的参数
2. 使用估计的位姿（非真值）
3. 进一步优化Gaussians以提升渲染质量

### 4. `scripts/eval_novel_view.py`
**新视角合成评估**

评估重建质量，通过渲染训练集外的视角并与真值对比。

**评估指标：**
- PSNR (Peak Signal-to-Noise Ratio)
- SSIM (Structural Similarity Index)
- LPIPS (Learned Perceptual Image Patch Similarity)

### 5. `scripts/export_ply.py`
**导出PLY格式点云**

将Gaussian参数转换为标准PLY格式，可在第三方查看器中查看。

**转换内容：**
- 3D位置 (means3D)
- RGB颜色（转换为球谐函数表示）
- 不透明度 (opacities)
- 尺度 (scales)
- 旋转 (rotations)

**支持查看器：**
- SuperSplat
- PolyCam
- 其他支持Gaussian Splatting的查看器

### 6. `scripts/iphone_demo.py`
**iPhone在线演示**

通过NeRFCapture应用实时采集和处理iPhone数据。

### 7. `scripts/nerfcapture2dataset.py`
**NeRFCapture数据集转换**

将NeRFCapture应用采集的数据转换为标准数据集格式。

---

## 配置系统 (configs/)

### 配置结构
配置文件采用**Python模块**格式（非YAML），便于灵活配置和代码复用。

### 按数据集组织
```
configs/
├── data/                 # 数据集YAML配置
│   ├── replica.yaml
│   ├── scannet.yaml
│   └── TUM/
│       ├── freiburg1_desk.yaml
│       └── ...
├── iphone/              # iPhone数据配置
├── replica/             # Replica数据集配置
│   ├── splatam.py      # 标准SplaTAM配置
│   ├── splatam_s.py    # SplaTAM-S变体
│   ├── gaussian_splatting.py
│   ├── post_splatam_opt.py
│   └── replica.bash    # 批处理多场景
├── replica_v2/          # ReplicaV2配置（用于新视角合成）
├── tum/                 # TUM-RGBD配置
├── scannet/             # ScanNet配置
└── scannetpp/           # ScanNet++配置
```

### 配置文件示例结构

```python
config = dict(
    # 基础设置
    workdir="./experiments/Replica",
    run_name="room0_0",
    seed=0,
    primary_device="cuda:0",

    # SLAM参数
    map_every=1,                    # 每N帧执行一次建图
    keyframe_every=5,               # 每N帧选择一个关键帧
    mapping_window_size=24,         # 建图时使用的关键帧数量

    # 跟踪配置
    tracking=dict(
        num_iters=40,               # 跟踪优化迭代次数
        use_gt_poses=False,         # 是否使用真值位姿
        forward_prop=True,          # 是否使用恒速模型前向传播
        use_sil_for_loss=True,      # 是否使用轮廓损失
        sil_thres=0.99,             # 轮廓阈值
        loss_weights=dict(
            im=0.5,                 # RGB损失权重
            depth=1.0,              # 深度损失权重
        ),
        lrs=dict(                   # 学习率
            cam_unnorm_rots=0.0004,
            cam_trans=0.002,
        ),
    ),

    # 建图配置
    mapping=dict(
        num_iters=60,               # 建图优化迭代次数
        add_new_gaussians=True,     # 是否添加新Gaussians
        prune_gaussians=True,       # 是否剪枝Gaussians
        use_gaussian_splatting_densification=False,  # 是否使用梯度密集化
        lrs=dict(                   # 学习率
            means3D=0.0001,
            rgb_colors=0.0025,
            unnorm_rotations=0.001,
            logit_opacities=0.05,
            log_scales=0.001,
        ),
    ),

    # 数据配置
    data=dict(
        basedir="./data/Replica",
        sequence="room0",
        desired_image_height=680,
        desired_image_width=1200,
        start=0,
        end=-1,
        stride=1,
    ),

    # WandB日志
    use_wandb=True,
    wandb=dict(
        entity="your_entity",
        project="SplaTAM",
        group="Replica",
        name="room0_0",
    ),
)
```

---

## 数据加载器 (datasets/)

### 基础架构

#### `datasets/gradslam_datasets/basedataset.py`
**抽象基类 `GradSLAMDataset`**

所有数据集加载器的父类，定义了统一接口。

**核心方法：**
- `__init__()`: 初始化数据集路径、分辨率等
- `__len__()`: 返回数据集帧数
- `__getitem__(idx)`: 返回第idx帧的 (color, depth, intrinsics, pose)
- `get_filepaths()`: 获取所有图像/深度文件路径

**重要功能：**
- 自动调整图像分辨率
- 支持相对位姿（相对于第一帧）
- 处理坏帧（invalid poses）
- 支持训练/测试集分割

#### `datasets/gradslam_datasets/dataconfig.py`
**配置加载器**

- `load_dataset_config(path)`: 从YAML加载数据集配置
- 支持配置继承 (`inherit_from`)
- 递归更新配置字典

#### `datasets/gradslam_datasets/geometryutils.py`
**几何变换工具**

- `relative_transformation()`: 计算相对位姿变换
- SE(3)变换相关函数

#### `datasets/gradslam_datasets/datautils.py`
**数据处理工具**

- 图像读取和预处理
- 深度图处理
- 相机内参处理

### 具体数据集实现

#### `replica.py` - Replica数据集
- **ReplicaDataset**: 标准Replica数据集
- **ReplicaV2Dataset**: 带有训练/测试分割的变体（用于新视角合成）

#### `tum.py` - TUM-RGBD数据集
- 读取TUM格式的RGB-D序列
- 解析`associate.txt`文件（RGB-Depth对应关系）

#### `scannet.py` - ScanNet数据集
- 处理ScanNet扫描数据
- 读取`.sens`文件提取的帧

#### `scannetpp.py` - ScanNet++数据集
- 支持高分辨率DSLR图像
- 需要预处理去畸变

#### `nerfcapture.py` - NeRFCapture (iPhone)数据
- 实时流式数据接收
- 支持LiDAR深度

#### 其他数据集
- `icl.py`: ICL-NUIM数据集
- `azure.py`: Azure Kinect数据
- `realsense.py`: Intel RealSense数据
- `record3d.py`: Record3D应用数据
- `ai2thor.py`: AI2-THOR模拟器数据

---

## 工具模块 (utils/)

### SLAM核心工具

#### `utils/slam_helpers.py`
**SLAM专用辅助函数**

**关键函数：**
- `transform_to_frame()`: 将Gaussians变换到特定帧坐标系
  - 控制是否对Gaussians和相机参数求导
  - 用于跟踪（相机导数）和建图（Gaussians导数）

- `transformed_params2rendervar()`: 准备渲染变量（RGB）
  - 转换参数为渲染器需要的格式

- `transformed_params2depthplussilhouette()`: 准备深度+轮廓渲染变量
  - 用于深度渲染和轮廓检测

- `l1_loss_v1/v2()`: L1损失函数

- `matrix_to_quaternion()`: 旋转矩阵转四元数
  - 来自PyTorch3D，用于真值位姿转换

- `quat_mult()`: 四元数乘法

#### `utils/slam_external.py`
**来自3D Gaussian Splatting的外部代码**

⚠️ **注意**: 此文件代码遵循Gaussian Splatting项目的许可证（非MIT）

**关键函数：**
- `build_rotation(q)`: 从四元数构建旋转矩阵

- `calc_ssim()`: 计算SSIM（结构相似性）
  - 用于RGB损失

- `calc_psnr()`: 计算PSNR

- `prune_gaussians()`: 剪枝Gaussians
  - 移除低不透明度的Gaussians
  - 移除过大的Gaussians

- `densify()`: 梯度驱动的密集化
  - 克隆高梯度Gaussians
  - 分裂大的Gaussians

- `accumulate_mean2d_gradient()`: 累积2D投影梯度
  - 用于密集化判断

#### `utils/keyframe_selection.py`
**关键帧选择**

**核心函数：**
- `keyframe_selection_overlap()`: 基于重叠度选择关键帧

**算法流程：**
1. 从当前帧随机采样像素点（默认1600个）
2. 将像素反投影为3D点云
3. 将3D点云投影到每个关键帧
4. 计算落在图像内的点的比例
5. 选择重叠度最高的K个关键帧

**用途：**
- 建图阶段选择最相关的关键帧进行优化
- 避免使用所有关键帧（提高效率）

### Gaussian Splatting工具

#### `utils/gs_helpers.py`
**Gaussian Splatting专用辅助函数**

与`slam_helpers.py`类似，但用于`scripts/gaussian_splatting.py`（真值位姿场景）。

#### `utils/gs_external.py`
**Gaussian Splatting外部代码**

与`slam_external.py`内容相同，但独立维护以供不同脚本使用。

### 评估与可视化工具

#### `utils/eval_helpers.py`
**评估与进度报告**

**关键函数：**
- `evaluate_ate()`: 计算绝对轨迹误差（ATE）
  - 使用Horn方法对齐轨迹
  - 计算平均平移误差

- `align()`: 使用Horn方法对齐两条轨迹
  - 闭式求解旋转和平移

- `report_loss()`: 向WandB报告损失

- `report_progress()`: 报告训练进度
  - 计算ATE
  - 渲染图像并计算指标（PSNR, SSIM, LPIPS）
  - 上传到WandB

- `eval()`: 最终评估
  - 遍历所有帧
  - 计算轨迹误差
  - 计算渲染质量指标

**评估指标：**
- **ATE**: 绝对轨迹误差
- **PSNR**: 峰值信噪比（越高越好，通常>20dB）
- **SSIM**: 结构相似性（0-1，越接近1越好）
- **LPIPS**: 感知相似性（越低越好，使用AlexNet）
- **MS-SSIM**: 多尺度SSIM
- **Depth L1**: 深度L1误差

#### `utils/recon_helpers.py`
**重建辅助函数**

**核心函数：**
- `setup_camera()`: 创建相机对象
  - 设置内参、外参
  - 转换为OpenGL投影矩阵
  - 返回`GaussianRasterizationSettings`对象

**参数转换：**
- OpenCV坐标系 → OpenGL坐标系
- 相机内参 → 透视投影矩阵

### 其他工具

#### `utils/common_utils.py`
**通用工具函数**

- `seed_everything(seed)`: 设置所有随机种子
  - PyTorch, NumPy, Python random
  - 确保可复现性

- `save_params()`: 保存参数为.npz文件

- `save_params_ckpt()`: 保存检查点

- `params2cpu()`: 将GPU参数转为CPU NumPy数组

#### `utils/graphics_utils.py`
**图形学相关工具**

- 焦距计算
- 视场角转换
- 其他图形学辅助函数

#### `utils/neighbor_search.py`
**邻域搜索**

- K近邻搜索
- 用于Gaussian初始化和密集化

---

## 可视化脚本 (viz_scripts/)

### `viz_scripts/final_recon.py`
**交互式最终重建可视化**

**功能：**
- 加载保存的参数（params.npz）
- 使用Open3D进行交互式3D可视化
- 显示：
  - Gaussian点云（渲染为RGB或深度）
  - 相机轨迹
  - 相机视锥体

**交互控制：**
- 鼠标旋转、缩放视角
- 键盘切换渲染模式（RGB/深度/中心点）
- 实时渲染更新

**配置选项：**
```python
viz=dict(
    render_mode='color',        # 'color', 'depth', 'centers'
    visualize_cams=True,        # 显示相机
    viz_w=600, viz_h=340,       # 渲染分辨率
    view_scale=2,               # 视角缩放
)
```

### `viz_scripts/online_recon.py`
**在线重建可视化**

**功能：**
- 逐帧播放重建过程
- 显示Gaussians的增量添加
- 显示相机运动轨迹
- 可选：播放完成后进入交互模式

**用途：**
- 调试SLAM过程
- 制作演示视频
- 理解系统行为

---

## 自动化脚本 (bash_scripts/)

### 数据集下载脚本

#### `download_replica.sh`
下载Replica数据集（由NICE-SLAM托管）

#### `download_tum.sh`
下载TUM-RGBD数据集

#### `download_replicav2.sh`
下载ReplicaV2数据集（vMAP版本，用于新视角合成）

### 运行脚本

#### `online_demo.bash`
启动iPhone在线演示
```bash
bash bash_scripts/online_demo.bash configs/iphone/online_demo.py
```

#### `nerfcapture.bash`
离线处理NeRFCapture数据
```bash
bash bash_scripts/nerfcapture.bash configs/iphone/nerfcapture.py
```

#### `nerfcapture2dataset.bash`
仅采集数据（不运行SLAM）
```bash
bash bash_scripts/nerfcapture2dataset.bash configs/iphone/dataset.py
```

#### `start_docker.bash`
启动Docker容器

---

## 外部依赖

### `diff-gaussian-rasterization-w-depth.git/`
**自定义Gaussian光栅化库（Git子模块）**

这是3D Gaussian Splatting渲染器的修改版，添加了深度输出。

**来源**: https://github.com/JonathonLuiten/diff-gaussian-rasterization-w-depth

**功能：**
- 将Gaussians光栅化为2D图像
- 输出RGB、深度、轮廓
- 提供可微分梯度用于优化

**输出：**
- **RGB**: 3通道彩色图像
- **Depth**: 深度图
- **Silhouette**: 轮廓/存在性遮罩
- **Depth²**: 深度平方（用于不确定性估计）

**使用：**
```python
from diff_gaussian_rasterization import GaussianRasterizer as Renderer

renderer = Renderer(raster_settings=cam)
rgb, radius, _ = renderer(**rendervar)
```

---

## 数据流与模块交互

### 完整SLAM流程

```
                    [数据集加载器]
                          ↓
                    RGB-D + 位姿
                          ↓
              ┌───────────┴───────────┐
              ↓                       ↓
        [第一帧初始化]          [后续帧处理]
              ↓                       ↓
        点云生成              ┌──────┴──────┐
              ↓                ↓             ↓
        Gaussian初始化    [跟踪阶段]   [建图阶段]
              ↓                ↓             ↓
        参数准备          位姿优化    Gaussians优化
              ↓                ↓             ↓
              └────────────────┴─────────────┘
                          ↓
                   [密集化/剪枝]
                          ↓
                   添加新Gaussians
                          ↓
                    [下一帧...]
                          ↓
                    保存参数/评估
```

### 模块依赖关系

```
scripts/splatam.py
    ├─ datasets/gradslam_datasets/*
    │   └─ 数据加载
    ├─ utils/slam_helpers.py
    │   └─ 变换、损失函数
    ├─ utils/slam_external.py
    │   └─ 旋转、SSIM、剪枝、密集化
    ├─ utils/keyframe_selection.py
    │   └─ 关键帧选择
    ├─ utils/recon_helpers.py
    │   └─ 相机设置
    ├─ utils/eval_helpers.py
    │   └─ 评估、进度报告
    ├─ utils/common_utils.py
    │   └─ 种子、保存参数
    └─ diff_gaussian_rasterization
        └─ Gaussian渲染器
```

### 参数传递流程

```
配置文件 (config.py)
    ↓
实验对象 (experiment.config)
    ↓
rgbd_slam(config)
    ↓
初始化参数 (params)
    - means3D
    - rgb_colors
    - unnorm_rotations
    - logit_opacities
    - log_scales
    - cam_unnorm_rots
    - cam_trans
    ↓
优化器 (optimizer)
    ↓
损失计算 (get_loss)
    ↓
反向传播 + 更新
    ↓
保存 (params.npz)
```

---

## 关键数据结构

### Gaussian参数 (params)

```python
params = {
    # Gaussians属性 (N个Gaussians)
    'means3D': Tensor[N, 3],           # 3D位置
    'rgb_colors': Tensor[N, 3],        # RGB颜色 [0, 1]
    'unnorm_rotations': Tensor[N, 4],  # 未归一化四元数
    'logit_opacities': Tensor[N, 1],   # logit空间不透明度
    'log_scales': Tensor[N, 1或3],     # log空间尺度（各向同性/各向异性）

    # 相机轨迹 (T帧)
    'cam_unnorm_rots': Tensor[1, 4, T],  # 未归一化四元数
    'cam_trans': Tensor[1, 3, T],        # 平移

    # 元数据
    'timestep': Tensor[N],              # Gaussian添加时间
    'intrinsics': ndarray[3, 3],        # 相机内参
    'w2c': ndarray[4, 4],               # 第一帧世界到相机变换
    'gt_w2c_all_frames': ndarray[T, 4, 4],  # 真值位姿
    'keyframe_time_indices': ndarray[K],    # 关键帧索引
}
```

### 变量 (variables)

```python
variables = {
    'max_2D_radius': Tensor[N],           # 每个Gaussian最大2D半径
    'means2D_gradient_accum': Tensor[N],  # 累积2D投影梯度
    'denom': Tensor[N],                   # 梯度累积计数
    'timestep': Tensor[N],                # Gaussian添加时间
    'scene_radius': float,                # 场景半径估计
    'means2D': Tensor[N, 2],              # 当前帧2D投影（用于密集化）
    'seen': Tensor[N],                    # 当前帧可见性
}
```

### 渲染变量 (rendervar)

```python
rendervar = {
    'means3D': Tensor[N, 3],
    'means2D': Tensor[N, 2],              # 预留（由渲染器计算）
    'colors_precomp': Tensor[N, 3],       # 预计算颜色
    'rotations': Tensor[N, 4],            # 归一化四元数
    'opacities': Tensor[N, 1],            # Sigmoid后的不透明度
    'scales': Tensor[N, 3],               # Exp后的尺度
}
```

### 数据帧 (curr_data)

```python
curr_data = {
    'cam': GaussianRasterizationSettings,  # 相机对象
    'im': Tensor[3, H, W],                 # RGB图像 [0, 1]
    'depth': Tensor[1, H, W],              # 深度图
    'id': int,                             # 帧索引
    'intrinsics': Tensor[3, 3],            # 相机内参
    'w2c': Tensor[4, 4],                   # 世界到相机变换
    'iter_gt_w2c_list': List[Tensor],      # 真值位姿列表
}
```

---

## 完整 SLAM 主循环详解（逐步说明）

下面按 `rgbd_slam()` 中每帧的实际执行顺序展开，结合关键代码行注释。

---

### 第一帧初始化（`time_idx == 0`）

```
initialize_first_timestep()
  ├─ 从第一帧 RGB-D 生成原始点云        get_pointcloud()
  │    深度反投影公式:
  │    pts_cam = [x = (u - cx)/fx * d,
  │               y = (v - cy)/fy * d,
  │               z = d]
  │    再通过 c2w = inv(w2c) 变换到世界坐标系
  │
  ├─ 初始化 N 个 Gaussians              initialize_params()
  │    means3D   = 点云 XYZ
  │    rgb_colors = 点云颜色
  │    unnorm_rotations = [1,0,0,0] * N  (单位四元数)
  │    logit_opacities  = 0              (sigmoid → 0.5)
  │    log_scales = log(sqrt(d / f_avg)) (投影几何估算半径)
  │    所有参数包装为 nn.Parameter (requires_grad=True)
  │
  ├─ 初始化相机轨迹张量
  │    cam_unnorm_rots: [1, 4, num_frames]  ← 全部单位四元数
  │    cam_trans:       [1, 3, num_frames]  ← 全部零向量
  │
  └─ 设置场景半径 scene_radius = max(depth) / scene_radius_depth_ratio
```

---

### 每帧主循环（`time_idx > 0`）

#### 步骤 1：相机位姿初始化

```python
# splatam.py:676
params = initialize_camera_pose(params, time_idx, forward_prop=...)
```

| 条件 | 操作 |
|------|------|
| `time_idx == 1` 或 `forward_prop=False` | 直接复制前一帧位姿作为初始值 |
| `time_idx > 1` 且 `forward_prop=True` | **恒速模型**：新位姿 = 前帧 + (前帧 - 前前帧) |

恒速模型公式（四元数 + 平移各自独立外推）：
```
q_new  = normalize(q_{t-1} + (q_{t-1} - q_{t-2}))
t_new  = t_{t-1} + (t_{t-1} - t_{t-2})
```

---

#### 步骤 2：相机跟踪（Tracking）

```
splatam.py:680–746
```

**核心思路**：固定所有 Gaussians 参数，仅对当前帧的 `cam_unnorm_rots[t]` 和 `cam_trans[t]` 求导优化。

```
创建独立优化器 (仅包含 cam_unnorm_rots/cam_trans 的当前帧切片)
记录 best_loss = ∞, best_rot, best_trans

for iter in range(num_iters_tracking):   # 通常 10–80 次
    ① transform_to_frame(gaussians_grad=False, camera_grad=True)
       把所有 Gaussian 从世界坐标系变换到当前相机坐标系
       仅相机位姿参数保留梯度

    ② Renderer() → im(渲染RGB), depth(渲染深度), silhouette(轮廓)

    ③ 构建损失掩码:
       mask = (gt_depth > 0)
       if ignore_outlier_depth_loss:
           depth_error = |gt_depth - render_depth|
           mask &= (depth_error < 10 * median(depth_error))
       if use_sil_for_loss:
           mask &= (silhouette > sil_thres)  ← 只在已有 Gaussian 覆盖区域计算

    ④ L_track = λ_depth * Σ|D_gt - D_render|[mask]
              + λ_rgb  * Σ|I_gt - I_render|[mask]

    ⑤ loss.backward() → optimizer.step()

    ⑥ if loss < best_loss:
           best_loss = loss
           保存当前 cam_unnorm_rots[t], cam_trans[t] 副本

结束后：强制写回 best_rot, best_trans（非最后一次梯度步）
```

**为什么要保留最优候选**：跟踪优化可能过冲（overshoot），最后一次迭代不一定是最优位姿，保留所有迭代中损失最小的结果更鲁棒。

**深度损失使用 sum 而非 mean**：相比建图阶段的 mean，跟踪用 sum 使损失对帧内遮罩大小敏感，有助于在轮廓外区域覆盖度不足时惩罚更重。

---

#### 步骤 3：轮廓驱动 Gaussian 增密（Densification）

触发条件：`time_idx % map_every == 0` 且 `add_new_gaussians=True`

```python
# splatam.py:793–796
add_new_gaussians(params, variables, densify_curr_data, sil_thres, time_idx, ...)
```

```
渲染当前帧轮廓 silhouette[H, W]
渲染当前帧深度 render_depth[H, W]

non_presence_mask = (silhouette < sil_thres)          ← 未被 Gaussian 覆盖的像素
                  | (render_depth > gt_depth           ← Gaussian 挡住了更近的物体
                     AND depth_error > 50*median)

对 non_presence_mask 中有效深度的像素:
  get_pointcloud() → 反投影到世界坐标系 → 新点云
  initialize_new_params() → 新 Gaussian 参数
  torch.cat() 拼接到已有 params 上
```

每次增密后 variables（gradient_accum、max_2D_radius 等）也随之扩充。

---

#### 步骤 4：关键帧选择

```python
# splatam.py:810–819
selected_keyframes = keyframe_selection_overlap(depth, curr_w2c, intrinsics,
                                                keyframe_list[:-1], num_keyframes)
# 然后强制加入最新关键帧 + 当前帧
```

重叠度计算流程（`utils/keyframe_selection.py`）：
```
① 从当前帧深度图随机采样 1600 个像素
② 反投影到 3D 世界坐标 (pts_world)
③ for each candidate_keyframe:
       pts_cam = w2c_kf @ pts_world
       project → (u, v)
       overlap = # of (u,v) within [0,W] x [0,H] / 1600
④ 按 overlap 降序取前 (mapping_window_size - 2) 帧
```

最终建图关键帧集合 = `selected_keyframes` + `keyframe_list[-1]` + `current_frame`

---

#### 步骤 5：建图（Mapping）

```
splatam.py:826–893
```

```
创建新优化器 (包含所有 Gaussian 参数，cam 参数 lr=0)

for iter in range(num_iters_mapping):   # 通常 10–60 次
    ① 随机从 selected_keyframes 中选 1 帧 (包括当前帧)
       ← 每次迭代换不同视角，防止过拟合单视角

    ② transform_to_frame(gaussians_grad=True, camera_grad=False)

    ③ Renderer() → im, depth, silhouette

    ④ L_map = λ_depth * mean|D_gt - D_render|[mask]
            + λ_rgb  * (0.8 * L1(I) + 0.2 * (1 - SSIM(I)))
                      ↑ 建图用 SSIM 组合损失，跟踪只用 L1

    ⑤ loss.backward()

    ⑥ [可选] prune_gaussians()
       移除 opacity < threshold 或尺度过大的 Gaussians

    ⑦ [可选] densify() (梯度密集化)
       累积 means2D 梯度，克隆/分裂高梯度 Gaussians

    ⑧ optimizer.step()
```

---

#### 步骤 6：关键帧入库

```python
# splatam.py:914–927
# 每 keyframe_every 帧选一帧存入 keyframe_list
# 同时保存: id, est_w2c, color, depth
```

---

#### 步骤 7：检查点保存

```python
# splatam.py:930–933
if time_idx % checkpoint_interval == 0:
    save_params_ckpt(params, output_dir, time_idx)
    np.save(f"keyframe_time_indices{time_idx}.npy", keyframe_time_indices)
```

---

## IMU 辅助旋转初始化（wheeltec_online_slam.py）

> **注意**：标准 `splatam.py`（离线模式）不使用 IMU，IMU 仅在 `wheeltec_online_slam.py` 的在线模式中实现。

### 触发条件

配置中设置 `use_imu_for_propagation=True` 且 ROS2 `/camera/gyro_accel/sample` 话题正常发布（~100 Hz）。

### IMU 数据流

```
ROS2 /camera/gyro_accel/sample (~100 Hz)
       ↓
_imu_callback()
       ↓
_imu_buffer (deque, maxlen=500, 约5秒缓存)
每条记录: {'ts': float, 'gyro': [ωx, ωy, ωz] rad/s}
```

### 帧间旋转积分（Rodrigues 公式）

```python
# wheeltec_online_slam.py:256–281
def integrate_rotation(t_start, t_end) -> np.ndarray (3×3):
    # 筛选时间窗口内的陀螺仪测量
    window = [m for m in _imu_buffer if t_start < m['ts'] <= t_end]

    R = I(3×3)
    for m in window:
        dt = m['ts'] - prev_ts
        ω  = m['gyro']                     # rad/s
        θ  = |ω| * dt                      # 转过的角度
        axis = ω / |ω|                     # 旋转轴
        K = skew_symmetric(axis)           # 反对称矩阵
        dR = I + sin(θ)*K + (1-cos(θ))*K²  # Rodrigues 旋转矩阵
        R = R @ dR
    return R  # 从 t_start 到 t_end 的增量旋转
```

### 用于位姿初始化

```python
# wheeltec_online_slam.py:529–537
# 在恒速模型之后，用 IMU 的 dR 覆盖旋转分量
if imu_dR is not None:
    R_w2c_prev = build_rotation(prev_rot_quat)        # 前帧旋转矩阵
    R_w2c_new  = imu_dR.T @ R_w2c_prev               # imu_dR^T = camera-frame delta
    params['cam_unnorm_rots'][..., t] = matrix_to_quaternion(R_w2c_new)
```

**为什么用 `imu_dR.T`**：陀螺仪积分得到的 `dR` 是 body（相机）坐标系下的旋转增量，对应 `c2w` 方向的变化。而系统存的是 `w2c`，所以需要转置。

### IMU vs. 纯恒速模型对比

| | 恒速模型（splatam.py） | IMU辅助（wheeltec_online_slam.py） |
|---|---|---|
| 旋转初始化 | 四元数线性外推 | 陀螺仪积分（更准确） |
| 平移初始化 | 线性外推 | 仍用线性外推（无加速度计积分） |
| 适用场景 | 运动平稳 | 快速旋转/手持抖动 |
| 依赖 | 无外部传感器 | 需要 ROS2 IMU 话题 |

### 轮式里程计辅助（可选）

配置 `use_odom_init=True` 时，还会订阅 `/odom`：
```
/odom → _odom_callback() → _latest_odom (4×4 变换矩阵)
```
目前里程计数据随帧一起打包进 `frame['odom']`，可供未来扩展使用（当前版本中旋转初始化优先用 IMU，平移初始化仍依赖恒速模型）。

---

## 重要算法详解

### 1. 损失函数对比：跟踪 vs 建图

| 项目 | 跟踪（Tracking） | 建图（Mapping） |
|------|------|------|
| RGB 损失 | `sum(|I_gt - I_render|[mask])` | `0.8*L1 + 0.2*(1-SSIM)` |
| 深度损失 | `sum(|D_gt - D_render|[mask])` | `mean(|D_gt - D_render|[mask])` |
| 轮廓掩码 | 可选（use_sil_for_loss） | 不用 |
| 异常深度过滤 | 可选（ignore_outlier_depth_loss） | 可选 |
| 优化对象 | 相机位姿 | Gaussian 参数 |

### 2. Gaussian 剪枝（prune_gaussians）

**触发**：建图每次迭代内（在 `loss.backward()` 之后，`optimizer.step()` 之前）

**移除条件**：
- `opacity < removal_opacity_threshold`（通常 0.005–0.02）
- 超出 `scene_radius` 范围的 Gaussian（防止浮动噪点）
- 达到 `stop_after` 迭代次数后停止剪枝

### 3. 梯度密集化（densify，可选）

**流程**：
```
累积每次迭代的 means2D.grad → means2D_gradient_accum
grad_mean2D = gradient_accum / denom

for each Gaussian with grad_mean2D > grad_thresh:
    if scale < scene_radius * 0.05:  克隆 (clone)
    else:                             分裂 (split into 2)
```

**与轮廓密集化的区别**：
- 轮廓密集化：基于渲染覆盖度，在图像空洞处补充新 Gaussian（每 `map_every` 帧一次）
- 梯度密集化：基于优化梯度，在已有 Gaussian 细节不足处加密（每次建图迭代内）

### 4. 关键帧选择（keyframe_selection_overlap）

**重叠度计算**:
1. 从当前帧随机采样像素 → 反投影为 3D 点（使用当前帧估计位姿）
2. 将 3D 点投影到每个候选关键帧的图像平面
3. 计算落在 `[0,W] × [0,H]` 内的点比例 = 重叠度
4. 取重叠度最高的 `mapping_window_size - 2` 帧

**组合策略**：重叠选帧 + 强制加最新关键帧 + 当前帧，确保局部一致性。

---

## 文件读写格式

### params.npz
**保存的Gaussian和相机参数**

格式: NumPy压缩数组

包含字段:
- 所有Gaussian参数
- 相机轨迹
- 元数据（内参、第一帧w2c、真值位姿等）

读取:
```python
params = dict(np.load("params.npz", allow_pickle=True))
```

### paramsN.npz
**检查点文件**

N = 帧索引

与params.npz格式相同，但对应特定帧的状态。

### keyframe_time_indicesN.npy
**关键帧索引列表**

格式: NumPy数组

记录哪些帧被选为关键帧。

### splat.ply
**导出的PLY点云**

格式: PLY (Polygon File Format)

包含:
- 顶点位置 (x, y, z)
- 法向量 (nx, ny, nz) - 通常为零
- 球谐函数颜色 (f_dc_0, f_dc_1, f_dc_2)
- 不透明度 (opacity)
- 尺度 (scale_0, scale_1, scale_2)
- 旋转四元数 (rot_0, rot_1, rot_2, rot_3)

---

## 论文核心理论（Paper: SplaTAM, arXiv 2312.02126）

### 3D Gaussian 表示

每个 Gaussian 仅用 **8 个参数**描述（相比原版 3DGS 更简洁）：

| 参数 | 含义 | 维度 |
|------|------|------|
| **c** | RGB 颜色（view-independent） | 3 |
| **μ** | 世界坐标系中心位置 | 3 |
| **r** | 球形半径（各向同性）| 1 |
| **o** | 不透明度 ∈ [0, 1] | 1 |

**各向同性设计**的好处：参数更少，渲染更快，内存减少 57.5%（vs 各向异性），SLAM 场景下精度损失可忽略（ATE 0.55cm vs 0.57cm）。

---

### 可微分渲染公式（论文 Eq. 1–5）

渲染按深度由近到远对所有 Gaussian 做 alpha 合成：

**2D 投影**（world → image plane）：
```
μ^2D = K * E_t * μ / d        # 中心投影
r^2D = f * r / d               # 半径投影（d = 深度，f = 焦距）
```

**单像素权重**（每个 Gaussian 对像素 p 的贡献）：
```
f_i(p) = o_i * exp(-||p - μ_i^2D||² / (2 * r_i^2D²))
```

**颜色渲染**（alpha 合成，前向遮挡）：
```
C(p) = Σ_i  c_i * f_i(p) * Π_{j<i}(1 - f_j(p))
```

**深度渲染**（加权深度）：
```
D(p) = Σ_i  d_i * f_i(p) * Π_{j<i}(1 - f_j(p))
```

**轮廓渲染**（累积不透明度，衡量地图覆盖程度）：
```
S(p) = Σ_i  f_i(p) * Π_{j<i}(1 - f_j(p))
```

`S(p) ≈ 1` 表示该像素已被 Gaussian 充分覆盖；`S(p) ≈ 0` 表示地图空洞。

> 深度平方 D²(p) 也同步渲染，用于计算不确定性 σ² = D² - D²（代码中 `depth_sil[2]`）。

---

### 相机跟踪损失（论文 Eq. 8）

```
L_t = Σ_p  [S(p) > 0.99] * (L1(D(p)) + 0.5 * L1(C(p)))
```

**关键设计**：
- **轮廓掩码** `[S(p) > 0.99]`：只在地图已充分覆盖的像素上计算损失，避免"新区域"干扰跟踪
- **颜色权重 0.5**：深度是绝对几何约束（权重 1.0），RGB 是补充约束
- 轮廓阈值 0.99（非 0.5）是关键：阈值 0.5 时 ATE 为 1.38cm，0.99 时为 **0.27cm**（5× 提升）

---

### Gaussian 增密掩码（论文 Eq. 9）

```
M(p) = (S(p) < 0.5)                               # 地图未覆盖
      + (D_GT(p) < D(p)) * (L1(D(p)) > λ * MDE)  # 前景遮挡
```

- `λ = 50`，MDE = 当前帧深度误差中位数
- 两个条件的并集：地图空洞 OR 有新前景物体出现

**初始化半径**（论文 Eq. 6）：
```
r = D_GT / f      # 深度 / 焦距 = 投影到图像上约 1 像素大小
```

---

### 各模块的实际耗时（RTX 3080 Ti，1200×980）

| 模块 | 每次迭代 | 每帧 |
|------|----------|------|
| 跟踪（40 次迭代） | **25 ms** | 1.00 s |
| 建图（60 次迭代） | **24 ms** | 1.44 s |
| 总计（离线） | — | **~2.5 s/帧** |

对比：NICE-SLAM 每帧 2.04s（跟踪）+ 4.50s（建图），Point-SLAM 0.76s + 4.50s。

**SplaTAM-S**（精简版，10 + 15 次迭代）：**0.19s 跟踪 + 0.33s 建图**，适合 Jetson 等嵌入式设备。

---

### 消融实验关键结论（Replica/Room 0, ATE RMSE）

**跟踪消融**（Table 5）：

| 恒速传播 | 轮廓掩码 | 轮廓阈值 | ATE (cm) | Depth L1 (cm) | PSNR (dB) |
|----------|----------|----------|----------|---------------|-----------|
| ✗ | ✗ | 0.99 | 2.95 | 2.15 | 25.40 |
| ✓ | ✗ | 0.99 | 115.80 | ✗（跟踪失败）| — |
| ✓ | ✓ | 0.5 | 1.38 | 12.58 | 31.30 |
| ✓ | ✓ | **0.99** | **0.27** | **0.49** | **32.81** |

**结论**：
1. **恒速模型是必要的**（但若没有轮廓掩码则会发散）
2. **轮廓掩码 + 高阈值 0.99 是核心**，缺一不可
3. 无轮廓掩码时恒速模型反而更差（位姿初始化更激进但损失无法正确引导）

**颜色/深度消融**（Table 4）：
- 只用深度：跟踪完全失败（L1 深度无法提供 x-y 方向约束）
- 只用颜色：能跟踪但 ATE 高 5×（缺少绝对尺度）
- 颜色 + 深度：**最优**

---

## 性能优化建议

### 1. 多分辨率策略
在配置中设置不同分辨率:
```python
data=dict(
    desired_image_height=680,        # 建图分辨率
    desired_image_width=1200,
    tracking_image_height=340,       # 跟踪分辨率（更快）
    tracking_image_width=600,
    densification_image_height=680,  # 密集化分辨率
    densification_image_width=1200,
)
```

### 2. 调整优化迭代次数
```python
tracking=dict(num_iters=40),  # 减少跟踪迭代 → 更快
mapping=dict(num_iters=60),   # 增加建图迭代 → 更高质量
```

### 3. 控制建图频率
```python
map_every=5,  # 每5帧建图一次（而非每帧）
```

### 4. 禁用梯度密集化
```python
mapping=dict(
    use_gaussian_splatting_densification=False,  # 更快但质量略低
)
```

---

## 常见问题排查

### GPU内存不足
1. 降低图像分辨率
2. 减少mapping_window_size
3. 启用更激进的剪枝
4. 禁用梯度密集化

### 跟踪失败
1. 增加tracking迭代次数
2. 调整loss_weights（增加depth权重）
3. 启用use_sil_for_loss
4. 检查forward_prop设置

### 重建质量差
1. 增加mapping迭代次数
2. 调整add_new_gaussians阈值
3. 启用梯度密集化
4. 增加keyframe_every频率

---

## 代码风格与约定

1. **张量维度约定**:
   - RGB图像: [3, H, W]
   - 深度图: [1, H, W]
   - 相机位姿: [4, 4] (world-to-camera)
   - 四元数: [w, x, y, z] (实部在前)

2. **参数命名**:
   - `w2c`: world-to-camera变换
   - `c2w`: camera-to-world变换
   - `unnorm_*`: 未归一化的参数
   - `logit_*`: logit空间的参数
   - `log_*`: log空间的参数

3. **模块组织**:
   - `*_helpers.py`: 辅助函数
   - `*_external.py`: 外部代码（可能有不同许可证）
   - `*_utils.py`: 通用工具

4. **配置约定**:
   - 使用Python字典而非YAML（更灵活）
   - 分层组织（tracking, mapping, data, wandb等）
   - 场景特定配置继承通用配置
