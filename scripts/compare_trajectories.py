#!/usr/bin/env python3
"""
Compare SplaTAM estimated trajectory with wheel odometry trajectory.

Usage:
    python scripts/compare_trajectories.py \
        ./experiments/Wheeltec/wheeltec_scene_01_0/params.npz \
        --odom_dir ./data/wheeltec/wheeltec_scene_01/poses
"""

import numpy as np
import matplotlib.pyplot as plt


def compare_trajectories(params_path, odom_dir=None):
    params = np.load(params_path, allow_pickle=True)

    # Extract SplaTAM trajectory
    cam_trans = params['cam_trans']  # (1, 3, T)
    splatam_traj = cam_trans[0].T  # (T, 3)

    fig = plt.figure(figsize=(15, 5))

    # 3D trajectory
    ax1 = fig.add_subplot(131, projection='3d')
    ax1.plot(splatam_traj[:, 0], splatam_traj[:, 1], splatam_traj[:, 2],
             'b-', linewidth=2, label='SplaTAM')

    if odom_dir is not None:
        import glob
        from natsort import natsorted
        odom_files = natsorted(glob.glob(f"{odom_dir}/*.npy"))
        odom_traj = []
        for f in odom_files:
            pose = np.load(f)
            odom_traj.append(pose[:3, 3])
        odom_traj = np.array(odom_traj)

        ax1.plot(odom_traj[:, 0], odom_traj[:, 1], odom_traj[:, 2],
                 'r--', linewidth=2, label='Wheel Odometry')

    ax1.set_xlabel('X (m)')
    ax1.set_ylabel('Y (m)')
    ax1.set_zlabel('Z (m)')
    ax1.set_title('3D Trajectory')
    ax1.legend()
    ax1.grid(True)

    # Top view (XY)
    ax2 = fig.add_subplot(132)
    ax2.plot(splatam_traj[:, 0], splatam_traj[:, 1], 'b-', linewidth=2, label='SplaTAM')
    if odom_dir is not None:
        ax2.plot(odom_traj[:, 0], odom_traj[:, 1], 'r--', linewidth=2, label='Wheel Odom')
    ax2.set_xlabel('X (m)')
    ax2.set_ylabel('Y (m)')
    ax2.set_title('Top View (XY)')
    ax2.legend()
    ax2.grid(True)
    ax2.axis('equal')

    # Side view (XZ)
    ax3 = fig.add_subplot(133)
    ax3.plot(splatam_traj[:, 0], splatam_traj[:, 2], 'b-', linewidth=2, label='SplaTAM')
    if odom_dir is not None:
        ax3.plot(odom_traj[:, 0], odom_traj[:, 2], 'r--', linewidth=2, label='Wheel Odom')
    ax3.set_xlabel('X (m)')
    ax3.set_ylabel('Z (m)')
    ax3.set_title('Side View (XZ)')
    ax3.legend()
    ax3.grid(True)

    plt.tight_layout()
    plt.savefig('trajectory_comparison.png', dpi=300, bbox_inches='tight')
    print("Saved: trajectory_comparison.png")
    plt.show()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Compare SplaTAM and odometry trajectories')
    parser.add_argument('params_path', help='Path to params.npz')
    parser.add_argument('--odom_dir', help='Wheel odometry poses directory', default=None)
    args = parser.parse_args()

    compare_trajectories(args.params_path, args.odom_dir)
