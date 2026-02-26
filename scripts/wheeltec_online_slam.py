"""
Wheeltec + SplaTAM Online 3D Gaussian SLAM

Real-time RGB-D SLAM using ROS2 subscribers from Wheeltec robot + Orbbec Astra S.
Adapted from scripts/iphone_demo.py — replaces CycloneDDS with ROS2 rclpy.

Usage:
    # On Jetson (with ROS2 + camera running):
    python scripts/wheeltec_online_slam.py configs/wheeltec/online_slam.py

    # With custom topics:
    python scripts/wheeltec_online_slam.py configs/wheeltec/online_slam.py \
        --rgb_topic /camera/rgb/image_raw \
        --depth_topic /camera/depth/image
"""
#!/usr/bin/env python3

import argparse
import os
import shutil
import sys
import time
import threading
import signal
from pathlib import Path
from importlib.machinery import SourceFileLoader
from collections import deque

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _BASE_DIR)

import cv2
import numpy as np
import torch
import torch.nn.functional as F
from tqdm import tqdm

from utils.common_utils import seed_everything, save_params_ckpt, save_params
from utils.eval_helpers import report_progress
from utils.keyframe_selection import keyframe_selection_overlap
from utils.recon_helpers import setup_camera
from utils.slam_external import build_rotation, prune_gaussians, densify
from utils.slam_helpers import matrix_to_quaternion
from scripts.splatam import (
    get_loss, initialize_optimizer, initialize_params,
    initialize_camera_pose, get_pointcloud, add_new_gaussians,
)
from diff_gaussian_rasterization import GaussianRasterizer as Renderer

