import glob
import os
from pathlib import Path
from typing import Dict, List, Optional, Union

import numpy as np
import torch
from natsort import natsorted

from .basedataset import GradSLAMDataset


class WheeltecDataset(GradSLAMDataset):
    """
    Dataset class for Wheeltec robot with Orbbec Astra depth camera.
    Expects data in the following structure:
        <input_folder>/
            rgb/          # RGB images (*.jpg or *.png)
            depth/        # Depth images (*.png, uint16, millimeters)
            poses/        # Optional wheel odometry poses (*.npy, 4x4 matrices)
    """

    def __init__(
        self,
        config_dict,
        basedir,
        sequence,
        stride: Optional[int] = None,
        start: Optional[int] = 0,
        end: Optional[int] = -1,
        desired_height: Optional[int] = 480,
        desired_width: Optional[int] = 640,
        load_embeddings: Optional[bool] = False,
        embedding_dir: Optional[str] = "embeddings",
        embedding_dim: Optional[int] = 512,
        **kwargs,
    ):
        self.input_folder = os.path.join(basedir, sequence)
        self.pose_path = os.path.join(self.input_folder, "poses")
        if not os.path.isdir(self.pose_path):
            self.pose_path = None
        super().__init__(
            config_dict,
            stride=stride,
            start=start,
            end=end,
            desired_height=desired_height,
            desired_width=desired_width,
            load_embeddings=load_embeddings,
            embedding_dir=embedding_dir,
            embedding_dim=embedding_dim,
            **kwargs,
        )

    def get_filepaths(self):
        color_paths = natsorted(glob.glob(os.path.join(self.input_folder, "rgb", "*.jpg")))
        if len(color_paths) == 0:
            color_paths = natsorted(glob.glob(os.path.join(self.input_folder, "rgb", "*.png")))
        depth_paths = natsorted(glob.glob(os.path.join(self.input_folder, "depth", "*.png")))
        embedding_paths = None
        if self.load_embeddings:
            embedding_paths = natsorted(glob.glob(f"{self.input_folder}/{self.embedding_dir}/*.pt"))
        return color_paths, depth_paths, embedding_paths

    def load_poses(self):
        if self.pose_path is None:
            # No odometry available — return identity poses.
            # SplaTAM will estimate poses via visual tracking.
            return [torch.eye(4).float() for _ in range(self.num_imgs)]
        posefiles = natsorted(glob.glob(os.path.join(self.pose_path, "*.npy")))
        poses = []
        for posefile in posefiles:
            c2w = torch.from_numpy(np.load(posefile)).float()
            poses.append(c2w)
        return poses
