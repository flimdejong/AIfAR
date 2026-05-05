import cv2
import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO
from transformers import pipeline

import os
current_dir = os.path.dirname(os.path.abspath(__file__))
yolo_dir_cpu = os.path.join(current_dir, "..", "resource", "yolov8n", "yolov8n.onnx") # use the yolov8n_openvino_model/ directory from outside the current folder.
yolo_dir_gpu = os.path.join(current_dir, "..", "resource", "yolo26n.pt")

device = "cuda" if torch.cuda.is_available() else "cpu"

if device == "cpu":
    model = YOLO(yolo_dir_cpu, task="detect")
    depth_pipe = pipeline(task="depth-estimation", 
                      model="Intel/dpt-swinv2-tiny-256", # use a smaller model for CPU to speed up inference
                      device=-1)  # use CPU for depth estimation as well
else:
    model = YOLO(yolo_dir_gpu, task="detect")
    depth_pipe = pipeline(task="depth-estimation", 
                      model="depth-anything/Depth-Anything-V2-Small-hf",
                      device=0) # use GPU for depth estimation if available


cap = cv2.VideoCapture(0)  # /dev/video0. change this if PROBLEM!!!
frame_count = 0
person_depth = 0.0

while True:
    ret, frame = cap.read()
    frame_count += 1
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # tracking (should give consistent IDs across frames)
    results = model.track(rgb, persist=True, classes=[0], imgsz=320, verbose=False)
    boxes = results[0].boxes

    if boxes is not None and len(boxes) > 0 and boxes.id is not None:
        for box, track_id in zip(boxes, boxes.id.tolist()):
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            tid = int(track_id)

            # depth estimation using depth-anything.
            if frame_count % 5 == 0:  # only every 5th frame
                pil_frame = Image.fromarray(rgb)
                person_patch = pil_frame.crop((x1, y1, x2, y2))
                depth_result = depth_pipe(person_patch)
                person_depth = np.array(depth_result["predicted_depth"]).mean()

                # draw bbox
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, f"ID:{tid} depth:{person_depth:.2f}", (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    cv2.imshow("Test", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()