# ============================================================
# ROS2 Frame Receiver (runs in background thread)
# ============================================================
class ROS2FrameReceiver:
    """
    Subscribes to ROS2 RGB + Depth topics via rclpy.
    Stores the latest synchronized frame pair in a thread-safe buffer.
    """
    def __init__(self, config, max_queue=2):
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy
        from sensor_msgs.msg import Image, CameraInfo
        from nav_msgs.msg import Odometry
        from message_filters import ApproximateTimeSynchronizer, Subscriber

        self.config = config
        self.ros2_cfg = config.get('ros2', {})
        self.cam_cfg = config.get('camera', {})

        # Thread-safe frame buffer
        self._lock = threading.Lock()
        self._frame_queue = deque(maxlen=max_queue)
        self._latest_odom = None
        self._intrinsics_received = False
        self._fx = self.cam_cfg.get('fx', 570.3)
        self._fy = self.cam_cfg.get('fy', 570.3)
        self._cx = self.cam_cfg.get('cx', 319.5)
        self._cy = self.cam_cfg.get('cy', 239.5)
        self._stop_event = threading.Event()
        self._frame_count = 0
        self._imu_buffer = deque(maxlen=500)  # ~5s at 100 Hz

        # Initialize ROS2
        rclpy.init()
        self.node = rclpy.create_node('splatam_online_slam')

        # QoS profiles — try both RELIABLE and BEST_EFFORT to match publisher
        queue_size = self.ros2_cfg.get('queue_size', 10)
        qos_reliable = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=queue_size,
        )
        qos_best_effort = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=queue_size,
        )

        # Use RELIABLE first (Astra S ROS2 driver default), fallback configurable
        sub_qos = qos_reliable

        # Synchronized RGB + Depth subscribers
        self._rgb_sub = Subscriber(
            self.node,
            Image,
            self.ros2_cfg.get('rgb_topic', '/camera/color/image_raw'),
            qos_profile=sub_qos,
        )
        self._depth_sub = Subscriber(
            self.node,
            Image,
            self.ros2_cfg.get('depth_topic', '/camera/depth/image_raw'),
            qos_profile=sub_qos,
        )
        self._sync = ApproximateTimeSynchronizer(
            [self._rgb_sub, self._depth_sub],
            queue_size=queue_size,
            slop=0.1,  # 100ms tolerance for RGB-Depth sync
        )
        self._sync.registerCallback(self._synced_callback)

        # Camera info subscriber (one-shot for intrinsics)
        self._caminfo_sub = self.node.create_subscription(
            CameraInfo,
            self.ros2_cfg.get('camera_info_topic', '/camera/color/camera_info'),
            self._caminfo_callback,
            qos_reliable,
        )

        # Optional: odometry subscriber for pose initialization
        if self.ros2_cfg.get('use_odom_init', False):
            self._odom_sub = self.node.create_subscription(
                Odometry,
                self.ros2_cfg.get('odom_topic', '/odom'),
                self._odom_callback,
                qos_best_effort,
            )

        # Debug: standalone subscribers to verify topic connectivity
        self._debug_rgb_count = 0
        self._debug_depth_count = 0
        self._debug_rgb_sub = self.node.create_subscription(
            Image,
            self.ros2_cfg.get('rgb_topic', '/camera/color/image_raw'),
            self._debug_rgb_callback,
            sub_qos,
        )
        self._debug_depth_sub = self.node.create_subscription(
            Image,
            self.ros2_cfg.get('depth_topic', '/camera/depth/image_raw'),
            self._debug_depth_callback,
            sub_qos,
        )

        # Spin ROS2 in background thread
        self._spin_thread = threading.Thread(target=self._spin_loop, daemon=True)
        self._spin_thread.start()
        self.node.get_logger().info('SplaTAM ROS2 node started, waiting for frames...')

        # Debug: print connectivity status after 3 seconds
        self._debug_timer = self.node.create_timer(3.0, self._debug_status)

        # Optional IMU subscriber for gyroscope-aided rotation initialization
        if self.ros2_cfg.get('use_imu_for_propagation', False):
            from sensor_msgs.msg import Imu as ImuMsg
            _imu_topic = self.ros2_cfg.get('imu_topic', '/camera/gyro_accel/sample')
            self._imu_sub = self.node.create_subscription(
                ImuMsg, _imu_topic, self._imu_callback, qos_best_effort)
            self.node.get_logger().info(f'IMU enabled: {_imu_topic}')

    def _debug_rgb_callback(self, msg):
        self._debug_rgb_count += 1

    def _debug_depth_callback(self, msg):
        self._debug_depth_count += 1

    def _debug_status(self):
        synced = self._frame_count
        self.node.get_logger().info(
            f'[DEBUG] RGB msgs: {self._debug_rgb_count}, '
            f'Depth msgs: {self._debug_depth_count}, '
            f'Synced frames: {synced}'
        )
        if self._debug_rgb_count == 0 and self._debug_depth_count == 0:
            self.node.get_logger().warn(
                'No messages received! Check: QoS mismatch? '
                'Run: ros2 topic info /camera/color/image_raw --verbose'
            )
        elif synced == 0 and (self._debug_rgb_count > 0 or self._debug_depth_count > 0):
            self.node.get_logger().warn(
                'Messages received but sync failed! '
                'RGB and Depth timestamps may differ too much. '
                'Try increasing slop in ApproximateTimeSynchronizer.'
            )

    def _spin_loop(self):
        """Background thread: spin ROS2 executor."""
        import rclpy
        while not self._stop_event.is_set():
            rclpy.spin_once(self.node, timeout_sec=0.01)

    def _caminfo_callback(self, msg):
        """Extract intrinsics from CameraInfo (one-shot)."""
        if not self._intrinsics_received:
            K = np.array(msg.k).reshape(3, 3)
            with self._lock:
                self._fx = float(K[0, 0])
                self._fy = float(K[1, 1])
                self._cx = float(K[0, 2])
                self._cy = float(K[1, 2])
                self._intrinsics_received = True
            self.node.get_logger().info(
                f'Camera intrinsics received: fx={self._fx:.1f}, fy={self._fy:.1f}, '
                f'cx={self._cx:.1f}, cy={self._cy:.1f}'
            )

    def _odom_callback(self, msg):
        """Cache latest odometry for pose initialization."""
        pos = msg.pose.pose.position
        ori = msg.pose.pose.orientation
        # Build 4x4 transform from odom
        odom_mat = np.eye(4, dtype=np.float32)
        # Quaternion to rotation matrix (ROS convention: x,y,z,w)
        qx, qy, qz, qw = ori.x, ori.y, ori.z, ori.w
        odom_mat[0, 0] = 1 - 2*(qy**2 + qz**2)
        odom_mat[0, 1] = 2*(qx*qy - qz*qw)
        odom_mat[0, 2] = 2*(qx*qz + qy*qw)
        odom_mat[1, 0] = 2*(qx*qy + qz*qw)
        odom_mat[1, 1] = 1 - 2*(qx**2 + qz**2)
        odom_mat[1, 2] = 2*(qy*qz - qx*qw)
        odom_mat[2, 0] = 2*(qx*qz - qy*qw)
        odom_mat[2, 1] = 2*(qy*qz + qx*qw)
        odom_mat[2, 2] = 1 - 2*(qx**2 + qy**2)
        odom_mat[0, 3] = pos.x
        odom_mat[1, 3] = pos.y
        odom_mat[2, 3] = pos.z
        with self._lock:
            self._latest_odom = odom_mat.copy()

    def _imu_callback(self, msg):
        """Cache gyroscope measurements for inter-frame rotation integration."""
        ts = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        with self._lock:
            self._imu_buffer.append({
                'ts': ts,
                'gyro': np.array([
                    msg.angular_velocity.x,
                    msg.angular_velocity.y,
                    msg.angular_velocity.z,
                ], dtype=np.float64),
            })

    def integrate_rotation(self, t_start, t_end):
        """
        Integrate gyroscope measurements from t_start to t_end using the
        Rodrigues formula. Returns a 3×3 delta rotation matrix expressed in
        the IMU/camera body frame at t_start.
        Returns np.eye(3) if no measurements exist in the window.
        """
        with self._lock:
            window = [m for m in self._imu_buffer if t_start < m['ts'] <= t_end]
        if not window:
            return np.eye(3, dtype=np.float64)
        R = np.eye(3, dtype=np.float64)
        prev_ts = t_start
        for m in window:
            dt = m['ts'] - prev_ts
            omega = m['gyro']
            angle = np.linalg.norm(omega) * dt
            if angle > 1e-9:
                axis = omega / (np.linalg.norm(omega) + 1e-12)
                K = np.array([[0.0, -axis[2], axis[1]],
                              [axis[2], 0.0, -axis[0]],
                              [-axis[1], axis[0], 0.0]])
                dR = np.eye(3) + np.sin(angle) * K + (1.0 - np.cos(angle)) * (K @ K)
                R = R @ dR
            prev_ts = m['ts']
        return R

    def _synced_callback(self, rgb_msg, depth_msg):
        """Receive synchronized RGB + Depth, convert to numpy."""
        # Decode RGB
        if rgb_msg.encoding in ('rgb8',):
            rgb = np.frombuffer(rgb_msg.data, dtype=np.uint8).reshape(
                rgb_msg.height, rgb_msg.width, 3)
        elif rgb_msg.encoding in ('bgr8',):
            bgr = np.frombuffer(rgb_msg.data, dtype=np.uint8).reshape(
                rgb_msg.height, rgb_msg.width, 3)
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        elif rgb_msg.encoding in ('mono8',):
            gray = np.frombuffer(rgb_msg.data, dtype=np.uint8).reshape(
                rgb_msg.height, rgb_msg.width)
            rgb = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
        else:
            # Fallback: try as rgb8
            rgb = np.frombuffer(rgb_msg.data, dtype=np.uint8).reshape(
                rgb_msg.height, rgb_msg.width, 3)

        # Decode Depth
        if depth_msg.encoding == '16UC1':
            depth = np.frombuffer(depth_msg.data, dtype=np.uint16).reshape(
                depth_msg.height, depth_msg.width)
            depth = depth.astype(np.float32) / self.cam_cfg.get('png_depth_scale', 1000.0)
        elif depth_msg.encoding == '32FC1':
            depth = np.frombuffer(depth_msg.data, dtype=np.float32).reshape(
                depth_msg.height, depth_msg.width)
        else:
            # Fallback: assume 16UC1
            depth = np.frombuffer(depth_msg.data, dtype=np.uint16).reshape(
                depth_msg.height, depth_msg.width)
            depth = depth.astype(np.float32) / self.cam_cfg.get('png_depth_scale', 1000.0)

        # Clamp depth to valid range
        depth_near = self.cam_cfg.get('depth_near', 0.4)
        depth_far = self.cam_cfg.get('depth_far', 4.0)
        depth[(depth < depth_near) | (depth > depth_far)] = 0.0

        # Get current odom
        with self._lock:
            odom = self._latest_odom.copy() if self._latest_odom is not None else None

        frame = {
            'rgb': rgb.copy(),
            'depth': depth.copy(),
            'odom': odom,
            'timestamp': rgb_msg.header.stamp.sec + rgb_msg.header.stamp.nanosec * 1e-9,
        }

        with self._lock:
            self._frame_queue.append(frame)
            self._frame_count += 1

    def get_frame(self, timeout=5.0):
        """
        Blocking call: return next frame dict or None on timeout.
        Returns: {'rgb': HxWx3 uint8, 'depth': HxW float32 (meters), 'odom': 4x4|None}
        """
        t0 = time.time()
        while time.time() - t0 < timeout:
            with self._lock:
                if len(self._frame_queue) > 0:
                    return self._frame_queue.popleft()
            time.sleep(0.005)
        return None

    def get_intrinsics(self):
        """Return (fx, fy, cx, cy) — may be from config or from CameraInfo."""
        with self._lock:
            return self._fx, self._fy, self._cx, self._cy

    @property
    def frame_count(self):
        with self._lock:
            return self._frame_count

    def shutdown(self):
        """Clean up ROS2 resources."""
        import rclpy
        self._stop_event.set()
        self._spin_thread.join(timeout=2.0)
        self.node.destroy_node()
        rclpy.shutdown()


