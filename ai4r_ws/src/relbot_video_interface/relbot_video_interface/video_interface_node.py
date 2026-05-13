#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
import gi
import numpy as np
import cv2
from ultralytics import YOLO
from PIL import Image
from transformers import pipeline
import torch

gi.require_version('Gst', '1.0')
from gi.repository import Gst

# Some constants
IMG_SIZE = 320  # YOLO input size. onnx is also exported with this size!! To change: `yolo export model=yolov8n.pt format=onnx imgsz=NEWSIZE` in terminal.
PERSON_CLASS_ID = 0  # COCO class ID for 'person'
DEBUG = True  # Set to True to visualize input frames and debug info

class VideoInterfaceNode(Node):
    def __init__(self):
        super().__init__('video_interface')
        # Publisher: sends object position to the RELBot
        # Topic `/object_position` is watched by the robot controller for actuation
        self.position_pub = self.create_publisher(Point, '/object_position', 10)

        # Declare GStreamer pipeline + YOLO model path as parameters for flexibility
        self.declare_parameter('gst_pipeline', (
            'udpsrc port=5000 caps="application/x-rtp,media=video,'
            'encoding-name=H264,payload=96" ! '
            'rtph264depay ! avdec_h264 ! videoconvert ! '
            'video/x-raw,format=RGB ! appsink name=sink'
        ))

        pipeline_str = self.get_parameter('gst_pipeline').value

        # Select device for inference and choose appropriate depth estimation model
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.get_logger().info(f'Using device: {self.device}')
        self.model = YOLO('yolov8n.pt')

        if self.device == 'cpu':
           self.depth_pipe = pipeline(
               task='depth-estimation',
               model='Intel/dpt-swinv2-tiny-256',
               device=-1
           )
        else:
           self.depth_pipe = pipeline(
               task='depth-estimation',
               model='Intel/dpt-swinv2-tiny-256',
               device=0
           )

        # Initialize GStreamer and build pipeline
        Gst.init(None)
        self.pipeline = Gst.parse_launch(pipeline_str)
        self.sink = self.pipeline.get_by_name('sink')
        # Drop late frames to ensure real-time processing
        self.sink.set_property('drop', True)
        self.sink.set_property('max-buffers', 1)
        self.pipeline.set_state(Gst.State.PLAYING)

        # Timer: fires at ~30Hz to pull frames and publish positions
        # The period (1/30) sets how often on_timer() is called
        self.timer = self.create_timer(1.0 / 30.0, self.on_timer)
        self.get_logger().info('VideoInterfaceNode initialized, streaming at 30Hz')

        self.target_id = None

    def on_timer(self):
        # Pull the latest frame from the GStreamer appsink
        sample = self.sink.emit('pull-sample')
        if not sample:
            # No new frame available
            return

        buf = sample.get_buffer()
        caps = sample.get_caps()
        width = caps.get_structure(0).get_value('width')
        height = caps.get_structure(0).get_value('height')
        ok, mapinfo = buf.map(Gst.MapFlags.READ)
        if not ok:
            # Failed to map buffer data
            return

        # Convert raw buffer to numpy array [height, width, channels]
        frame = np.frombuffer(mapinfo.data, np.uint8).reshape(height, width, 3).copy()
        buf.unmap(mapinfo)

        # TODO: Insert detection/tracking logic here to compute object position
        results = self.model.track(frame, persist=True, classes=[PERSON_CLASS_ID], imgsz=IMG_SIZE, verbose=False) # yolo takes care of resizing.
        boxes = results[0].boxes

        if boxes is None or boxes.id is None:
            return
        
        coords = boxes.xyxy.int().tolist()       # [[x1,y1,x2,y2], ...]
        ids = boxes.id.int().tolist()            # [id, ...]
        
        if self.target_id is not None and self.target_id not in ids:
            self.target_lost_frames += 1
            if self.target_lost_frames > 30:  # ~1 second at 30fps
                self.target_id = None
                self.target_lost_frames = 0
            return
        else:
            self.target_lost_frames = 0

        for (x1, y1, x2, y2), tid in zip(coords, ids):
            if self.target_id is None:
                self.target_id = tid
            if tid != self.target_id:
                continue

            x_center = (x1 + x2) / 2.0

            pil_frame = Image.fromarray(frame)
            person_patch = pil_frame.crop((x1, y1, x2, y2))
            depth_result = self.depth_pipe(person_patch)

            depth_map = np.array(depth_result['predicted_depth'])
            #print(f"depth shape: {depth_map.shape}")
            # print(f"min: {depth_map.min():.2f}, max: {depth_map.max():.2f}, mean: {depth_map.mean():.2f}")
            scale_y = depth_map.shape[0] / frame.shape[0]
            scale_x = depth_map.shape[1] / frame.shape[1]

            cx = int(((x1 + x2) / 2) * scale_x)
            cy = int(((y1 + y2) / 2) * scale_y)
            person_depth = float(depth_map[cy, cx])

            # Publish person position as a Point message (x=center_x, y=0, z=depth) for the robot controller
            msg = Point()
            msg.x = float(x_center)  # object center x-coordinate
            msg.y = 0.0  # y-coordinate unused, assumed flat ground.
            msg.z = float(person_depth)  # depth from deep net
            self.position_pub.publish(msg)

            # draw boxes
            if DEBUG:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                #cv2.putText(frame, f'ID:{tid} depth:{person_depth:.2f}', (x1, y1 - 10),
                #            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow('Detection Stream', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                cv2.waitKey(1)
                self.get_logger().debug(f'Published position: ({msg.x}, {msg.y}, {msg.z})')

    def destroy_node(self):
        # Cleanup GStreamer resources on shutdown
        self.pipeline.set_state(Gst.State.NULL)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = VideoInterfaceNode()
    try:
        rclpy.spin(node)  # Keep node alive, invoking on_timer periodically
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()