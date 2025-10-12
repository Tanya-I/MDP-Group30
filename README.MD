# MDP-Group30: Multidisciplinary Design Project

This repository contains all the code, models, and documentation for **MDP-Group30**, developed as part of the NTU Multidisciplinary Design Project.

---

## Project Structure

```
MDP-Group30/
├── Image Recognition/          # Image recognition model and weights
│   ├── recognition_local.py
│   ├── v1.pt
├── RPI/                        # Raspberry Pi communication and control scripts
│   ├── a5_pc.py
│   ├── a5_rpi.py
│   ├── bt_message_mapper.py
│   ├── camera_test.py
│   ├── rpi_android_bt.py
│   ├── rpi_stm.py
└── README.md
```

---

## Image Recognition Module

The **Image Recognition** folder contains the **basic image recognition model** used in this project.

It includes the PyTorch model weights (`v1.pt`) and the Python script `recognition_local.py` for local testing and inference.

#### Requirements

> **Note:** Ensure that both `recognition_local.py` and `v1.pt` are in the same folder when running the script.

Before running the script, make sure you have the required dependencies installed:

```bash
pip install ultralytics opencv-python numpy
```

#### Running the Model Locally

You can test the model on your local machine by running the following command inside the `Image Recognition` directory:

```bash
python recognition_local.py test.jpg out_b.jpg --model v1.pt --conf 0.6
```

#### Argument Explanation

| Argument | Description |
|----------|-------------|
| `test.jpg` | Input image you want to run the model on |
| `out_b.jpg` | Output image that will be saved with detected objects drawn |
| `--model v1.pt` | The PyTorch model weights file |
| `--conf 0.6` | Confidence threshold for detections (default: 0.6) |

#### Example

```bash
python recognition_local.py sample_input.jpg result_output.jpg --model v1.pt --conf 0.6
```

This will take `sample_input.jpg`, perform detection using the YOLO-based model, and save the result as `result_output.jpg` with bounding boxes and labels.

---

## Raspberry Pi Module

The **RPI** folder contains Python scripts for communication between the Raspberry Pi, STM32 microcontroller, Android device, and PC. These scripts handle camera operations, Bluetooth communication, serial communication, and image recognition integration.

### File Descriptions

#### `camera_test.py`
Basic camera testing script that streams live camera feed via Flask web server on port 5000. Used to verify camera functionality and preview the camera feed in a web browser.

**Usage:**
```bash
python camera_test.py
# Visit: http://<rpi_ip>:5000
```

#### `rpi_stm.py`
Simple serial communication script for testing STM32-Raspberry Pi communication via USB. Provides an interactive console to send and receive messages between RPI and STM32.

**Features:**
- Connects via `/dev/ttyACM0` at 115200 baud
- Bidirectional messaging (RPI ↔ STM32)
- Interactive command-line interface

**Usage:**
```bash
python rpi_stm.py
```

#### `a5_rpi.py`
Main RPI script for checklist task A5. Handles camera capture, STM32 communication, and provides Flask API endpoints for PC to fetch images and send commands.

**Features:**
- Live camera preview at `/preview`
- Photo capture on STM32 "ready" signal
- API endpoints: `/get_photo`, `/capture`, `/send_command`
- Automatic cleanup of conflicting processes

**Usage:**
```bash
python a5_rpi.py
```

#### `a5_pc.py`
PC-side script for checklist task A5. Fetches captured images from RPI, runs inference using the local model server, and sends back classification results (y/n) based on whether the detected object is valid.

**Requirements:**
- RPI running `a5_rpi.py`
- Local inference server running (uvicorn)
- Configure `PI_URL` and `SERVER_URL` in the script

**Usage:**
```bash
python a5_pc.py
```

#### `bt_message_mapper.py`
Utility class for mapping messages between Android Bluetooth format and RPI internal format. Handles formatting and parsing of robot positions, object positions, targets, and task completion messages.

**Message Formats:**
- `ROBOT, X, Y, DIRECTION`
- `OBJECT#, X, Y, DIRECTION`
- `TARGET, OBSTACLE_NUMBER, TARGET_ID`
- `WEEK#_TASK_DONE`
- `GRID_COMPLETE`

#### `rpi_android_bt.py`
Bluetooth RFCOMM server for communication between Raspberry Pi and Android device. Integrates `bt_message_mapper.py` for proper message formatting and parsing.

**Features:**
- SPP (Serial Port Profile) Bluetooth communication
- Interactive console for sending formatted messages
- Automatic message parsing from Android
- Command shortcuts: `robot`, `object`, `target`, `task`

**Usage:**
```bash
python rpi_android_bt.py
```

**Example Commands:**
```bash
robot 5 10 N          # Send robot position
object 3 15 8 E       # Send object 3 position
target 1 15           # Send target assignment
task 8                # Send Week 8 task completion
raw hello world       # Send raw message
```

### Dependencies

Install required packages for RPI scripts:

```bash
pip install opencv-python flask pyserial pybluez requests
```

---