# ============================================================
# Online SLAM Main Loop
# ============================================================
def online_slam_loop(receiver: ROS2FrameReceiver, save_path: Path, config: dict, stop_event: threading.Event = None):
    """
    Main SLAM loop: receive frames from ROS2, perform tracking + mapping.
    Adapted from scripts/iphone_demo.py::dataset_capture_loop().
    """
    if stop_event is None:
        stop_event = threading.Event()
    num_frames = config.get('num_frames', 500)
    if num_frames <= 0:
        num_frames = 999999  # Unlimited

    save_path.mkdir(parents=True, exist_ok=True)
    rgb_dir = save_path / "rgb"
    depth_dir = save_path / "depth"
    rgb_dir.mkdir(exist_ok=True)
    depth_dir.mkdir(exist_ok=True)

    # Initialize runtime tracking
    keyframe_list = []
    keyframe_time_indices = []
    est_w2c_all_frames = []
    tracking_iter_time_sum = 0
    tracking_iter_time_count = 0
    mapping_iter_time_sum = 0
    mapping_iter_time_count = 0
    tracking_frame_time_sum = 0
    tracking_frame_time_count = 0
    mapping_frame_time_sum = 0
    mapping_frame_time_count = 0

    params = None
    variables = None
    intrinsics = None
    densify_intrinsics = None
    cam = None
    densify_cam = None
    first_frame_w2c = None
    time_idx = 0

    print(f"\n{'='*60}")
    use_imu = config.get('use_imu_for_propagation', False)
    prev_frame_ts = None

    print(f"  SplaTAM Online SLAM — Wheeltec RGB-D")
    print(f"  Max frames: {num_frames}")
    print(f"  Tracking iters: {config['tracking']['num_iters']}")
    print(f"  Mapping iters: {config['mapping']['num_iters']}")
    print(f"  Output: {save_path}")
    print(f"{'='*60}\n")

    print("Waiting for ROS2 frames...")

    while time_idx < num_frames and not stop_event.is_set():
        # ---- Receive Frame ----
        frame = receiver.get_frame(timeout=2.0)
        if frame is None:
            if stop_event.is_set():
                break
            print(f"[WARN] No frame received for 2s at time_idx={time_idx}, retrying...")
            continue

        rgb_np = frame['rgb']      # HxWx3 uint8
        depth_np = frame['depth']  # HxW float32 (meters)
        odom = frame['odom']       # 4x4 or None
        curr_frame_ts = frame['timestamp']

        # Integrate gyroscope for rotation-aided pose initialization
        imu_dR = None
        if use_imu and prev_frame_ts is not None and time_idx > 0:
            imu_dR = receiver.integrate_rotation(prev_frame_ts, curr_frame_ts)

        print(f"\rFrame {time_idx + 1}/{num_frames} | "
              f"Gaussians: {params['means3D'].shape[0] if params is not None else 0}", end="")

        # Save raw frames to disk
        cv2.imwrite(str(rgb_dir / f"{time_idx:06d}.png"),
                     cv2.cvtColor(rgb_np, cv2.COLOR_RGB2BGR))
        depth_save = (depth_np * 1000.0).astype(np.uint16)  # back to mm
        cv2.imwrite(str(depth_dir / f"{time_idx:06d}.png"), depth_save)

        # ---- Preprocess: Tracking Resolution ----
        color = cv2.resize(rgb_np, dsize=(
            config['data']['desired_image_width'],
            config['data']['desired_image_height']),
            interpolation=cv2.INTER_LINEAR)
        curr_depth = cv2.resize(depth_np, dsize=(
            config['data']['desired_image_width'],
            config['data']['desired_image_height']),
            interpolation=cv2.INTER_NEAREST)
        curr_depth = np.expand_dims(curr_depth, -1)
        color_tensor = torch.from_numpy(color).cuda().float().permute(2, 0, 1) / 255.0
        depth_tensor = torch.from_numpy(curr_depth).cuda().float().permute(2, 0, 1)

        # ---- Preprocess: Densification Resolution ----
        densify_color = cv2.resize(rgb_np, dsize=(
            config['data']['densification_image_width'],
            config['data']['densification_image_height']),
            interpolation=cv2.INTER_LINEAR)
        densify_depth_np = cv2.resize(depth_np, dsize=(
            config['data']['densification_image_width'],
            config['data']['densification_image_height']),
            interpolation=cv2.INTER_NEAREST)
        densify_depth_np = np.expand_dims(densify_depth_np, -1)
        densify_color_tensor = torch.from_numpy(densify_color).cuda().float().permute(2, 0, 1) / 255.0
        densify_depth_tensor = torch.from_numpy(densify_depth_np).cuda().float().permute(2, 0, 1)

        # ---- First Frame: Initialize ----
        if time_idx == 0:
            fx, fy, cx, cy = receiver.get_intrinsics()
            intrinsics = torch.tensor([
                [fx, 0, cx], [0, fy, cy], [0, 0, 1]
            ]).cuda().float()
            intrinsics = intrinsics / config['data']['downscale_factor']
            intrinsics[2, 2] = 1.0

            densify_intrinsics = torch.tensor([
                [fx, 0, cx], [0, fy, cy], [0, 0, 1]
            ]).cuda().float()
            densify_intrinsics = densify_intrinsics / config['data']['densify_downscale_factor']
            densify_intrinsics[2, 2] = 1.0

            first_frame_w2c = torch.eye(4).cuda().float()
            cam = setup_camera(
                color_tensor.shape[2], color_tensor.shape[1],
                intrinsics.cpu().numpy(), first_frame_w2c.cpu().numpy())
            densify_cam = setup_camera(
                densify_color_tensor.shape[2], densify_color_tensor.shape[1],
                densify_intrinsics.cpu().numpy(), first_frame_w2c.cpu().numpy())

            # Initialize Gaussian point cloud from first frame
            mask = (densify_depth_tensor > 0).reshape(-1)
            init_pt_cld, mean3_sq_dist = get_pointcloud(
                densify_color_tensor, densify_depth_tensor, densify_intrinsics,
                first_frame_w2c, mask=mask, compute_mean_sq_dist=True,
                mean_sq_dist_method=config['mean_sq_dist_method'])
            params, variables = initialize_params(
                init_pt_cld, num_frames, mean3_sq_dist,
                config['gaussian_distribution'])
            variables['scene_radius'] = torch.max(densify_depth_tensor) / config['scene_radius_depth_ratio']

            print(f"\n[Init] {params['means3D'].shape[0]} Gaussians from first frame")

        # ---- Build Current Data Dict ----
        # Use identity w2c as estimated poses are stored in cam_unnorm_rots/cam_trans
        est_w2c_all_frames.append(first_frame_w2c)  # placeholder, updated after tracking
        iter_time_idx = time_idx
        curr_data = {
            'cam': cam, 'im': color_tensor, 'depth': depth_tensor,
            'id': iter_time_idx, 'intrinsics': intrinsics,
            'w2c': first_frame_w2c, 'iter_gt_w2c_list': est_w2c_all_frames,
        }
        tracking_curr_data = curr_data

        num_iters_mapping = config['mapping']['num_iters']

        # ---- Initialize Camera Pose ----
        if time_idx > 0:
            params = initialize_camera_pose(params, time_idx, forward_prop=config['tracking']['forward_prop'])
            # Override rotation with IMU gyroscope integration when available.
            # w2c_{t+1} = R_imu^T @ w2c_t  (body-frame delta from gyro)
            if imu_dR is not None:
                with torch.no_grad():
                    prev_rot = F.normalize(params['cam_unnorm_rots'][..., time_idx - 1].detach())
                    R_w2c_prev = build_rotation(prev_rot)
                    imu_dR_t = torch.from_numpy(imu_dR).float().cuda()
                    R_w2c_new = imu_dR_t.T @ R_w2c_prev
                    params['cam_unnorm_rots'][..., time_idx] = matrix_to_quaternion(R_w2c_new)

        # ============================================================
        # TRACKING
        # ============================================================
        tracking_start_time = time.time()
        if time_idx > 0 and not config['tracking']['use_gt_poses']:
            optimizer = initialize_optimizer(params, config['tracking']['lrs'], tracking=True)
            candidate_cam_unnorm_rot = params['cam_unnorm_rots'][..., time_idx].detach().clone()
            candidate_cam_tran = params['cam_trans'][..., time_idx].detach().clone()
            current_min_loss = float(1e20)

            num_iters_tracking = config['tracking']['num_iters']
            do_continue_slam = False
            progress_bar = tqdm(range(num_iters_tracking), desc=f"Tracking {time_idx}", leave=False)

            iter = 0
            while True:
                iter_start_time = time.time()
                loss, variables, losses = get_loss(
                    params, tracking_curr_data, variables, iter_time_idx,
                    config['tracking']['loss_weights'],
                    config['tracking']['use_sil_for_loss'],
                    config['tracking']['sil_thres'],
                    config['tracking']['use_l1'],
                    config['tracking']['ignore_outlier_depth_loss'],
                    tracking=True,
                    visualize_tracking_loss=config['tracking']['visualize_tracking_loss'],
                    tracking_iteration=iter)
                loss.backward()
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)

                with torch.no_grad():
                    if loss < current_min_loss:
                        current_min_loss = loss
                        candidate_cam_unnorm_rot = params['cam_unnorm_rots'][..., time_idx].detach().clone()
                        candidate_cam_tran = params['cam_trans'][..., time_idx].detach().clone()
                    if config['report_iter_progress']:
                        report_progress(params, tracking_curr_data, iter+1, progress_bar,
                                        iter_time_idx, sil_thres=config['tracking']['sil_thres'], tracking=True)
                    else:
                        progress_bar.update(1)

                tracking_iter_time_sum += time.time() - iter_start_time
                tracking_iter_time_count += 1
                iter += 1
                if iter == num_iters_tracking:
                    if (losses['depth'] < config['tracking']['depth_loss_thres']
                            and config['tracking']['use_depth_loss_thres']):
                        break
                    elif config['tracking']['use_depth_loss_thres'] and not do_continue_slam:
                        do_continue_slam = True
                        progress_bar = tqdm(range(num_iters_tracking), desc=f"Tracking {time_idx} (ext)", leave=False)
                        num_iters_tracking = 2 * num_iters_tracking
                    else:
                        break

            progress_bar.close()
            with torch.no_grad():
                params['cam_unnorm_rots'][..., time_idx] = candidate_cam_unnorm_rot
                params['cam_trans'][..., time_idx] = candidate_cam_tran

        tracking_end_time = time.time()
        tracking_frame_time_sum += tracking_end_time - tracking_start_time
        tracking_frame_time_count += 1

        # Update estimated w2c for current frame
        with torch.no_grad():
            if time_idx == 0:
                est_w2c_all_frames[-1] = first_frame_w2c
            else:
                curr_cam_rot = F.normalize(params['cam_unnorm_rots'][..., time_idx].detach())
                curr_cam_tran = params['cam_trans'][..., time_idx].detach()
                curr_w2c = torch.eye(4).cuda().float()
                curr_w2c[:3, :3] = build_rotation(curr_cam_rot)
                curr_w2c[:3, 3] = curr_cam_tran
                est_w2c_all_frames[-1] = curr_w2c

        # Report tracking progress periodically
        if time_idx == 0 or (time_idx + 1) % config['report_global_progress_every'] == 0:
            try:
                progress_bar = tqdm(range(1), desc=f"Tracking Result {time_idx}", leave=False)
                with torch.no_grad():
                    report_progress(params, tracking_curr_data, 1, progress_bar,
                                    iter_time_idx, sil_thres=config['tracking']['sil_thres'], tracking=True)
                progress_bar.close()
            except Exception:
                ckpt_output_dir = save_path / "checkpoints"
                os.makedirs(ckpt_output_dir, exist_ok=True)
                save_params_ckpt(params, str(ckpt_output_dir), time_idx)
                print('\n[WARN] Failed to evaluate trajectory.')

        # ============================================================
        # MAPPING (Densification + Keyframe Optimization)
        # ============================================================
        if time_idx == 0 or (time_idx + 1) % config['map_every'] == 0:
            # Add new Gaussians from current view
            if config['mapping']['add_new_gaussians'] and time_idx > 0:
                densify_curr_data = {
                    'cam': densify_cam, 'im': densify_color_tensor,
                    'depth': densify_depth_tensor, 'id': time_idx,
                    'intrinsics': densify_intrinsics, 'w2c': first_frame_w2c,
                    'iter_gt_w2c_list': est_w2c_all_frames,
                }
                params, variables = add_new_gaussians(
                    params, variables, densify_curr_data,
                    config['mapping']['sil_thres'], time_idx,
                    config['mean_sq_dist_method'],
                    config['gaussian_distribution'])

            # Select keyframes for mapping
            with torch.no_grad():
                curr_cam_rot = F.normalize(params['cam_unnorm_rots'][..., time_idx].detach())
                curr_cam_tran = params['cam_trans'][..., time_idx].detach()
                curr_w2c = torch.eye(4).cuda().float()
                curr_w2c[:3, :3] = build_rotation(curr_cam_rot)
                curr_w2c[:3, 3] = curr_cam_tran
                num_keyframes = config['mapping_window_size'] - 2
                selected_keyframes = keyframe_selection_overlap(
                    depth_tensor, curr_w2c, intrinsics, keyframe_list[:-1], num_keyframes)
                selected_time_idx = [keyframe_list[frame_idx]['id'] for frame_idx in selected_keyframes]
                if len(keyframe_list) > 0:
                    selected_time_idx.append(keyframe_list[-1]['id'])
                    selected_keyframes.append(len(keyframe_list) - 1)
                selected_time_idx.append(time_idx)
                selected_keyframes.append(-1)

            # Mapping optimization
            optimizer = initialize_optimizer(params, config['mapping']['lrs'], tracking=False)
            mapping_start_time = time.time()
            if num_iters_mapping > 0:
                progress_bar = tqdm(range(num_iters_mapping), desc=f"Mapping {time_idx}", leave=False)
            for iter in range(num_iters_mapping):
                iter_start_time = time.time()
                rand_idx = np.random.randint(0, len(selected_keyframes))
                selected_rand_keyframe_idx = selected_keyframes[rand_idx]
                if selected_rand_keyframe_idx == -1:
                    iter_time_idx = time_idx
                    iter_color = color_tensor
                    iter_depth = depth_tensor
                else:
                    iter_time_idx = keyframe_list[selected_rand_keyframe_idx]['id']
                    iter_color = keyframe_list[selected_rand_keyframe_idx]['color']
                    iter_depth = keyframe_list[selected_rand_keyframe_idx]['depth']
                iter_gt_w2c = est_w2c_all_frames[:iter_time_idx + 1]
                iter_data = {
                    'cam': cam, 'im': iter_color, 'depth': iter_depth,
                    'id': iter_time_idx, 'intrinsics': intrinsics,
                    'w2c': first_frame_w2c, 'iter_gt_w2c_list': iter_gt_w2c,
                }
                loss, variables, losses = get_loss(
                    params, iter_data, variables, iter_time_idx,
                    config['mapping']['loss_weights'],
                    config['mapping']['use_sil_for_loss'],
                    config['mapping']['sil_thres'],
                    config['mapping']['use_l1'],
                    config['mapping']['ignore_outlier_depth_loss'],
                    mapping=True)
                loss.backward()
                with torch.no_grad():
                    if config['mapping']['prune_gaussians']:
                        params, variables = prune_gaussians(
                            params, variables, optimizer, iter,
                            config['mapping']['pruning_dict'])
                    if config['mapping']['use_gaussian_splatting_densification']:
                        params, variables = densify(
                            params, variables, optimizer, iter,
                            config['mapping']['densify_dict'])
                    optimizer.step()
                    optimizer.zero_grad(set_to_none=True)
                    if config['report_iter_progress']:
                        report_progress(params, iter_data, iter+1, progress_bar,
                                        iter_time_idx, sil_thres=config['mapping']['sil_thres'],
                                        mapping=True, online_time_idx=time_idx)
                    else:
                        progress_bar.update(1)
                mapping_iter_time_sum += time.time() - iter_start_time
                mapping_iter_time_count += 1

            if num_iters_mapping > 0:
                progress_bar.close()
            mapping_end_time = time.time()
            mapping_frame_time_sum += mapping_end_time - mapping_start_time
            mapping_frame_time_count += 1

        # ---- Add Keyframe ----
        if (time_idx == 0
                or (time_idx + 1) % config['keyframe_every'] == 0
                or time_idx == num_frames - 2):
            with torch.no_grad():
                curr_cam_rot = F.normalize(params['cam_unnorm_rots'][..., time_idx].detach())
                curr_cam_tran = params['cam_trans'][..., time_idx].detach()
                curr_w2c = torch.eye(4).cuda().float()
                curr_w2c[:3, :3] = build_rotation(curr_cam_rot)
                curr_w2c[:3, 3] = curr_cam_tran
                curr_keyframe = {
                    'id': time_idx,
                    'est_w2c': curr_w2c,
                    'color': color_tensor,
                    'depth': depth_tensor,
                }
                keyframe_list.append(curr_keyframe)
                keyframe_time_indices.append(time_idx)

        # ---- Checkpoint ----
        if time_idx % config['checkpoint_interval'] == 0 and config['save_checkpoints']:
            ckpt_output_dir = save_path / "checkpoints"
            os.makedirs(ckpt_output_dir, exist_ok=True)
            save_params_ckpt(params, str(ckpt_output_dir), time_idx)
            np.save(str(ckpt_output_dir / f"keyframe_time_indices{time_idx}.npy"),
                    np.array(keyframe_time_indices))

        prev_frame_ts = curr_frame_ts
        torch.cuda.empty_cache()
        time_idx += 1

    # ============================================================
    # Finish: Save Final Results
    # ============================================================
    print(f"\n\n{'='*60}")
    print("  Online SLAM Complete!")
    print(f"  Processed {time_idx} frames")
    print(f"  Final Gaussians: {params['means3D'].shape[0]}")

    # Print runtime stats
    if tracking_iter_time_count > 0:
        print(f"  Avg Tracking/Iter: {tracking_iter_time_sum/tracking_iter_time_count*1000:.1f} ms")
    if tracking_frame_time_count > 0:
        print(f"  Avg Tracking/Frame: {tracking_frame_time_sum/tracking_frame_time_count:.3f} s")
    if mapping_iter_time_count > 0:
        print(f"  Avg Mapping/Iter: {mapping_iter_time_sum/mapping_iter_time_count*1000:.1f} ms")
    if mapping_frame_time_count > 0:
        print(f"  Avg Mapping/Frame: {mapping_frame_time_sum/mapping_frame_time_count:.3f} s")
    print(f"{'='*60}\n")

    # Save final params
    params['timestep'] = variables['timestep']
    params['intrinsics'] = intrinsics.detach().cpu().numpy()
    params['w2c'] = first_frame_w2c.detach().cpu().numpy()
    params['org_width'] = config['data']['desired_image_width']
    params['org_height'] = config['data']['desired_image_height']
    params['gt_w2c_all_frames'] = np.stack(
        [w.detach().cpu().numpy() for w in est_w2c_all_frames], axis=0)
    params['keyframe_time_indices'] = np.array(keyframe_time_indices)

    output_dir = os.path.join(config['workdir'], config['run_name'])
    save_params(params, output_dir)
    print(f"Saved SplaTAM result to: {output_dir}")

    # Also save poses as individual .npy files for offline reprocessing
    poses_dir = save_path / "poses"
    poses_dir.mkdir(exist_ok=True)
    for i, w2c in enumerate(est_w2c_all_frames):
        c2w = torch.linalg.inv(w2c).detach().cpu().numpy()
        np.save(str(poses_dir / f"{i:06d}.npy"), c2w)
    print(f"Saved {len(est_w2c_all_frames)} estimated poses to: {poses_dir}")


