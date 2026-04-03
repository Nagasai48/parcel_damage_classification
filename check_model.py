import os
import tensorflow as tf
from tensorflow.keras.models import load_model

model_path = r'c:\Users\kukka\Desktop\parcel_damage_classification\models\resnet34_model.h5'

print("Script started...")
print(f"Checking for model at: {model_path}")
if os.path.exists(model_path):
    print("Model file exists!")
    try:
        model = load_model(model_path, compile=False)
        print(f"Model loaded!")
        print(f"Input shape: {model.input_shape}")
        print(f"Output shape: {model.output_shape}")
        
    except Exception as e:
        print(f"Error loading model: {e}")
else:
    print("Model not found at that path.")
    # Try searching in the current directory also
    alt_path = 'resnet34_model.h5'
    if os.path.exists(alt_path):
        print(f"Found at {alt_path} instead!")
    else:
        print("Not found in current directory either.")
