# AIfAR

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