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

## 重要算法详解

### 1. 跟踪阶段优化

**目标**: 估计当前帧相机位姿

**固定参数**: Gaussians (means3D, rgb_colors, etc.)

**优化参数**: cam_unnorm_rots[:, :, t], cam_trans[:, :, t]

**损失函数**:
```
L_track = λ_rgb * L1(I_render, I_gt) + λ_depth * L1(D_render, D_gt)
```

**可选遮罩**:
- 轮廓遮罩: 仅计算Gaussians覆盖区域的损失
- 深度异常值遮罩: 排除深度误差过大的像素

### 2. 建图阶段优化

**目标**: 优化Gaussians参数

**固定参数**: 相机位姿 (cam_unnorm_rots, cam_trans)

**优化参数**: means3D, rgb_colors, unnorm_rotations, logit_opacities, log_scales

**损失函数**:
```
L_map = λ_rgb * (0.8 * L1(I) + 0.2 * (1 - SSIM(I))) + λ_depth * L1(D)
```

**优化策略**:
- 随机选择关键帧进行优化
- 每次迭代优化一个关键帧
- 关键帧通过重叠度选择

### 3. Gaussian密集化

**基于轮廓的添加**:
1. 渲染当前帧轮廓
2. 找到轮廓值 < 阈值的像素（未被覆盖）
3. 从这些像素生成新点云
4. 初始化新Gaussians并添加到场景

**基于梯度的密集化** (可选):
1. 累积Gaussians的2D投影梯度
2. 克隆高梯度小Gaussians
3. 分裂高梯度大Gaussians

### 4. Gaussian剪枝

**条件**:
- 不透明度 < 阈值（通常0.005）
- 尺度过大（超出场景范围）
- 在某些迭代后定期剪枝

### 5. 关键帧选择

**重叠度计算**:
1. 从当前帧采样像素 → 3D点云
2. 投影到每个候选关键帧
3. 计算落在图像内的点的比例
4. 选择重叠度最高的K帧

**优点**:
- 自动选择相关视角
- 避免使用所有关键帧（节省计算）

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
