from ultralytics import YOLO

# Load a COCO-pretrained YOLO26n model
model = YOLO("yolo26n.pt")

results = model("person.jpg", classes=[0])  # class 0 = person
results[0].show() 