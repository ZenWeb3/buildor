import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import asyncio
import websockets
import json
import math
import urllib.request
import os
import base64
from collections import deque

# Download the hand landmarker model if not present
MODEL_PATH = "hand_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"

if not os.path.exists(MODEL_PATH):
    print("Downloading hand landmarker model...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("Model downloaded!")

# Track connected clients
clients = set()

# Frame counter for video streaming (send every N frames to reduce bandwidth)
SEND_VIDEO_EVERY = 1
frame_counter = 0

# Smoothing buffers for each hand (stores last N positions)
SMOOTHING_FRAMES = 5
hand_buffers = {
    "Left": {
        "index_tip": deque(maxlen=SMOOTHING_FRAMES),
        "thumb_tip": deque(maxlen=SMOOTHING_FRAMES),
        "palm": deque(maxlen=SMOOTHING_FRAMES),
    },
    "Right": {
        "index_tip": deque(maxlen=SMOOTHING_FRAMES),
        "thumb_tip": deque(maxlen=SMOOTHING_FRAMES),
        "palm": deque(maxlen=SMOOTHING_FRAMES),
    }
}

def smooth_position(buffer, new_pos):
    """Add new position to buffer and return smoothed average"""
    buffer.append(new_pos)
    if len(buffer) == 0:
        return new_pos
    
    avg_x = sum(p['x'] for p in buffer) / len(buffer)
    avg_y = sum(p['y'] for p in buffer) / len(buffer)
    avg_z = sum(p['z'] for p in buffer) / len(buffer)
    
    return {'x': avg_x, 'y': avg_y, 'z': avg_z}

def calculate_distance(p1, p2):
    """Calculate distance between two landmarks"""
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def detect_gestures(landmarks):
    """Detect gestures from hand landmarks with hysteresis for stability"""
    thumb_tip = landmarks[4]
    index_tip = landmarks[8]
    middle_tip = landmarks[12]
    ring_tip = landmarks[16]
    pinky_tip = landmarks[20]
    
    palm = landmarks[0]
    
    # Pinch detection with slightly larger threshold for stability
    pinch_distance = calculate_distance(thumb_tip, index_tip)
    is_pinching = pinch_distance < 0.06
    
    # Fist detection
    fingertips = [landmarks[i] for i in [8, 12, 16, 20]]
    avg_distance = sum(calculate_distance(tip, palm) for tip in fingertips) / 4
    is_fist = avg_distance < 0.13
    
    # Two finger pinch (thumb + middle)
    two_pinch_distance = calculate_distance(thumb_tip, middle_tip)
    is_two_pinching = two_pinch_distance < 0.06
    
    # Count extended fingers (finger tip farther from wrist than knuckle)
    wrist = landmarks[0]
    fingers_up = 0
    
    # Index finger - compare tip to pip (middle joint)
    index_pip = landmarks[6]
    if calculate_distance(index_tip, wrist) > calculate_distance(index_pip, wrist) + 0.02:
        fingers_up += 1
    
    # Middle finger
    middle_pip = landmarks[10]
    if calculate_distance(middle_tip, wrist) > calculate_distance(middle_pip, wrist) + 0.02:
        fingers_up += 1
    
    # Ring finger
    ring_pip = landmarks[14]
    if calculate_distance(ring_tip, wrist) > calculate_distance(ring_pip, wrist) + 0.02:
        fingers_up += 1
    
    # Pinky finger
    pinky_pip = landmarks[18]
    if calculate_distance(pinky_tip, wrist) > calculate_distance(pinky_pip, wrist) + 0.02:
        fingers_up += 1
    
    return {
        "pinch": is_pinching,
        "fist": is_fist,
        "two_pinch": is_two_pinching,
        "pinch_distance": pinch_distance,
        "fingers_up": fingers_up
    }

def get_hand_data(landmarks, handedness):
    """Extract relevant hand data with smoothing"""
    index_tip = landmarks[8]
    thumb_tip = landmarks[4]
    palm = landmarks[0]
    
    # Get raw positions
    raw_index = {'x': index_tip.x, 'y': index_tip.y, 'z': index_tip.z}
    raw_thumb = {'x': thumb_tip.x, 'y': thumb_tip.y, 'z': thumb_tip.z}
    raw_palm = {'x': palm.x, 'y': palm.y, 'z': palm.z}
    
    # Apply smoothing
    buffer = hand_buffers.get(handedness, hand_buffers["Right"])
    smoothed_index = smooth_position(buffer["index_tip"], raw_index)
    smoothed_thumb = smooth_position(buffer["thumb_tip"], raw_thumb)
    smoothed_palm = smooth_position(buffer["palm"], raw_palm)
    
    gestures = detect_gestures(landmarks)
    
    return {
        "hand": handedness,
        "index_tip": smoothed_index,
        "thumb_tip": smoothed_thumb,
        "palm": smoothed_palm,
        "gestures": gestures
    }

def draw_landmarks_on_image(frame, detection_result):
    """Draw hand landmarks on the image"""
    if detection_result.hand_landmarks:
        h, w, _ = frame.shape
        for hand_landmarks in detection_result.hand_landmarks:
            # Draw points
            for landmark in hand_landmarks:
                x = int(landmark.x * w)
                y = int(landmark.y * h)
                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)
            
            # Draw connections
            connections = [
                (0, 1), (1, 2), (2, 3), (3, 4),
                (0, 5), (5, 6), (6, 7), (7, 8),
                (0, 9), (9, 10), (10, 11), (11, 12),
                (0, 13), (13, 14), (14, 15), (15, 16),
                (0, 17), (17, 18), (18, 19), (19, 20),
                (5, 9), (9, 13), (13, 17)
            ]
            for start, end in connections:
                x1 = int(hand_landmarks[start].x * w)
                y1 = int(hand_landmarks[start].y * h)
                x2 = int(hand_landmarks[end].x * w)
                y2 = int(hand_landmarks[end].y * h)
                cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
    
    return frame

