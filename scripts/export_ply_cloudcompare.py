"""
Export SplaTAM params.npz to a standard PLY with RGB vertex colors.
CloudCompare, MeshLab, Open3D can directly display colors.

Usage:
    python scripts/export_ply_cloudcompare.py configs/wheeltec/online_slam.py
    python scripts/export_ply_cloudcompare.py configs/wheeltec/splatam.py
"""
import os
import argparse
from importlib.machinery import SourceFileLoader

import numpy as np

# Spherical harmonic 0-th order constant
C0 = 0.28209479177387814


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def export_cloudcompare_ply(params_path, output_path, opacity_threshold=0.5):
    """
    Convert SplaTAM params.npz to a standard colored point cloud PLY.

    Steps:
        1. rgb_colors (raw) -> SH coefficient -> actual RGB via: rgb = SH * C0 + 0.5
        2. logit_opacities -> sigmoid -> filter low opacity points
        3. Write standard PLY with (x, y, z, red, green, blue)
    """
    params = dict(np.load(params_path, allow_pickle=True))

    means = params['means3D']           # (N, 3)
    rgb_raw = params['rgb_colors']      # (N, 3) — raw color values
    logit_opac = params['logit_opacities']  # (N, 1)

    # Convert logit opacity to [0, 1]
    opacity = sigmoid(logit_opac).squeeze()

    # Convert raw color to RGB [0, 1]
    # In SplaTAM, rgb_colors stores values that go through sigmoid in the renderer
    # The export_ply.py converts them to SH via (rgb-0.5)/C0
    # So the actual visible color is: sigmoid(rgb_raw) or just rgb_raw clipped to [0,1]
    # depending on the representation.
    # Since the original export does: colors_sh = (rgb_raw - 0.5) / C0
    # and the renderer recovers: rgb = sh * C0 + 0.5 = rgb_raw
    # So rgb_raw IS already the [0,1] color, just need to clip.
    rgb = np.clip(rgb_raw, 0.0, 1.0)

    # Filter by opacity
    mask = opacity > opacity_threshold
    means_filtered = means[mask]
    rgb_filtered = rgb[mask]
    opacity_filtered = opacity[mask]

    n_total = means.shape[0]
    n_kept = means_filtered.shape[0]
    print(f"Total Gaussians: {n_total}")
    print(f"Opacity threshold: {opacity_threshold}")
    print(f"Kept: {n_kept} ({100*n_kept/n_total:.1f}%)")

    # Convert to uint8
    rgb_uint8 = (rgb_filtered * 255).astype(np.uint8)

    # Write PLY with standard vertex colors
    with open(output_path, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {n_kept}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        f.write("property uchar red\n")
        f.write("property uchar green\n")
        f.write("property uchar blue\n")
        f.write("end_header\n")
        for i in range(n_kept):
            x, y, z = means_filtered[i]
            r, g, b = rgb_uint8[i]
            f.write(f"{x} {y} {z} {r} {g} {b}\n")

    print(f"Saved to: {output_path}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export SplaTAM result to CloudCompare-compatible PLY")
    parser.add_argument("config", type=str, help="Path to config file")
    parser.add_argument("--opacity_threshold", type=float, default=0.5,
                        help="Filter out Gaussians with opacity below this (default: 0.5)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output PLY path (default: splat_rgb.ply in results dir)")
    parser.add_argument("--scene_name", type=str, default=None,
                        help="Override scene name to export from a specific run (e.g. office_scan_02)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    experiment = SourceFileLoader(
        os.path.basename(args.config), args.config
    ).load_module()
    config = experiment.config

    work_path = config['workdir']
    run_name = config['run_name']
    if args.scene_name:
        run_name = f"{args.scene_name}_{config['seed']}"
    params_path = os.path.join(work_path, run_name, "params.npz")

    if not os.path.exists(params_path):
        print(f"ERROR: {params_path} not found. Run SLAM first.")
        exit(1)

    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(work_path, run_name, "splat_rgb.ply")

    export_cloudcompare_ply(params_path, output_path, args.opacity_threshold)
