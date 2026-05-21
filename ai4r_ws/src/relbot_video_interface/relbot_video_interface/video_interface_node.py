#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point
import gi
import numpy as np
import cv2
from ultralytics import YOLO

gi.require_version('Gst', '1.0')
from gi.repository import Gst

# Some constants
IMG_SIZE = 320  # YOLO input size
PERSON_CLASS_ID = 0  # COCO class ID for 'person'
DEBUG = True  # Set to True to visualize input frames and debug info

# Proximity threshold: y1/height ratio above which we consider the person "close"
# y1 is the TOP of the bounding box. A high y1 (e.g. 0.6) means the box starts
# far down the frame → person is large/close. Tune this value to your liking.
STOP_THRESHOLD = 0.6

class VideoInterfaceNode(Node):
    def __init__(self):
        super().__init__('video_interface')
        self.position_pub = self.create_publisher(Point, '/object_position', 10)

        self.declare_parameter('gst_pipeline', (
            'udpsrc port=5000 caps="application/x-rtp,media=video,'
            'encoding-name=H264,payload=96" ! '
            'rtph264depay ! avdec_h264 ! videoconvert ! '
            'video/x-raw,format=RGB ! appsink name=sink'
        ))

        pipeline_str = self.get_parameter('gst_pipeline').value

        self.model = YOLO('yolov8n.pt')

        # Initialize GStreamer and build pipeline
        Gst.init(None)
        self.pipeline = Gst.parse_launch(pipeline_str)
        self.sink = self.pipeline.get_by_name('sink')
        self.sink.set_property('drop', True)
        self.sink.set_property('max-buffers', 1)
        self.pipeline.set_state(Gst.State.PLAYING)

        self.timer = self.create_timer(1.0 / 30.0, self.on_timer)
        self.get_logger().info('VideoInterfaceNode initialized, streaming at 30Hz')

        self.target_id = None
        self.target_lost_frames = 0

    def on_timer(self):
        sample = self.sink.emit('pull-sample')
        if not sample:
            return

        buf = sample.get_buffer()
        caps = sample.get_caps()
        width = caps.get_structure(0).get_value('width')
        height = caps.get_structure(0).get_value('height')
        ok, mapinfo = buf.map(Gst.MapFlags.READ)
        if not ok:
            return

        frame = np.frombuffer(mapinfo.data, np.uint8).reshape(height, width, 3).copy()
        buf.unmap(mapinfo)

        results = self.model.track(frame, persist=True, classes=[PERSON_CLASS_ID], imgsz=IMG_SIZE, verbose=False)
        boxes = results[0].boxes

        if boxes is None or boxes.id is None:
            return

        coords = boxes.xyxy.int().tolist()
        ids = boxes.id.int().tolist()

        if self.target_id is not None and self.target_id not in ids:
            self.target_lost_frames += 1
            if self.target_lost_frames > 30:
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

            # Proximity proxy: how far down the frame the TOP of the box is.
            # Range 0.0 (top of image, person far) → 1.0 (bottom, person very close).
            proximity = y1 / height

            if proximity >= STOP_THRESHOLD:
                z = 10001.0  # Signal robot to stop
            else:
                z = proximity  # Normal approach: low value = far, high = close

            msg = Point()
            msg.x = float(x_center)
            msg.y = 0.0
            msg.z = z
            self.position_pub.publish(msg)

            if DEBUG:
                color = (0, 0, 255) if z == 10001.0 else (0, 255, 0)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f'prox:{proximity:.2f} z:{z:.0f}', (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                cv2.imshow('Detection Stream', cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                cv2.waitKey(1)
                self.get_logger().debug(f'Published position: ({msg.x}, {msg.y}, {msg.z})')

    def destroy_node(self):
        self.pipeline.set_state(Gst.State.NULL)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = VideoInterfaceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()