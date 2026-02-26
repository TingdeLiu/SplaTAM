# Wheeltec 机器人资料参考文档

本文档整理了 Wheeltec 机器人系统中可能有用的配置文件、Launch文件和相关文档。

## 当前配置

**车型**：senior_4wd_bs（高级四驱版）
**深度相机**：Astra Stereo S（奥比中光双目立体相机）
**激光雷达**：M10P/M10P-PHY（360°TOF激光雷达）

### 传感器快速参考

| 传感器 | 型号 | 关键参数 |
|--------|------|----------|
| **深度相机** | Astra Stereo S | 深度范围：0.4-4.0m<br>分辨率：640×480@30FPS<br>FOV：H58.4°×V45.5°<br>精度：±1-3mm@1m |
| **激光雷达** | M10P/M10P-PHY | 测距范围：0.05-30m<br>扫描角度：360°<br>精度：±3cm<br>频率：12Hz |
| **底盘** | Senior 4WD BS | 轮径：152mm<br>轮距：312.7mm<br>最大速度：2.7m/s<br>负载：12kg |

## 目录

1. [车型规格参数](#车型规格参数)
2. [机械尺寸](#机械尺寸)
3. [激光雷达规格](#激光雷达规格)
4. [相机配置](#相机配置)
5. [TF变换配置](#tf变换配置)
6. [Launch文件说明](#launch文件说明)
7. [URDF机器人描述](#urdf机器人描述)
8. [导航和建图](#导航和建图)
9. [Wheeltec官方文档](#wheeltec官方文档)

---

## 车型规格参数

### Senior_4wd_bs（高级四驱版）详细规格

| 参数 | 数值 |
|------|------|
| **负载能力** | 12kg |
| **最大速度** | 2.7m/s |
| **产品自重** | 13.3kg |
| **默认尺寸** | 486×523×542mm (长×宽×高) |
| **驱动轮** | 直径152mm越野轮 |
| **悬挂系统** | 共轴摆式悬挂 |
| **电源** | 24V 6000mAh磷酸铁锂电池 + 带3C认证25.55V快充充电器 |
| **电池续航能力** | 约5.5小时 (负载3kg) |
| **电机** | MD36L 60W 直流有刷电机 |
| **减速比** | 1:27 |
| **编码器** | 500线 B磁阻效应AB相高精度编码器 |

### 控制方式

- APP (蓝牙或WiFi)
- 多模智控手柄
- CAN总线
- 串口
- USB (转串口)

### ROS功能套餐

- 导航
- 建图
- 避障
- 图传
- 完整的ROS镜像和源码

---

## 机械尺寸

### Senior_4wd_bs 机械尺寸 (带机械臂配置)

**整体尺寸**：
- 总长：486mm
- 总高：541.69mm
- 总宽：522.58mm

**底盘参数**：
- 轮距（左右轮中心距）：312.7mm
- 轮径：Φ152mm
- 底盘高度：382.5mm

**重要坐标点**（用于TF配置）：
- base_footprint 到 base_link 的Z轴高度：**0.04994m** (见TF变换配置章节)

**参考图纸**：`data/小车二维机械图.png`

---

## 激光雷达规格

### M10P/M10P-PHY 360°激光雷达

**基本参数**：
| 参数 | 数值 |
|------|------|
| **型号** | M10P/M10P-PHY |
| **类型** | 近距离、中距离 |
| **测距原理** | TOF (Time of Flight) |
| **应用场景** | 室内外通用 |
| **扫描角度** | 360° |

**性能参数**：
| 参数 | 数值 |
|------|------|
| **输出数据分辨率** | 1mm |
| **测量距离精度** | ±3cm |
| **最小测量距离** | 0.05m (5cm) |
| **测量半径** | 白色物体：30m / 黑色物体：12m |
| **测量/采样率** | 20000次/s 或 10000次/s |
| **角度分辨率** | 0.22° 或 0.36° |
| **扫描频率** | 12Hz 或 10Hz |
| **抗环境光强度** | 100KLux |

**硬件规格**：
| 参数 | 数值 |
|------|------|
| **外形尺寸** | 直径80mm × 高40mm |
| **重量** | 约210g |
| **光源** | 905nm激光 |
| **电源** | 5VDC |
| **驱动方式** | 内置无刷电机 |
| **防护等级** | IP65 |
| **工作温度** | -10℃ ~ 50℃ |
| **存储温度** | -40℃ ~ 80℃ |

**软件支持**：
- **ROS支持**：ROS1/ROS2
- **WINDOWS**：提供上位机软件
- **STM32**：提供数据采集例程和滤波代码
- **Python**：支持Python 2.7和3.0，兼容Windows和Ubuntu
- **数据内容**：距离、角度

---

## 相机配置

### Astra Stereo S 相机（当前配置）

**型号**：Astra Stereo S（奥比中光双目立体深度相机）

#### 技术规格

**深度性能**：
| 参数 | 数值 |
|------|------|
| **深度范围** | 0.4-4.0米（实测） |
| **精度** | 1m处：±1-3mm |
| **深度FOV** | 水平58.4° × 垂直45.5° |
| **深度图分辨率** | 1280×1024@7FPS<br>640×480@30FPS<br>320×240@30FPS<br>160×120@30FPS |
| **延迟** | 30-45ms |

**彩色图像**：
| 参数 | 数值 |
|------|------|
| **彩色FOV** | 水平63.10° × 垂直49.4° |
| **彩色图分辨率** | 1280×960@7FPS<br>640×480@30FPS<br>320×240@30FPS |

**硬件规格**：
| 参数 | 数值 |
|------|------|
| **尺寸** | 165mm(长) × 40mm(厚) × 30mm(高) |
| **功耗** | <2W，峰值电流<500mA |
| **数据传输** | USB 2.0或以上 |
| **供电方式** | USB供电 |
| **工作温度** | 10°C ~ 40°C |
| **安全性** | Class1激光 |

**音频功能**：
- 双声道立体声麦克风

**系统支持**：
- Android / Linux / Windows 7/8/10 / ROS

**Stereo S 特有功能**：
- 双IR相机配置，支持立体视觉
- 可通过服务 `/camera/switch_ir_camera` 切换左右IR相机

---

### Astra 相机系列

Wheeltec 机器人支持奥比中光（Orbbec）Astra 系列深度相机。

#### 支持的相机型号

在 `turn_on_wheeltec_robot/launch/wheeltec_camera.launch` 中定义：

- **Astra_S** - 基础款深度相机（默认）
- **Astra Stereo S** - 双目立体深度相机（当前配置）
- **Astra_Pro** - 专业版
- **Astra_Pro_Plus** - 专业增强版
- **Astra_Dabai** - 大白系列
- **Astra_Gemini** - Gemini Pro 相机
- **RgbCam** - 仅使用RGB相机
- **组合模式** - 例如 `Astra_S+RgbCam`（同时使用深度相机和RGB相机）

#### 相机 Launch 文件

**主要启动文件**：`turn_on_wheeltec_robot/launch/wheeltec_camera.launch`

参数说明：
```xml
<arg name="camera_mode" default="Astra_S" />
<arg name="if_usb_cam" default="false" />
```

- `camera_mode`: 选择相机型号
- `if_usb_cam`:
  - `false` - 启动深度相机（默认）
  - `true` - 优先启动RgbCam相机（Astra-S除外），如果没有则启动深度相机的RGB功能

**Astra相机驱动文件位置**：`ros_astra_camera/launch/`

常用launch文件：
- `astra.launch` - Astra S 相机
- `stereo_s.launch` - Astra Stereo S 相机（当前配置，带UVC支持）
- `astrapro.launch` - Astra Pro 相机
- `astraproplus.launch` - Astra Pro Plus 相机
- `dabai_u3.launch` - Dabai 相机
- `gemini.launch` - Gemini Pro 相机
- `multi_astra.launch` - 多相机配置

#### 相机标定文件

**标定文件默认保存路径**（来自 `ros_astra_camera/launch/astra.launch`）：

```
file://${ROS_HOME}/camera_info/${NAME}.yaml
```

其中 `${NAME}` 的格式为 `[rgb|depth]_[serial#]`，例如 `depth_B00367707227042B`

**相机标定参数**：
- `rgb_camera_info_url` - RGB相机标定文件URL（默认为空，使用默认路径）
- `depth_camera_info_url` - 深度相机标定文件URL（默认为空，使用默认路径）

#### 相机参数配置

在 `ros_astra_camera/launch/astra.launch` 中的默认参数：

```xml
<arg name="depth_registration" default="true" />  <!-- 硬件深度对齐 -->
<arg name="color_depth_synchronization" default="false" />  <!-- 颜色深度同步 -->
<arg name="auto_exposure" default="true" />  <!-- 自动曝光 -->
<arg name="auto_white_balance" default="true" />  <!-- 自动白平衡 -->
```

#### 相机话题（Topics）

**重要话题**：
- `*/image_raw` - 深度/RGB/IR 原始图像
- `*/image_rect_raw` - 经过标定矫正的图像
- `*/camera_info` - 相机内参/外参信息
- `/camera/depth/points` - 不带颜色的点云
- `/camera/depth_registered/points` - 带RGB颜色的点云（xyzrgb）

**话题重映射**（在 `wheeltec_camera.launch` 中）：
```xml
<remap from="/camera/color/image_raw" to="/camera/rgb/image_raw"/>
<remap from="/camera/color/camera_info" to="/camera/rgb/camera_info"/>
```

#### 相机服务（Services）

Astra相机提供的ROS服务（参考 `ros_astra_camera/README.md`）：

**设备信息**：
- `/camera/get_device_type` - 获取设备型号
- `/camera/get_serial` - 获取序列号

**IR相机参数**：
- `/camera/get_ir_exposure` - 获取IR曝光值
- `/camera/get_ir_gain` - 获取IR增益值
- `/camera/set_ir_exposure` - 设置IR曝光值
- `/camera/set_ir_gain` - 设置IR增益值
- `/camera/reset_ir_exposure` - 重置IR曝光到默认值
- `/camera/reset_ir_gain` - 重置IR增益到默认值

**RGB相机参数**：
- `/camera/get_uvc_exposure` - 获取RGB曝光值
- `/camera/get_uvc_gain` - 获取RGB增益值
- `/camera/get_uvc_white_balance` - 获取白平衡值
- `/camera/set_uvc_exposure` - 设置RGB曝光（0表示自动模式）
- `/camera/set_uvc_gain` - 设置RGB增益
- `/camera/set_uvc_white_balance` - 设置白平衡（0表示自动模式）

**激光和其他功能**：
- `/camera/set_laser` - 开启/关闭激光（true/false）
- `/camera/set_ldp` - 开启/关闭LDP（true/false）
- `/camera/set_ir_flood` - 开启/关闭IR泛光灯（true/false）
- `/camera/switch_ir_camera` - 切换左右IR相机（仅stereo_s系列）

---

## TF变换配置

### 坐标系结构

Wheeltec机器人的主要坐标系：

- `base_footprint` - 机器人底盘投影在地面的参考点
- `base_link` - 机器人底盘中心
- `laser` - 激光雷达坐标系
- `camera_link` - 相机坐标系
- `gyro_link` - IMU陀螺仪坐标系
- `odom` / `odom_combined` - 里程计坐标系

### TF发布节点

**配置文件**：`turn_on_wheeltec_robot/launch/robot_model_visualization.launch`

该文件根据不同车型发布相应的静态TF变换。

#### Senior_4wd_bs 车型（当前配置）

**重要**：Senior_4wd_bs 车型的 base_footprint 到 base_link 的Z轴高度为 **0.04994m**（第8行注释中确认）。

需要在 `robot_model_visualization.launch` 中确认或添加如下配置：

```xml
<group if="$(eval car_mode == 'senior_4wd_bs')">
    <node pkg="tf" type="static_transform_publisher" name="base_to_laser"
          args="[需要实际测量] base_link laser 100" />
    <node pkg="tf" type="static_transform_publisher" name="base_to_camera"
          args="[需要实际测量] base_link camera_link 100" />
    <node pkg="tf" type="static_transform_publisher" name="base_to_gyro"
          args="0 0 0 0 0 0 base_footprint gyro_link 100" />
</group>
```

**注意**：激光雷达和相机的实际安装位置需要根据机械图纸和实际测量确定。参考机械尺寸章节中的二维机械图。

#### Mini_4wd 车型示例（四驱小车）

从 `robot_model_visualization.launch` 第145-149行：

```xml
<group if="$(eval car_mode == 'mini_4wd')">
    <node pkg="tf" type="static_transform_publisher" name="base_to_laser"
          args="0.03163 0.00009 0.09292 3.14 0 0  base_link laser 100" />
    <node pkg="tf" type="static_transform_publisher" name="base_to_camera"
          args="0.10709 0.00032 0.0767 0 0 0   base_link camera_link 100" />
    <node pkg="tf" type="static_transform_publisher" name="base_to_gyro"
          args="0 0 0 0 0 0 base_footprint gyro_link 100" />
</group>
```

**TF变换参数解释**：

`args="x y z yaw pitch roll parent_frame child_frame period"`

- **激光雷达到base_link**：
  - 平移：x=0.03163m, y=0.00009m, z=0.09292m
  - 旋转：yaw=3.14rad (180度), pitch=0, roll=0

- **相机到base_link**：
  - 平移：x=0.10709m, y=0.00032m, z=0.0767m
  - 旋转：yaw=0, pitch=0, roll=0

- **IMU到base_footprint**：
  - 平移：x=0, y=0, z=0（位于base_footprint中心）
  - 旋转：yaw=0, pitch=0, roll=0

#### Mini_mec 车型示例（麦克纳姆轮）

从 `robot_model_visualization.launch` 第48-54行：

```xml
<group if="$(eval car_mode == 'mini_mec')">
    <node pkg="tf" type="static_transform_publisher" name="base_to_laser"
          args="0.03163 0.00009 0.09502 3.14 0 0  base_footprint laser 100" />
    <node pkg="tf" type="static_transform_publisher" name="base_to_camera"
          args="0.10709 0.00032 0.0762 0 0 0   base_footprint camera_link 100" />
    <node pkg="tf" type="static_transform_publisher" name="base_to_gyro"
          args="0 0 0 0 0 0 base_footprint gyro_link 100" />
</group>
```

### base_footprint 到 base_link 的变换

**重要**：从 `robot_model_visualization.launch` 第7行：

```xml
<node pkg="tf" type="static_transform_publisher" name="base_to_link"
      args="0 0 0.07258 0 0 0 base_footprint base_link 100" />
```

**不同车型的Z轴高度**（第8行注释）：

| 车型 | Z轴高度(m) | 车型 | Z轴高度(m) |
|------|-----------|------|-----------|
| mini_4wd | 0.0682 | mini_mec | 0.07258 |
| mini_akm | 0.0216 | mini_omni | 0.06542 |
| mini_tank | 0.03715 | mini_diff | 0.01563 |
| senior_4wd_bs | 0.04994 | senior_mec_bs | 0.02391 |
| senior_diff | 0.0374 | senior_omni | 0.09016 |
| top_4wd_bs | 0.08786 | top_mec_bs | 0.05274 |

**注意**：如果你的车型与上述不同，需要修改第7行的Z轴参数。

### 支持的车型完整列表

从 `turn_on_wheeltec_robot/launch/turn_on_wheeltec_robot.launch` 第3-12行：

**阿克曼系列**：mini_akm, senior_akm, top_akm_bs, top_akm_dl, V550_akm

**麦轮系列**：mini_mec, senior_mec_bs, senior_mec_dl, top_mec_bs, top_mec_dl, senior_mec_EightDrive, top_mec_EightDrive, flagship_mec_bs, flagship_mec_dl, r3s_mec

**全向轮系列**：mini_omni, senior_omni, top_omni

**四驱系列**：mini_4wd, senior_4wd_bs, senior_4wd_dl, top_4wd_bs, top_4wd_dl, flagship_4wd_bs, flagship_4wd_dl, r3S_4wd

**差速系列**：mini_tank, mini_diff, senior_diff, four_wheel_diff_bs, four_wheel_diff_dl, flagship_four_wheel_diff_dl, flagship_four_wheel_diff_bs, brushless_senior_diff, S100_diff

**带机械臂系列**：mini_tank_moveit_four, mini_4wd_moveit_four, mini_mec_moveit_four, mini_mec_moveit_six, mini_4wd_moveit_six

---

## Launch文件说明

### 主启动文件

#### 1. turn_on_wheeltec_robot.launch

**路径**：`turn_on_wheeltec_robot/launch/turn_on_wheeltec_robot.launch`

**功能**：机器人底层控制的主启动文件

**重要参数**：
```xml
<arg name="car_mode" default="mini_mec" />  <!-- 车型选择，当前配置使用 senior_4wd_bs -->
<arg name="navigation" default="false" />   <!-- 是否开启导航功能 -->
<arg name="pure3d_nav" default="false" />   <!-- 是否开启纯视觉3D导航 -->
<arg name="repeat" default="false" />       <!-- 是否重复开启底层节点 -->
<arg name="if_voice" default="false" />     <!-- 是否使用语音 -->
<arg name="is_cartographer" default="false" />  <!-- 是否使用cartographer建图 -->
<arg name="odom_frame_id" default="odom_combined" />  <!-- 里程计坐标系 -->
```

**当前配置启动命令**：
```bash
roslaunch turn_on_wheeltec_robot turn_on_wheeltec_robot.launch car_mode:=senior_4wd_bs
```

**包含的功能模块**：
1. **底层串口通信** - `include/base_serial.launch`（开启底层单片机控制）
2. **TF变换和机器人模型** - `robot_model_visualization.launch`
3. **扩展卡尔曼滤波** - `include/robot_pose_ekf.launch`（融合IMU和里程计）
4. **导航算法**（可选）：
   - TEB local planner（推荐）
   - DWA local planner（备选）

#### 2. wheeltec_camera.launch

**路径**：`turn_on_wheeltec_robot/launch/wheeltec_camera.launch`

**功能**：启动Astra系列深度相机

**当前配置启动命令**：
```bash
# 方式1：通过wheeltec封装的launch文件
roslaunch turn_on_wheeltec_robot wheeltec_camera.launch camera_mode:=Astra_S

# 方式2：直接启动Astra Stereo S驱动（推荐，支持双IR）
roslaunch astra_camera stereo_s.launch
```

详见 [相机配置](#相机配置) 部分。

#### 3. 3d_mapping.launch

**路径**：`turn_on_wheeltec_robot/launch/3d_mapping.launch`

**功能**：同时进行2D建图和3D建图（使用RTAB-Map）

**启动流程**：
1. 开启2D建图（调用 `mapping.launch`）
2. 开启摄像头（调用 `wheeltec_camera.launch`）
3. 开启3D建图（调用 `include/rtabmap_mapping.launch`）

**重要参数**：
```xml
<arg name="odom_frame_id" value="odom"/>  <!-- 使用2D建图定位补偿 -->
```

#### 4. mapping.launch

**路径**：`turn_on_wheeltec_robot/launch/mapping.launch`

**功能**：2D SLAM建图

**支持的SLAM算法**：
- Gmapping（默认）
- Cartographer
- Hector
- Karto

#### 5. navigation.launch

**路径**：`turn_on_wheeltec_robot/launch/navigation.launch`

**功能**：机器人自主导航

**包含的功能**：
- AMCL定位
- move_base导航
- TEB/DWA局部路径规划

#### 6. nav_grasp_return.launch

**路径**：`turn_on_wheeltec_robot/launch/nav_grasp_return.launch`

**功能**：导航-抓取-返回完整工作流

详见 `NAV_GRASP_RETURN_README.md`

---

## URDF机器人描述

### URDF文件位置

**路径**：`turn_on_wheeltec_robot/urdf/`

### Mini_4wd 机器人URDF示例

**文件**：`turn_on_wheeltec_robot/urdf/mini_4wd_robot.urdf`

#### 主要Link（连杆）

1. **base_link** - 机器人底盘主体
   - 质量：0.62 kg
   - 网格模型：`meshes/mini_4wd_robot_meshes/base_link.STL`

2. **车轮** (4个)：
   - `lf_wheel_link` - 左前轮
   - `lb_wheel_link` - 左后轮
   - `rf_wheel_link` - 右前轮
   - `rb_wheel_link` - 右后轮
   - 质量：约 0.042 kg/轮
   - 类型：continuous joint（连续旋转）

3. **laser** - 激光雷达
   - 质量：0.048 kg
   - 位置（相对base_link）：
     - xyz: (0.03163, 0.00009, 0.09292)
     - rpy: (0, 0, 3.14159) - 旋转180度

4. **camera_link** - 相机
   - 质量：0.056 kg
   - 位置（相对base_link）：
     - xyz: (0.10709, 0.00032, 0.0767)
     - rpy: (0, 0, 0)

5. **controller_link** - 控制器
   - 质量：0.039 kg

#### 重要坐标（相对base_link）

从URDF文件提取的关键坐标：

| 组件 | X (m) | Y (m) | Z (m) | 说明 |
|------|-------|-------|-------|------|
| 激光雷达 | 0.03163 | 0.00009 | 0.09292 | 旋转180度 |
| 相机 | 0.10709 | 0.00032 | 0.0767 | 朝前 |
| 左前轮 | 0.07889 | 0.09090 | -0.0363 | |
| 左后轮 | -0.09301 | 0.09090 | -0.0363 | |
| 右后轮 | -0.09301 | -0.09072 | -0.0363 | |
| 右前轮 | 0.07889 | -0.09072 | -0.0363 | |

**轮距和轴距**：
- 轮距（左右轮间距）：约 0.18m
- 轴距（前后轮间距）：约 0.17m

---

## 导航和建图

### 导航参数配置

**路径**：`turn_on_wheeltec_robot/params_costmap_car/`

每种车型都有对应的参数文件夹，例如：
- `param_mini_4wd/` - mini_4wd车型参数
- `param_mini_mec/` - mini_mec车型参数
- `param_senior_4wd_bs/` - senior_4wd_bs车型参数（**当前配置**）

**包含文件**：
- `costmap_car_params.yaml` - 代价地图参数
- `teb_local_planner_params.yaml` - TEB局部规划器参数

**注意**：senior_4wd_bs 的导航参数需要根据以下特性调整：
- 轮距：312.7mm
- 轮径：152mm
- 最大速度：2.7m/s
- 车身尺寸：486×523mm (footprint)

### SLAM算法配置

从 `turn_on_wheeltec_robot/launch/mapping.launch` 支持的算法：

1. **Gmapping** - 基于粒子滤波的2D SLAM
2. **Cartographer** - Google的2D/3D SLAM
3. **Hector** - 不需要里程计的SLAM
4. **Karto** - 基于图优化的SLAM

---

## Wheeltec官方文档

### 导航-抓取-返回系统

**文档**：`turn_on_wheeltec_robot/NAV_GRASP_RETURN_README.md`

**系统组件**：
1. 导航-抓取-返回节点 - `turn_on_wheeltec_robot/scripts/nav_grasp_return.py`
2. Launch文件 - `turn_on_wheeltec_robot/launch/nav_grasp_return.launch`

**配置参数**：
```xml
<param name="target_x" type="double" value="1.0" />    <!-- 目标X坐标 -->
<param name="target_y" type="double" value="1.0" />    <!-- 目标Y坐标 -->
<param name="target_theta" type="double" value="0.0" /> <!-- 目标角度(度) -->
```

**工作流程**：
1. 初始化并连接到move_base
2. 记录起始位置
3. 导航到目标位置
4. 执行抓取动作
5. 返回起始位置

### Astra相机驱动文档

**文档**：`ros_astra_camera/README.md`

**安装依赖**：
```bash
sudo apt install ros-$ROS_DISTRO-rgbd-launch ros-$ROS_DISTRO-libuvc \
                 ros-$ROS_DISTRO-libuvc-camera ros-$ROS_DISTRO-libuvc-ros
```

**创建udev规则**：
```bash
roscd astra_camera
./scripts/create_udev_rules
```

**编译**：
```bash
cd ~/catkin_ws
catkin_make --pkg astra_camera
```

**启动示例**：
```bash
# 启动Astra相机
roslaunch astra_camera astra.launch

# 启动Astra Stereo S（带UVC）
roslaunch astra_camera stereo_s.launch
```

---

## 常用命令参考

### 编译和启动

```bash
# 编译工作空间
cd ~/catkin_ws
catkin_make
source devel/setup.bash

# 启动机器人底层（senior_4wd_bs车型）
roslaunch turn_on_wheeltec_robot turn_on_wheeltec_robot.launch car_mode:=senior_4wd_bs

# 启动相机（Astra Stereo S）
roslaunch turn_on_wheeltec_robot wheeltec_camera.launch camera_mode:=Astra_S
# 或直接启动 Stereo S 驱动
roslaunch astra_camera stereo_s.launch

# 启动2D建图
roslaunch turn_on_wheeltec_robot mapping.launch

# 启动3D建图
roslaunch turn_on_wheeltec_robot 3d_mapping.launch

# 启动导航
roslaunch turn_on_wheeltec_robot navigation.launch
```

### 查看TF树

```bash
# 查看TF树结构
rosrun tf view_frames

# 实时监控TF
rosrun rqt_tf_tree rqt_tf_tree

# 查看特定TF变换
rosrun tf tf_echo base_link camera_link
```

### 查看相机信息

```bash
# 查看相机话题
rostopic list | grep camera

# 查看RGB图像
rosrun image_view image_view image:=/camera/rgb/image_raw

# 查看深度图像
rosrun image_view image_view image:=/camera/depth/image_raw

# 查看点云
rosrun rviz rviz
# 在rviz中添加PointCloud2，选择topic: /camera/depth/points
```

### 相机服务调用示例

```bash
# 获取IR曝光值
rosservice call /camera/get_ir_exposure

# 设置IR曝光值
rosservice call /camera/set_ir_exposure "exposure: 50"

# 开启激光
rosservice call /camera/set_laser "enable: true"

# 关闭激光
rosservice call /camera/set_laser "enable: false"
```

---

## 相机标定建议

### 为什么需要标定

相机标定可以提供准确的内参（焦距、光心、畸变系数），从而：
1. 提高深度测量的准确性
2. 改善点云质量
3. 提升3D建图和导航的精度

### 标定工具

**ROS标定工具**：
```bash
# 安装标定工具包
sudo apt install ros-$ROS_DISTRO-camera-calibration

# 标定RGB相机（棋盘格尺寸8x6，方格大小0.025m）
rosrun camera_calibration cameracalibrator.py \
  --size 8x6 --square 0.025 \
  image:=/camera/rgb/image_raw \
  camera:=/camera/rgb

# 标定深度相机
rosrun camera_calibration cameracalibrator.py \
  --size 8x6 --square 0.025 \
  image:=/camera/depth/image_raw \
  camera:=/camera/depth
```

### 标定流程

1. **准备棋盘格标定板**
   - 打印或购买标定板
   - 测量准确的方格尺寸

2. **启动相机**
   ```bash
   roslaunch turn_on_wheeltec_robot wheeltec_camera.launch
   ```

3. **运行标定程序**
   - 执行上面的标定命令
   - 在不同位置、角度移动标定板
   - 收集足够的标定样本（建议40+张）

4. **保存标定结果**
   - 点击"CALIBRATE"进行计算
   - 点击"SAVE"保存标定文件
   - 标定文件会保存到 `~/.ros/camera_info/`

5. **应用标定结果**
   - 修改相机launch文件，指定标定文件路径：
   ```xml
   <arg name="rgb_camera_info_url"
        default="file://${HOME}/.ros/camera_info/rgb_xxxxx.yaml" />
   <arg name="depth_camera_info_url"
        default="file://${HOME}/.ros/camera_info/depth_xxxxx.yaml" />
   ```

---

## 故障排查

### 相机相关问题

**问题1：相机无法启动**
```bash
# 检查相机设备
ls /dev | grep -E 'video|Astra'

# 检查udev规则
ls -la /etc/udev/rules.d/ | grep -i astra

# 重新创建udev规则
roscd astra_camera
sudo ./scripts/create_udev_rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

**问题2：USB缓冲区错误**
```bash
# 增加USBFS缓冲区大小
echo 128 | sudo tee /sys/module/usbcore/parameters/usbfs_memory_mb

# 永久生效：添加到 /etc/rc.local
echo 'echo 128 > /sys/module/usbcore/parameters/usbfs_memory_mb' | \
  sudo tee -a /etc/rc.local
```

**问题3：点云数据质量差**
- 进行相机标定
- 调整相机曝光和增益参数
- 检查环境光照条件
- 清洁相机镜头

### TF变换问题

**问题：TF变换不存在或不准确**

```bash
# 检查TF树
rosrun tf view_frames
# 会生成 frames.pdf，查看坐标系关系

# 检查特定变换是否存在
rosrun tf tf_echo base_link camera_link

# 如果变换不存在，检查：
# 1. robot_model_visualization.launch 是否启动
# 2. car_mode 参数是否正确
# 3. static_transform_publisher 节点是否运行
rosnode list | grep static_transform
```

### 导航和建图问题

**问题：AMCL定位不准确**
- 检查激光雷达数据质量
- 调整AMCL参数（粒子数量、初始位置等）
- 确保地图文件正确加载

**问题：导航无法到达目标点**
- 检查代价地图是否正确
- 调整TEB/DWA规划器参数
- 确保目标点在自由空间内

---

## 参考资源

### 官方文档链接

- **ROS Wiki**:
  - [navigation](http://wiki.ros.org/navigation)
  - [move_base](http://wiki.ros.org/move_base)
  - [tf](http://wiki.ros.org/tf)
  - [camera_calibration](http://wiki.ros.org/camera_calibration)

- **Orbbec Astra**:
  - [Astra相机GitHub](https://github.com/orbbec/ros_astra_camera)

### 本地文档位置

- `turn_on_wheeltec_robot/NAV_GRASP_RETURN_README.md` - 导航抓取系统说明
- `ros_astra_camera/README.md` - Astra相机驱动说明
- `navigation-melodic/README.md` - ROS导航包说明
- `darknet_ros/README.md` - YOLO目标检测说明

---

## 下一步行动建议

### 立即可以做的事情

1. **验证当前配置 (senior_4wd_bs + Astra Stereo S)**
   ```bash
   # 启动机器人底层
   roslaunch turn_on_wheeltec_robot turn_on_wheeltec_robot.launch car_mode:=senior_4wd_bs

   # 启动Astra Stereo S相机
   roslaunch astra_camera stereo_s.launch

   # 查看RGB图像
   rosrun image_view image_view image:=/camera/rgb/image_raw

   # 查看深度图像
   rosrun image_view image_view image:=/camera/depth/image_raw
   ```

2. **检查TF配置**
   ```bash
   # 查看TF树，确认camera_link位置正确
   rosrun tf view_frames
   rosrun tf tf_echo base_link camera_link
   rosrun tf tf_echo base_link laser
   ```

3. **测试相机功能**
   ```bash
   # 测试双IR相机切换（Stereo S特有）
   rosservice call /camera/switch_ir_camera

   # 查看点云数据
   rosrun rviz rviz
   # 在rviz中添加PointCloud2，选择topic: /camera/depth_registered/points
   ```

4. **测试激光雷达**
   ```bash
   # 查看激光雷达话题
   rostopic echo /scan

   # 在rviz中可视化激光扫描
   rosrun rviz rviz
   # 添加LaserScan显示，选择topic: /scan
   ```

### 相机标定流程

如果需要更精确的相机参数：

1. 准备8x6或更大的棋盘格标定板
2. 启动相机
3. 运行标定程序，收集40+张不同角度的图像
4. 保存标定结果
5. 在launch文件中引用标定文件

### 集成YOLO检测

如果需要目标检测功能：

1. 查看 `darknet_ros` 包配置
2. 下载YOLO权重文件
3. 配置检测类别
4. 测试检测效果

---

## 快速配置摘要（Senior_4wd_bs + Astra Stereo S）

### 系统配置
- **车型代码**：`car_mode:=senior_4wd_bs`
- **相机型号**：Astra Stereo S
- **激光雷达**：M10P/M10P-PHY (360° TOF)

### 关键参数
- **base_footprint → base_link Z高度**：0.04994m
- **深度相机FOV**：H 58.4° × V 45.5°
- **深度范围**：0.4-4.0m
- **深度精度**：±1-3mm @ 1m
- **激光雷达测距精度**：±3cm
- **激光雷达范围**：0.05-30m (白色物体)

### 快速启动命令
```bash
# 1. 启动机器人底层
roslaunch turn_on_wheeltec_robot turn_on_wheeltec_robot.launch car_mode:=senior_4wd_bs

# 2. 启动相机
roslaunch astra_camera stereo_s.launch

# 3. 启动SLAM建图
roslaunch turn_on_wheeltec_robot mapping.launch

# 4. 可视化
rosrun rviz rviz
```

### 数据文件参考
- 产品规格：`data/产品信息.png`
- 机械图纸：`data/小车二维机械图.png`
- 激光雷达：`data/激光雷达.png`
- 相机规格：`data/AstraS规格书.pdf`
- 售后手册：`data/奥比中光相机售后问题汇总手册_2025.07.24.docx`

---

**文档最后更新**：2025-12-31

**注意事项**：
- 所有TF变换坐标需要根据实际测量调整（特别是激光雷达和相机的安装位置）
- Senior_4wd_bs 车型的 base_footprint 到 base_link 的Z轴高度已确认为 0.04994m
- 相机标定建议定期进行以保持最佳精度
- Astra Stereo S 支持双IR相机切换功能，使用 `/camera/switch_ir_camera` 服务
