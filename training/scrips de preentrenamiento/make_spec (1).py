#!/usr/bin/env python3
"""Genera el spec de TAO yolo_v4 con anchors calculados de tus etiquetas KITTI.
Uso: python3 make_spec.py --kitti kitti --out specs/yolo_v4_train.txt [--epochs 60] [--batch 4]
"""
import argparse, glob
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--kitti", default="kitti")
ap.add_argument("--out", default="specs/yolo_v4_train.txt")
ap.add_argument("--epochs", type=int, default=60)
ap.add_argument("--batch", type=int, default=4)
ap.add_argument("--eval-batch", type=int, default=1)
ap.add_argument("--conf", type=float, default=0.01)
ap.add_argument("--topk", type=int, default=100)
ap.add_argument("--ckpt-interval", type=int, default=10)
ap.add_argument("--net-w", type=int, default=736)   # múltiplo de 32
ap.add_argument("--net-h", type=int, default=1600)  # múltiplo de 32
ap.add_argument("--img-w", type=int, default=720)
ap.add_argument("--pretrained", default="/workspace/tao-experiments/pretrained/pretrained_object_detection_vresnet18/resnet_18.hdf5")
a = ap.parse_args()

classes = [c for c in Path(a.kitti, "classes.txt").read_text().split("\n") if c]
sx = a.net_w / a.img_w
wh = []
for f in glob.glob(f"{a.kitti}/train/labels/*.txt"):
    for ln in open(f):
        p = ln.split()
        if len(p) >= 8:
            x1, y1, x2, y2 = map(float, p[4:8])
            wh.append(((x2 - x1) * sx, y2 - y1))
wh = np.array(wh)

def iou(b, c):
    i = np.minimum(b[:, None, 0], c[None, :, 0]) * np.minimum(b[:, None, 1], c[None, :, 1])
    return i / (b[:, None, 0] * b[:, None, 1] + c[None, :, 0] * c[None, :, 1] - i)

rng = np.random.default_rng(0)
cent = wh[rng.choice(len(wh), 9, replace=False)]
for _ in range(100):
    asg = iou(wh, cent).argmax(1)
    new = np.array([np.median(wh[asg == k], 0) if (asg == k).any() else cent[k] for k in range(9)])
    if np.allclose(new, cent): break
    cent = new
cent = cent[np.argsort(cent[:, 0] * cent[:, 1])]
fmt = lambda c: "[" + ", ".join(f"({w:.2f}, {h:.2f})" for w, h in c) + "]"
print("anchors small/mid/big:", fmt(cent[:3]), fmt(cent[3:6]), fmt(cent[6:]))

base = f"/workspace/tao-experiments/{Path(a.kitti).name}"
mapping = "\n".join(f'  target_class_mapping {{ key: "{c}" value: "{c}" }}' for c in classes)
spec = f'''random_seed: 42
yolov4_config {{
  big_anchor_shape: "{fmt(cent[6:])}"
  mid_anchor_shape: "{fmt(cent[3:6])}"
  small_anchor_shape: "{fmt(cent[:3])}"
  box_matching_iou: 0.25
  matching_neutral_box_iou: 0.5
  arch: "resnet"
  nlayers: 18
  arch_conv_blocks: 2
  loss_loc_weight: 0.8
  loss_neg_obj_weights: 100.0
  loss_class_weights: 0.5
  label_smoothing: 0.0
  big_grid_xy_extend: 0.05
  mid_grid_xy_extend: 0.1
  small_grid_xy_extend: 0.2
  freeze_bn: false
  force_relu: false
}}
training_config {{
  batch_size_per_gpu: {a.batch}
  num_epochs: {a.epochs}
  enable_qat: false
  checkpoint_interval: {a.ckpt_interval}
  learning_rate {{
    soft_start_cosine_annealing_schedule {{
      min_learning_rate: 1e-7
      max_learning_rate: 1e-4
      soft_start: 0.3
    }}
  }}
  regularizer {{
    type: L1
    weight: 3e-5
  }}
  optimizer {{
    adam {{
      epsilon: 1e-7
      beta1: 0.9
      beta2: 0.999
      amsgrad: false
    }}
  }}
  pretrain_model_path: "{a.pretrained}"
}}
eval_config {{
  average_precision_mode: SAMPLE
  batch_size: {a.eval_batch}
  matching_iou_threshold: 0.5
}}
nms_config {{
  confidence_threshold: {a.conf}
  clustering_iou_threshold: 0.5
  top_k: {a.topk}
}}
augmentation_config {{
  hue: 0.05
  saturation: 1.3
  exposure: 1.3
  vertical_flip: 0
  horizontal_flip: 0
  jitter: 0.1
  output_width: {a.net_w}
  output_height: {a.net_h}
  output_channel: 3
  randomize_input_shape_period: 0
  mosaic_prob: 0
  mosaic_min_ratio: 0.2
}}
dataset_config {{
  data_sources: {{
    label_directory_path: "{base}/train/labels"
    image_directory_path: "{base}/train/images"
  }}
  include_difficult_in_training: true
{mapping}
  validation_data_sources: {{
    label_directory_path: "{base}/val/labels"
    image_directory_path: "{base}/val/images"
  }}
}}
'''
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
Path(a.out).write_text(spec)
print("spec escrito en", a.out)
