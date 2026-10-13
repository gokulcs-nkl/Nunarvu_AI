import torch
import os
import sys

print("Checking torch...")
print(f"Torch version: {torch.__version__}")

print("Attempting to load face recognition models...")
try:
    from facenet_pytorch import InceptionResnetV1, MTCNN
    mtcnn = MTCNN(keep_all=True)
    resnet = InceptionResnetV1(pretrained='vggface2').eval()
    print("[OK] Face recognition models loaded successfully")
except Exception as e:
    print(f"[ERROR] Face recognition models: {e}")

print("Attempting to load YOLOv5 via torch.hub...")
try:
    # Set home to current dir to avoid permission issues
    os.environ['TORCH_HOME'] = os.getcwd()
    model = torch.hub.load('ultralytics/yolov5', 'yolov5s', pretrained=True)
    print("[OK] YOLOv5 model loaded successfully")
except Exception as e:
    print(f"[ERROR] YOLOv5: {e}")

print("Attempting to load YOLOv8 via ultralytics...")
try:
    from ultralytics import YOLO
    model = YOLO('yolov8n.pt')
    print("[OK] YOLOv8 model loaded successfully")
except Exception as e:
    print(f"[ERROR] YOLOv8: {e}")

print("Done.")
