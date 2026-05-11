# AIfAR

# Setup
git clone https://github.com/UAV-Centre-ITC/AI4R_RELBot.git
cd AI4R_RELBot
chmod +x assignment1_setup.sh

Add "ultralytics==8.4.38" "lapx>=0.5.12" && \ to the dockerfile or install in current runtime docker itself

# Running
Run setup script: ./assignment1_setup.sh

Navigate to: cd /ai4r_ws

Then colcon build and source
colcon build --packages-select relbot_video_interface
source install/setup.bash

Launch the rosnode
ros2 launch relbot_video_interface video_interface.launch.py

## Running at home
Install Gstreamer: sudo apt install gstreamer1.0-plugins-ugly 

### Start webcam host
gst-launch-1.0 -v \
  v4l2src device=/dev/video0 ! \
  image/jpeg,width=320,height=240,framerate=30/1 ! \
  jpegdec ! videoconvert ! \
  x264enc tune=zerolatency bitrate=800 speed-preset=ultrafast ! \
  rtph264pay config-interval=1 pt=96 ! \
  udpsink host=127.0.0.1 port=5000

### Verify topic output on object_position
Attach second shell to container (host):
docker exec -it relbot_ai4r_assignment1 bash

Then inside:
source /ai4r_ws/install/setup.bash
ros2 topic echo /object_position

### Create venv and run the test scripts. RUN FROM INSIDE /relbot_video/interface

1. sudo apt update && sudo apt install python3-venv -y
2. python3 -m venv myenv
3. source myenv/bin/activate
4. pip install ultralytics transformers torch pillow requests
5. python3 test/test_YOLO26.py || python3 test/test_DA.py

To run the video interface script locally, run:

1. pip install onnxruntime. if you have nvidia gpu do: pip install onnxruntime-gpu
2. source myenv/bin/activate
3. python3 test/test_videointerface.py