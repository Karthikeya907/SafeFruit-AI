"""Merged SAFEFRUIT AI Application."""

from __future__ import annotations
from pathlib import Path
from serial.tools import list_ports
from typing import Any, Dict, List, Optional
import base64
import cv2
import datetime as dt
import json
import numpy as np
import os
from flask import Flask, request, jsonify, Response, send_from_directory
import requests
import serial
import threading
import time
import queue
import traceback
import webbrowser

# ==== CONFIG ====
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
IMAGES_DIR = BASE_DIR / "images"
OUTPUT_DIR = IMAGES_DIR / "output"
for directory in (IMAGES_DIR, OUTPUT_DIR):
    directory.mkdir(parents=True, exist_ok=True)

def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
    return {}

CONFIG_DATA = _load_config()
CAMERA_INDEX = int(CONFIG_DATA.get("camera_index", 0))
AI_API_KEY = str(CONFIG_DATA.get("api_key", ""))
SERIAL_PORT = str(CONFIG_DATA.get("serial_port") or CONFIG_DATA.get("com_port") or "")
SERIAL_BAUDRATE = 9600

def save_config(camera_index: int, api_key: str, serial_port: str) -> None:
    payload = {
        "camera_index": camera_index,
        "api_key": api_key,
        "serial_port": serial_port,
        "com_port": serial_port
    }
    with CONFIG_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

def load_config() -> Dict[str, Any]:
    global CONFIG_DATA, CAMERA_INDEX, AI_API_KEY, SERIAL_PORT
    CONFIG_DATA = _load_config()
    CAMERA_INDEX = int(CONFIG_DATA.get("camera_index", 0))
    AI_API_KEY = str(CONFIG_DATA.get("api_key", ""))
    SERIAL_PORT = str(CONFIG_DATA.get("serial_port") or CONFIG_DATA.get("com_port") or "")
    return CONFIG_DATA


# ==== DECISION ====
class DecisionEngine:
    def make_decision(self, analyses: list) -> dict:
        if not analyses:
            return self._build_result('Unknown', 'FAIL', 0.0, [], 'No analysis results were received.')
        fruit_name = analyses[0].get('fruit_name', 'Unknown')
        detected_defects = []
        for result in analyses:
            defects = result.get('detected_defects') or []
            for defect in defects:
                defect_type = str(defect.get('type') or defect.get('name') or 'Unknown')
                confidence = float(defect.get('confidence') or 0.0)
                detected_defects.append({'type': defect_type, 'confidence': confidence})

        has_reject = any(d.get('type') in {'Rotten', 'Mold'} for d in detected_defects)
        if has_reject:
            return self._build_result(fruit_name, 'FAIL', 100.0, detected_defects, 'Rotten or mold detected.')

        area_related = [d for d in detected_defects if d.get('type') in {'Black_Spot', 'Brown_Spot', 'Damage'}]
        if area_related:
            highest_area = max((float(d.get('coverage_percent') or d.get('confidence') or 0.0) for d in area_related), default=0.0)
            if highest_area > 20.0:
                return self._build_result(fruit_name, 'FAIL', 100.0, detected_defects, 'Surface defect area is too large.')

        return self._build_result(fruit_name, 'PASS', 100.0, detected_defects or [{'type': 'Healthy_Surface', 'confidence': 100.0}], 'Healthy fruit.')

    def _build_result(self, fruit_name, status, conf, defects, reason):
        return {'fruit_name': fruit_name, 'overall_status': status, 'confidence': conf, 'detected_defects': defects, 'reason': reason}

    def evaluate_stage1(self, result: dict) -> tuple[bool, str]:
        status = result.get('overall_status', 'FAIL')
        if status == 'FAIL':
            return False, result.get('reason', 'Failed Stage 1 AI Analysis')
        return True, 'Passed AI Analysis'

    def evaluate_stage3(self, mq135: float, ph: float) -> tuple[bool, str]:
        if mq135 > 100:
            return False, f'High gas levels detected ({mq135})'
        if ph < 3.0 or ph > 8.0:
            return False, f'Abnormal pH level ({ph})'
        return True, 'Chemical sensors within limits'

# ==== AI CLIENT ====
import requests, base64

GEMINI_MODEL = 'gemini-1.5-flash'
GEMINI_ENDPOINT = f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'

