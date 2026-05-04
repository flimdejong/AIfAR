from ultralytics import YOLO
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
yolo_dir = os.path.join(current_dir, "..", "resource", "yolo26n.pt")
# Load a COCO-pretrained YOLO26n model
model = YOLO(yolo_dir)

test_img = os.path.join(current_dir, "..", "resource", "person.jpg")
results = model(test_img, classes=[0])  # class 0 = person
results[0].show() 