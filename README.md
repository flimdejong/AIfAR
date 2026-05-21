# AIfAR

# Setup
```bash
git clone https://github.com/flimdejong/AIfAR.git
cd AI4R_RELBot
chmod +x assignment1_setup.sh
```

# Running
Run setup script

```bash
./assignment1_setup.sh
```

Navigate to /ai4r_ws
Then colcon build and source:
```bash
colcon build --packages-select relbot_video_interface
source install/setup.bash
```

Launch the rosnode with the main code:
```bash
ros2 launch relbot_video_interface video_interface.launch.py
```

## Running on RELBot
```bash
Connect with ssh using
ssh -X pi@<ip>
```

### Start webcam host
```bash
gst-launch-1.0 -v \
  v4l2src device=/dev/video0 ! \
  image/jpeg,width=320,height=240,framerate=30/1 ! \
  jpegdec ! videoconvert ! \
  x264enc tune=zerolatency bitrate=800 speed-preset=ultrafast ! \
  rtph264pay config-interval=1 pt=96 ! \
  udpsink host=<local_ip> port=5000
```

### Run Xenomai & bridge
While connected with the robot, build the other nodes.

Note: If you get an error, close both programs (not terminals), and rerun terminal 1 with the Xenomai first.

In terminal 1:
```bash
source ~/ai4r_ws/install/setup.bash
cd ~/ai4r_ws/
sudo ./build/demo/demo   # low-level motor and FPGA interface
```

In terminal 2:
```bash
source ~/ai4r_ws/install/setup.bash
ros2 launch sequence_controller sequence_controller.launch.py   # high-level state machine
```

### Export ROS Domain
Do this for each new docker terminal you open.
```bash
export ROS_DOMAIN_ID=<RELBot_ID>   # e.g., 8 for RELBot08
```

## Verify topic output on object_position
Attach second shell to container (host):
```bash
docker exec -it relbot_ai4r_assignment1 bash
```

Then inside:
```bash
source /ai4r_ws/install/setup.bash
ros2 topic echo /object_position
```

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





<!-- gst-launch-1.0 -v \
v4l2src device=/dev/video2 ! \
image/jpeg,width=320,height=240,framerate=30/1 ! \
jpegdec ! videoconvert ! \
x264enc tune=zerolatency bitrate=800 speed-preset=ultrafast ! \
rtph264pay config-interval=1 pt=96 ! \
udpsink host=192.168.0.241 port=5000

ramforpresident -->