# AIfAR

### Create venv and run the test scripts

1. sudo apt update && sudo apt install python3-venv -y
2. python3 -m venv myenv
3. source myenv/bin/activate
4. pip install ultralytics transformers torch pillow requests
5. python3 test/test_YOLO26.py || python3 test/test_DA.py

To run the video interface script locally, run:

1. pip install openvino (only if you run on CPU and not on CUDA or MPS)
2. source myenv/bin/activate
3. python3 test/test_videointerface.py