# ============================================================
# Entry Point
# ============================================================
def parse_args():
    parser = argparse.ArgumentParser(description="Wheeltec Online 3D Gaussian SLAM")
    parser.add_argument("config", type=str, help="Path to config file")
    parser.add_argument("--rgb_topic", type=str, default=None, help="Override RGB topic")
    parser.add_argument("--depth_topic", type=str, default=None, help="Override Depth topic")
    parser.add_argument("--num_frames", type=int, default=None, help="Override max frames")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Load config
    experiment = SourceFileLoader(
        os.path.basename(args.config), args.config
    ).load_module()
    config = experiment.config

    # Apply CLI overrides
    if args.rgb_topic:
        config['ros2']['rgb_topic'] = args.rgb_topic
    if args.depth_topic:
        config['ros2']['depth_topic'] = args.depth_topic
    if args.num_frames:
        config['num_frames'] = args.num_frames

    if 'gaussian_distribution' not in config:
        config['gaussian_distribution'] = 'isotropic'

    seed_everything(seed=config['seed'])

    # Setup output directory
    results_dir = os.path.join(config['workdir'], config['run_name'])
    os.makedirs(results_dir, exist_ok=True)
    shutil.copy(args.config, os.path.join(results_dir, "config.py"))

    # Start ROS2 receiver
    receiver = ROS2FrameReceiver(config, max_queue=2)

    # Graceful shutdown on Ctrl+C — set stop flag, let loop finish current frame and save
    stop_event = threading.Event()
    def signal_handler(sig, frame):
        print("\n\n[INFO] Ctrl+C received, finishing current frame and saving...")
        stop_event.set()
    signal.signal(signal.SIGINT, signal_handler)

    try:
        online_slam_loop(
            receiver,
            Path(config['workdir']) / config['run_name'],
            config,
            stop_event,
        )
    finally:
        receiver.shutdown()
        print("ROS2 node shutdown complete.")
