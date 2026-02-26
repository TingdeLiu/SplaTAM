#!/usr/bin/env python3
"""
Convert Wheeltec robot ROS2 bag to SplaTAM dataset format.
Supports Orbbec Astra cameras and wheel odometry.

Requirements:
    pip install rosbags opencv-python tqdm numpy

    rosbags is a pure-Python library that reads both ROS1 (.bag) and
    ROS2 (mcap/sqlite3) bag files without needing a ROS installation.

Usage:
    # ROS2 bag directory (contains metadata.yaml)
    python scripts/wheeltec_rosbag_to_splatam.py rosbag2_dir output_dir

    # ROS1 .bag file (also supported)
    python scripts/wheeltec_rosbag_to_splatam.py data.bag output_dir

    # With wheel odometry
    python scripts/wheeltec_rosbag_to_splatam.py rosbag2_dir output_dir --use_odom
"""

import os
import cv2
import numpy as np
from tqdm import tqdm


def quaternion_to_rotation_matrix(x, y, z, w):
    """Convert quaternion to 4x4 homogeneous rotation matrix."""
    R = np.eye(4)
    R[0, 0] = 1 - 2 * (y * y + z * z)
    R[0, 1] = 2 * (x * y - z * w)
    R[0, 2] = 2 * (x * z + y * w)
    R[1, 0] = 2 * (x * y + z * w)
    R[1, 1] = 1 - 2 * (x * x + z * z)
    R[1, 2] = 2 * (y * z - x * w)
    R[2, 0] = 2 * (x * z - y * w)
    R[2, 1] = 2 * (y * z + x * w)
    R[2, 2] = 1 - 2 * (x * x + y * y)
    return R


def imgmsg_to_cv2(msg):
    """Convert a ROS Image message (deserialized by rosbags) to a numpy array."""
    encoding = msg.encoding
    height = msg.height
    width = msg.width
    data = bytes(msg.data)

    if encoding in ('bgr8', 'rgb8'):
        img = np.frombuffer(data, dtype=np.uint8).reshape(height, width, 3)
        if encoding == 'rgb8':
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img
    elif encoding == '16UC1' or encoding == 'mono16':
        return np.frombuffer(data, dtype=np.uint16).reshape(height, width)
    elif encoding == '32FC1':
        return np.frombuffer(data, dtype=np.float32).reshape(height, width)
    elif encoding == 'mono8' or encoding == '8UC1':
        return np.frombuffer(data, dtype=np.uint8).reshape(height, width)
    else:
        raise ValueError(f"Unsupported encoding: {encoding}")