class AIClient:
    def __init__(self, api_key=None):
        self.api_key = api_key

    def analyze_images(self, frames: list) -> dict:
        if not frames:
            return {'fruit_name': 'Unknown', 'overall_status': 'FAIL', 'confidence': 0.0, 'detected_defects': [], 'reason': 'No images captured'}
        if not self.api_key:
            return {'fruit_name': 'Test Fruit', 'overall_status': 'PASS', 'confidence': 99.0, 'detected_defects': [], 'reason': 'No API key provided. Simulating success.'}
        
        prompt = 'You are inspecting a set of photos of a single piece of fruit rotated to show different angles on an automated sorting line. Analyze all the images to identify the fruit and detect any surface defects. Respond ONLY with raw JSON matching this structure: {"fruit_name": "Apple/Orange/etc", "confidence": 100, "detected_defects": [{"type": "Healthy_Surface/Rotten/Mold/Black_Spot/Brown_Spot/Damage", "confidence": 100, "coverage_percent": 0}], "overall_status": "PASS", "reason": ""}'
        
        url = f"{GEMINI_ENDPOINT}?key={self.api_key}"
        headers = {'Content-Type': 'application/json'}
        parts = [{'text': prompt}]
        
        for idx, frame in enumerate(frames):
            h, w = frame.shape[:2]
            max_dim = 512
            if max(h, w) > max_dim:
                scale = max_dim / float(max(h, w))
                frame = cv2.resize(frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            
            ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if ok:
                parts.append({
                    'inline_data': {
                        'mime_type': 'image/jpeg',
                        'data': base64.b64encode(buf.tobytes()).decode('ascii')
                    }
                })
        
        payload = {'contents': [{'parts': parts}]}
        
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=12)
            if r.status_code == 200:
                data = r.json()
                text = data['candidates'][0]['content']['parts'][0]['text']
                text = text.strip()
                if text.startswith('```'):
                    parts_split = text.split('```', 2)
                    if len(parts_split) > 1:
                        text = parts_split[1]
                    if text.startswith('json'):
                        text = text[4:]
                return json.loads(text.strip())
            else:
                return {'fruit_name': 'Unknown', 'overall_status': 'FAIL', 'confidence': 0.0, 'detected_defects': [], 'reason': f"HTTP {r.status_code}: {r.text}"}
        except Exception as e:
            return {'fruit_name': 'Unknown', 'overall_status': 'FAIL', 'confidence': 0.0, 'detected_defects': [], 'reason': f"AI Request failed: {e}"}

# ==== CAMERA ====
class CameraManager:
    def __init__(self):
        self.camera_index = 0
        self.capture = None

    def open(self):
        if self.capture is not None:
            self.capture.release()
        self.capture = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        time.sleep(0.5)
        if not self.capture.isOpened():
            self.capture = cv2.VideoCapture(self.camera_index)
            time.sleep(0.5)
        return self.capture.isOpened()

    def check_connection(self):
        return self.capture is not None and self.capture.isOpened()

    def capture_sequence(self, count=3, delay=2.0):
        frames = []
        for _ in range(count):
            if self.capture and self.capture.isOpened():
                ret, frame = self.capture.read()
                if ret and frame is not None:
                    frames.append(frame)
            time.sleep(delay)
        return frames

# ==== SERIAL COMM ====
class SerialController:
    def __init__(self):
        self.port = ""
        self.baudrate = SERIAL_BAUDRATE
        self.serial = None
        self.connected = False

    def is_connected(self):
        return self.connected and self.serial is not None and self.serial.is_open

    def connect(self):
        if self.is_connected():
            return True
        if not self.port:
            for p in list_ports.comports():
                if "arduino" in p.description.lower() or "ch340" in p.description.lower() or "serial" in p.description.lower():
                    self.port = p.device
                    break
        if not self.port:
            self.connected = False
            return False
            
        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=1)
            self.serial.setDTR(False)
            time.sleep(0.05)
            self.serial.setDTR(True)
            self.serial.setRTS(True)
            time.sleep(3)
            self.connected = True
            return True
        except serial.SerialException as e:
            print(f"Connection failed: {e}")
            self.connected = False
            self.serial = None
            return False

    def send_command(self, cmd: str):
        if self.is_connected():
            try:
                self.serial.write(f"{cmd}\n".encode())
                print(f"Sent: {cmd}")
            except serial.SerialException:
                self.connected = False
                self.serial = None

    def read_response(self) -> str:
        if self.is_connected():
            try:
                if self.serial.in_waiting > 0:
                    return self.serial.readline().decode().strip()
            except serial.SerialException:
                self.connected = False
                self.serial = None
        return ""