def frame_to_base64(frame, scale=0.5):
    """Convert frame to base64 JPEG for streaming to frontend"""
    # Resize for faster transfer
    small = cv2.resize(frame, (0, 0), fx=scale, fy=scale)
    # Encode as JPEG with better quality
    _, buffer = cv2.imencode('.jpg', small, [cv2.IMWRITE_JPEG_QUALITY, 80])
    # Convert to base64
    return base64.b64encode(buffer).decode('utf-8')

async def broadcast(message):
    """Send message to all connected clients"""
    if clients:
        await asyncio.gather(*[client.send(message) for client in clients])

async def handler(websocket):
    """Handle new websocket connection"""
    clients.add(websocket)
    print(f"Client connected. Total clients: {len(clients)}")
    try:
        await websocket.wait_closed()
    finally:
        clients.remove(websocket)
        print(f"Client disconnected. Total clients: {len(clients)}")

async def track_hands():
    """Main hand tracking loop with optimized settings"""
    
    # Create hand landmarker with better tracking settings
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=0.4,  # Lower = detects hands easier
        min_hand_presence_confidence=0.4,   # Lower = keeps tracking longer
        min_tracking_confidence=0.4         # Lower = smoother tracking
    )
    
    detector = vision.HandLandmarker.create_from_options(options)
    
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 60)  # Request higher FPS if available
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer for lower latency
    
    print("Hand tracking started. Press 'q' to quit.")
    print("Smoothing enabled - tracking should be smoother now!")
    
    try:
        while cap.isOpened():
            success, frame = cap.read()
            if not success:
                continue
            
            # Flip for mirror effect
            frame = cv2.flip(frame, 1)
            
            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Detect hands
            detection_result = detector.detect(mp_image)
            
            hand_data_list = []
            
            if detection_result.hand_landmarks:
                for idx, hand_landmarks in enumerate(detection_result.hand_landmarks):
                    handedness = detection_result.handedness[idx][0].category_name
                    hand_data = get_hand_data(hand_landmarks, handedness)
                    hand_data_list.append(hand_data)
                
                frame = draw_landmarks_on_image(frame, detection_result)
            else:
                # Clear buffers when no hands detected
                for hand in hand_buffers.values():
                    for buffer in hand.values():
                        buffer.clear()
            
            # Send data to clients
            if clients:
                global frame_counter
                message_data = {
                    "hands": hand_data_list,
                    "timestamp": asyncio.get_event_loop().time()
                }
                
                # Send video frame every N frames
                frame_counter += 1
                if frame_counter >= SEND_VIDEO_EVERY:
                    message_data["frame"] = frame_to_base64(frame)
                    frame_counter = 0
                
                await broadcast(json.dumps(message_data))
            
            # Display the frame
            cv2.imshow('Hand Sculpt - Tracker', frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            
            await asyncio.sleep(0.008)  # ~120 checks per second
    
    finally:
        cap.release()
        cv2.destroyAllWindows()
        detector.close()

async def main():
    """Run websocket server and hand tracking concurrently"""
    print("Starting Hand Sculpt Backend...")
    print("WebSocket server on ws://localhost:8765")
    
    async with websockets.serve(handler, "localhost", 8765):
        await track_hands()

if __name__ == "__main__":
    asyncio.run(main())