def extract_rosbag(bag_path, output_dir,
                   rgb_topic='/camera/color/image_raw',
                   depth_topic='/camera/depth/image_raw',
                   camera_info_topic='/camera/color/camera_info',
                   odom_topic='/odom',
                   use_odom=False,
                   depth_scale=1000.0):
    """
    Extract RGB-D data from a ROS1 or ROS2 bag file.

    Args:
        bag_path: Path to ROS bag file (.bag) or ROS2 bag directory
        output_dir: Output directory
        rgb_topic: RGB image topic
        depth_topic: Depth image topic
        camera_info_topic: Camera info topic
        odom_topic: Odometry topic
        use_odom: Whether to save wheel odometry poses
        depth_scale: Depth scale factor (meters -> millimeters)
    """
    try:
        from rosbags.highlevel import AnyReader
        from rosbags.typesys import Stores, get_typestore
    except ImportError:
        print("Error: rosbags not found.")
        print("Install with: pip install rosbags")
        raise

    from pathlib import Path

    rgb_dir = os.path.join(output_dir, 'rgb')
    depth_dir = os.path.join(output_dir, 'depth')
    os.makedirs(rgb_dir, exist_ok=True)
    os.makedirs(depth_dir, exist_ok=True)

    if use_odom:
        poses_dir = os.path.join(output_dir, 'poses')
        os.makedirs(poses_dir, exist_ok=True)

    bag_path = Path(bag_path)

    # Detect bag format and choose typestore
    if bag_path.suffix == '.bag':
        typestore = get_typestore(Stores.ROS1_NOETIC)
        print(f"Detected ROS1 bag: {bag_path}")
    else:
        typestore = get_typestore(Stores.ROS2_HUMBLE)
        print(f"Detected ROS2 bag: {bag_path}")

    # Collect all messages
    rgb_msgs = []
    depth_msgs = []
    odom_msgs = []
    camera_intrinsics = None

    topics_to_read = [rgb_topic, depth_topic, camera_info_topic]
    if use_odom:
        topics_to_read.append(odom_topic)

    print("Reading bag file...")
    with AnyReader([bag_path], default_typestore=typestore) as reader:
        # Filter to only requested topics that exist in the bag
        available_topics = {c.topic for c in reader.connections}
        print(f"Available topics: {available_topics}")

        read_topics = [t for t in topics_to_read if t in available_topics]
        missing = set(topics_to_read) - set(read_topics)
        if missing:
            print(f"Warning: Topics not found in bag: {missing}")

        connections = [c for c in reader.connections if c.topic in read_topics]

        for connection, timestamp, rawdata in tqdm(
            reader.messages(connections=connections),
            desc="Reading messages"
        ):
            msg = reader.deserialize(rawdata, connection.msgtype)

            if connection.topic == camera_info_topic and camera_intrinsics is None:
                K = np.array(msg.k).reshape(3, 3)
                camera_intrinsics = K
                print(f"Camera intrinsics:\n{K}")

            elif connection.topic == rgb_topic:
                rgb_msgs.append((timestamp, msg))

            elif connection.topic == depth_topic:
                depth_msgs.append((timestamp, msg))

            elif connection.topic == odom_topic and use_odom:
                odom_msgs.append((timestamp, msg))

    if camera_intrinsics is None:
        print("Warning: Camera intrinsics not found in bag, using Gemini 336L defaults @ 1280x720")
        camera_intrinsics = np.array([
            [607.4463, 0.0, 639.1863],
            [0.0, 607.3991, 361.7548],
            [0.0, 0.0, 1.0]
        ])

    np.savetxt(os.path.join(output_dir, 'camera_intrinsics.txt'),
               camera_intrinsics, fmt='%.6f')

    print(f"Found {len(rgb_msgs)} RGB, {len(depth_msgs)} depth frames")
    if use_odom:
        print(f"Found {len(odom_msgs)} odometry messages")

    # Time-synchronized extraction
    frame_idx = 0
    # Timestamps in nanoseconds for ROS2
    time_threshold_ns = 50_000_000  # 50ms in nanoseconds

    for rgb_t, rgb_msg in tqdm(rgb_msgs, desc="Processing frames"):
        # Find closest depth frame
        best_depth = None
        min_depth_diff = float('inf')

        for depth_t, depth_msg in depth_msgs:
            time_diff = abs(rgb_t - depth_t)
            if time_diff < min_depth_diff:
                min_depth_diff = time_diff
                best_depth = depth_msg

        if min_depth_diff > time_threshold_ns:
            continue

        # Find closest odometry
        best_odom = None
        if use_odom:
            min_odom_diff = float('inf')
            for odom_t, odom_msg in odom_msgs:
                time_diff = abs(rgb_t - odom_t)
                if time_diff < min_odom_diff:
                    min_odom_diff = time_diff
                    best_odom = odom_msg

        # Convert RGB
        try:
            rgb_image = imgmsg_to_cv2(rgb_msg)
            rgb_path = os.path.join(rgb_dir, f'{frame_idx:04d}.jpg')
            cv2.imwrite(rgb_path, rgb_image)
        except Exception as e:
            print(f"RGB conversion failed (frame {frame_idx}): {e}")
            continue

        # Convert depth
        try:
            depth_image = imgmsg_to_cv2(best_depth)

            if depth_image.dtype == np.float32 or depth_image.dtype == np.float64:
                depth_image = (depth_image * depth_scale).astype(np.uint16)
            elif depth_image.dtype == np.uint16:
                max_depth = depth_image.max()
                if max_depth < 100:
                    depth_image = (depth_image.astype(np.float32) * depth_scale).astype(np.uint16)

            depth_path = os.path.join(depth_dir, f'{frame_idx:04d}.png')
            cv2.imwrite(depth_path, depth_image)
        except Exception as e:
            print(f"Depth conversion failed (frame {frame_idx}): {e}")
            continue

        # Save odometry pose
        if use_odom and best_odom is not None:
            try:
                pos = best_odom.pose.pose.position
                ori = best_odom.pose.pose.orientation
                pose_matrix = quaternion_to_rotation_matrix(ori.x, ori.y, ori.z, ori.w)
                pose_matrix[0, 3] = pos.x
                pose_matrix[1, 3] = pos.y
                pose_matrix[2, 3] = pos.z
                pose_path = os.path.join(poses_dir, f'{frame_idx:04d}.npy')
                np.save(pose_path, pose_matrix)
            except Exception as e:
                print(f"Pose conversion failed (frame {frame_idx}): {e}")

        frame_idx += 1

    print(f"\nDone! Extracted {frame_idx} frames")
    print(f"Output directory: {output_dir}")
    print(f"  RGB:    {rgb_dir}")
    print(f"  Depth:  {depth_dir}")
    if use_odom:
        print(f"  Poses:  {poses_dir}")
    print(f"  Intrinsics: {os.path.join(output_dir, 'camera_intrinsics.txt')}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Convert Wheeltec ROS1/ROS2 bag to SplaTAM dataset format')
    parser.add_argument('bag_path', type=str,
                        help='Path to ROS1 .bag file or ROS2 bag directory')
    parser.add_argument('output_dir', type=str, help='Output directory')
    parser.add_argument('--rgb_topic', type=str,
                        default='/camera/color/image_raw',
                        help='RGB image topic')
    parser.add_argument('--depth_topic', type=str,
                        default='/camera/depth/image_raw',
                        help='Depth image topic')
    parser.add_argument('--camera_info_topic', type=str,
                        default='/camera/color/camera_info',
                        help='Camera info topic')
    parser.add_argument('--odom_topic', type=str,
                        default='/odom',
                        help='Odometry topic')
    parser.add_argument('--use_odom', action='store_true',
                        help='Save wheel odometry poses')
    parser.add_argument('--depth_scale', type=float, default=1000.0,
                        help='Depth scale factor (meters -> millimeters)')

    args = parser.parse_args()

    extract_rosbag(
        args.bag_path,
        args.output_dir,
        args.rgb_topic,
        args.depth_topic,
        args.camera_info_topic,
        args.odom_topic,
        args.use_odom,
        args.depth_scale
    )