# ==== WEB SERVER (FLASK) ====
app = Flask(__name__, static_folder=str(BASE_DIR.parent / 'Web' / 'frontend'), static_url_path='')

camera = CameraManager()
ai_client = AIClient()
decision_engine = DecisionEngine()
serial_controller = SerialController()

state = {
    "is_running": False,
    "stage": "IDLE",
    "operation": "Waiting for START",
    "result": {}
}

sensors = {
    "mq135": "--",
    "ph": "--",
    "conveyor": "OFF",
    "washing": "OFF",
    "uv": "OFF",
    "stage1_door": "--",
    "stage3_door": "--",
    "distance": "--"
}

serial_msg_queue = queue.Queue()
logs_list = []

def log_message(msg: str):
    timestamp = dt.datetime.now().strftime("%H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)
    logs_list.append(full_msg)
    if len(logs_list) > 100:
        logs_list.pop(0)

def flush_serial_queue():
    if serial_controller.is_connected():
        try:
            serial_controller.serial.reset_input_buffer()
            time.sleep(0.05)
        except:
            pass
    while not serial_msg_queue.empty():
        try:
            serial_msg_queue.get_nowait()
        except queue.Empty:
            break

def wait_for_serial_message(target: str, timeout: float = 30.0) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        if stop_event.is_set():
            return False
        try:
            msg = serial_msg_queue.get(timeout=0.5)
            if target in msg:
                return True
        except queue.Empty:
            continue
    return False

current_frame_jpg = None
stop_event = threading.Event()

def update_status(stage: str, operation: str):
    global state
    state["stage"] = stage
    state["operation"] = operation
    log_message(f"[{stage}] {operation}")

def inspection_worker():
    global state, current_frame_jpg
    try:
        update_status("CHECKS", "Validating hardware...")
        if not serial_controller.is_connected():
            if not serial_controller.connect():
                raise RuntimeError("Failed to connect to Arduino serial port.")
        if not camera.check_connection():
            if not camera.open():
                raise RuntimeError("Failed to open USB camera.")

        update_status("STAGE 1", "System check successful. Starting conveyor belt...")
        flush_serial_queue()
        serial_controller.send_command("START_INSPECTION")

        while state["is_running"] and not stop_event.is_set():
            update_status("STAGE 1", "Waiting for Stage 1 Ultrasonic to detect fruit...")
            flush_serial_queue()
            
            if not wait_for_serial_message("TAKE_IMAGE_1", timeout=60.0):
                if stop_event.is_set():
                    break
                log_message("[STAGE 1] Timeout waiting for fruit detection at Stage 1.")
                continue

            update_status("STAGE 1", "Fruit detected. Capturing Image 1...")
            frames = []
            
            if camera.capture and camera.capture.isOpened():
                ret, frame = camera.capture.read()
                if ret and frame is not None:
                    frames.append(frame)
                    current_frame_jpg = cv2.imencode('.jpg', frame)[1].tobytes()
            time.sleep(1.5)
            
            update_status("STAGE 1", "Stepping conveyor for Image 2...")
            flush_serial_queue()
            serial_controller.send_command("STEP_CONVEYOR")
            if not wait_for_serial_message("TAKE_IMAGE_2", timeout=5.0):
                log_message("[STAGE 1] Warning: TAKE_IMAGE_2 timeout.")
            
            update_status("STAGE 1", "Capturing Image 2...")
            if camera.capture and camera.capture.isOpened():
                ret, frame = camera.capture.read()
                if ret and frame is not None:
                    frames.append(frame)
                    current_frame_jpg = cv2.imencode('.jpg', frame)[1].tobytes()
            time.sleep(1.5)

            update_status("STAGE 1", "Stepping conveyor for Image 3...")
            flush_serial_queue()
            serial_controller.send_command("STEP_CONVEYOR")
            if not wait_for_serial_message("TAKE_IMAGE_3", timeout=5.0):
                log_message("[STAGE 1] Warning: TAKE_IMAGE_3 timeout.")
            
            update_status("STAGE 1", "Capturing Image 3...")
            if camera.capture and camera.capture.isOpened():
                ret, frame = camera.capture.read()
                if ret and frame is not None:
                    frames.append(frame)
                    current_frame_jpg = cv2.imencode('.jpg', frame)[1].tobytes()
            time.sleep(1.5)

            update_status("STAGE 1", "Sending images to AI for Analysis...")
            config = load_config()
            ai_client.api_key = str(config.get("api_key", ai_client.api_key))
            
            stage1_result = ai_client.analyze_images(frames)
            
            state["result"] = {
                "fruit": stage1_result.get("fruit_name", "--"),
                "status": "ANALYZING",
                "confidence": stage1_result.get("confidence", 0),
                "defects": ", ".join([d.get("type", "Unknown") for d in stage1_result.get("detected_defects", [])]) or "None",
                "reason": stage1_result.get("reason", "")
            }

            stage1_pass, s1_reason = decision_engine.evaluate_stage1(stage1_result)
            if not stage1_pass:
                state["result"]["status"] = "NOT SAFE TO EAT"
                state["result"]["reason"] = f"Stage 1 failed: {s1_reason}"
                update_status("STAGE 1", f"FAIL: {s1_reason}. Opening door.")
                serial_controller.send_command("FAIL")
            else:
                state["result"]["status"] = "SAFE TO EAT"
                state["result"]["reason"] = "Passed Stage 1."
                update_status("STAGE 1", "PASS. Proceeding to Stage 2...")
                serial_controller.send_command("PASS")

            update_status("PROCESSING", "Waiting for hardware to finish...")
            flush_serial_queue()
            if not wait_for_serial_message("System ready for next fruit", timeout=60.0):
                log_message("[PROCESSING] Timeout waiting for system to finish operations.")
            
            time.sleep(1)
            update_status("STAGE 1", "Restarting inspection for next fruit...")
            serial_controller.send_command("START_INSPECTION")

    except Exception as exc:
        traceback.print_exc()
        state["result"]["status"] = "ERROR"
        state["result"]["reason"] = str(exc)
        log_message(f"Error in inspection worker: {exc}")
        try:
            serial_controller.send_command("STOP_SYSTEM")
        except:
            pass
    finally:
        if state.get("result", {}).get("status") == "ERROR":
            update_status("ERROR", "Inspection Failed")
        else:
            update_status("IDLE", "Inspection Complete")
        state["is_running"] = False

def hardware_monitor_thread():
    global current_frame_jpg
    while True:
        if not serial_controller.is_connected():
            time.sleep(0.5)
            continue
        
        try:
            if serial_controller.serial.in_waiting > 0:
                resp = serial_controller.serial.readline().decode('utf-8', errors='ignore').strip()
                if resp:
                    if not resp.startswith("distance:"):
                        log_message(f"Arduino: {resp}")
                    parts = resp.split(',')
                    for p in parts:
                        if ':' in p:
                            k, v = p.split(':', 1)
                            k = k.strip().lower()
                            v = v.strip()
                            if k in sensors:
                                sensors[k] = v
                    serial_msg_queue.put(resp)
        except Exception as e:
            print(f"Serial read error: {e}")
            serial_controller.connected = False
            serial_controller.serial = None

        if not state["is_running"]:
            if camera.capture and camera.capture.isOpened():
                ok, frame = camera.capture.read()
                if ok and frame is not None:
                    ok2, buf = cv2.imencode('.jpg', frame)
                    if ok2:
                        current_frame_jpg = buf.tobytes()
        
        time.sleep(0.05)

@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/api/telemetry', methods=['GET'])
def api_telemetry():
    return jsonify({
        "camera_connected": camera.capture is not None and camera.capture.isOpened(),
        "arduino_connected": serial_controller.is_connected(),
        "api_valid": bool(ai_client.api_key),
        "state": state,
        "sensors": sensors,
        "logs": logs_list
    })

@app.route('/api/start', methods=['POST'])
def api_start():
    if state["is_running"]:
        return jsonify({"error": "Already running"}), 400
    stop_event.clear()
    state["is_running"] = True
    threading.Thread(target=inspection_worker, daemon=True).start()
    return jsonify({"success": True})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    global stop_event
    stop_event.set()
    try:
        serial_controller.send_command("STOP_SYSTEM")
    except:
        pass
    update_status("IDLE", "Stopped by User")
    state["is_running"] = False
    return jsonify({"success": True})

@app.route('/api/config', methods=['GET', 'POST'])
def api_config():
    if request.method == 'POST':
        data = request.json or {}
        try:
            cam_idx = int(data.get("camera_index", 0))
        except (ValueError, TypeError):
            cam_idx = 0
        save_config(
            cam_idx, 
            str(data.get("api_key", "")),
            str(data.get("com_port") or data.get("serial_port") or "")
        )
        load_config()
        camera.camera_index = CAMERA_INDEX
        ai_client.api_key = AI_API_KEY
        if serial_controller.port != SERIAL_PORT:
            serial_controller.port = SERIAL_PORT
            if serial_controller.serial:
                try:
                    serial_controller.serial.close()
                except:
                    pass
                serial_controller.serial = None
                serial_controller.connected = False
        return jsonify({"success": True})
    return jsonify({
        "camera_index": CAMERA_INDEX,
        "com_port": SERIAL_PORT,
        "api_key": AI_API_KEY
    })

@app.route('/api/history', methods=['GET'])
def api_history():
    return jsonify([])

@app.route('/api/test/camera', methods=['POST'])
def test_camera():
    success = camera.open()
    return jsonify({"success": success})

@app.route('/api/test/arduino', methods=['POST'])
def test_arduino():
    success = serial_controller.connect()
    return jsonify({"success": success})

@app.route('/api/test/api', methods=['POST'])
def test_api():
    if not ai_client.api_key:
        return jsonify({"success": False, "message": "No API Key configured."})
    
    payload = {'contents': [{'parts': [{'text': "Hello, verify API key."}]}]}
    headers = {'Content-Type': 'application/json'}
    
    models_to_try = [
        GEMINI_MODEL,
        'gemini-3.6-flash',
        'gemini-3.5-flash',
        'gemini-2.5-flash',
        'gemini-flash-latest'
    ]
    seen = set()
    models_to_try = [x for x in models_to_try if not (x in seen or seen.add(x))]
    
    errors = []
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={ai_client.api_key}"
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                return jsonify({"success": True, "message": f"API Key is VALID and working (using {model})!"})
            elif r.status_code == 503:
                errors.append(f"503 unavailable for {model}")
                continue
            else:
                errors.append(f"{model}: HTTP {r.status_code} - {r.text}")
        except Exception as e:
            errors.append(f"Error with {model}: {e}")
            continue
            
    return jsonify({"success": False, "message": f"API check failed. Errors: {' | '.join(errors)}"})

@app.route('/api/chat', methods=['POST'])
def api_chat():
    data = request.json
    user_message = data.get("message", "")
    if not ai_client.api_key:
        return jsonify({"success": False, "error": "No API Key configured."})
    
    payload = {'contents': [{'parts': [{'text': user_message}]}]}
    headers = {'Content-Type': 'application/json'}
    
    models_to_try = [
        GEMINI_MODEL,
        'gemini-3.6-flash',
        'gemini-3.5-flash',
        'gemini-2.5-flash',
        'gemini-flash-latest'
    ]
    seen = set()
    models_to_try = [x for x in models_to_try if not (x in seen or seen.add(x))]
    
    last_error = "No models tried"
    for model in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={ai_client.api_key}"
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                res_data = r.json()
                reply = res_data['candidates'][0]['content']['parts'][0]['text']
                return jsonify({"success": True, "reply": reply})
            elif r.status_code == 503:
                last_error = f"503 unavailable for {model}"
                continue
            else:
                last_error = f"HTTP {r.status_code}"
        except Exception as e:
            last_error = f"Error with {model}: {e}"
            continue
            
    return jsonify({"success": False, "error": f"API request failed: {last_error}"})


def generate_video():
    blank_frame = cv2.imencode('.jpg', np.zeros((480, 640, 3), dtype=np.uint8))[1].tobytes()
    while True: # Keep video feed alive even if inspection stops
        frame_to_send = current_frame_jpg if current_frame_jpg else blank_frame
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_to_send + b'\r\n')
        time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    return Response(generate_video(), mimetype='multipart/x-mixed-replace; boundary=frame')

def main():
    print("Starting SAFEFRUIT AI Web Server...")
    # Load config initially
    load_config()
    camera.camera_index = CAMERA_INDEX
    ai_client.api_key = AI_API_KEY
    serial_controller.port = SERIAL_PORT

    # Attempt to open camera initially
    camera.open()

    # Start HW monitor
    threading.Thread(target=hardware_monitor_thread, daemon=True).start()
    
    # Run Flask
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
