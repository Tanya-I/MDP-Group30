# MDP-Group30: Multidisciplinary Design Project

This repository contains all the code, models, and documentation for **MDP-Group30**, developed as part of the NTU Multidisciplinary Design Project.  
---

## Project Structure
MDP-Group30/
├── Image Recognition/ # Image recognition model and weights
│ ├── recognition_local.py
│ ├── v1.pt
└── README.md

---

## Image Recognition Module

The **Image Recognition** folder contains the **basic image recognition model** used in this project.  
It includes the PyTorch model weights (`v1.pt`) and the Python script `recognition_local.py` for local testing and inference.
---
### Requirements 
Ensure that both recognition_local.py and v1.pt are in the same folder when running the script.
Before running the script, make sure you have the required dependencies installed:

pip install ultralytics opencv-python numpy

---

### Running the Model Locally

You can test the model on your local machine by running the following command inside the `Image Recognition` directory:

```bash
python recognition_local.py test.jpg out_b.jpg --model v1.pt --conf 0.6

Argument Explanation
test.jpg :	Input image you want to run the model on
out_b.jpg :	Output image that will be saved with detected objects drawn
--model v1.pt :	The PyTorch model weights file
--conf 0.6 :	Confidence threshold for detections (default: 0.6)

Example:
```bash
python recognition_local.py sample_input.jpg result_output.jpg --model v1.pt --conf 0.6

This will take sample_input.jpg, perform detection using the YOLO-based model, and save the result as result_output.jpg with bounding boxes and labels.