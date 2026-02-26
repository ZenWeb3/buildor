# ✋ Hand Sculpt 3D

Sculpt 3D voxel art using just your hands — Minecraft meets Iron Man.

![Demo](demo.gif)

## 🎯 Features

- **Gesture-based 3D sculpting** — pinch to place cubes
- **Minecraft-style building** — cubes snap to faces of existing cubes
- **Real-time hand tracking** using MediaPipe
- **Smooth rotation & zoom** with hand gestures
- **Beautiful visuals** with bloom/glow effects
- **Live webcam PiP** — see your hands while you sculpt
- **Undo support** — remove mistakes easily

## 🎮 Controls

### Hand Gestures
| Gesture | Action |
|---------|--------|
| **Pinch** | Place cube |
| **🖐️ Open palm** | Rotate sculpture |
| **✌️ 2 fingers** | Zoom in |
| **☝️ 1 finger** | Zoom out |
| **🤟 3 fingers** | Undo last cube |
| **Fist** | Clear all |

### Keyboard
| Key | Action |
|-----|--------|
| `C` | Cycle colors |
| `Z` | Undo |
| `G` | Toggle grid |
| `R` | Reset view |

## 🚀 Quick Start

### 1. Clone & setup

```bash
git clone https://github.com/yourusername/hand-sculpt.git
cd hand-sculpt
```

### 2. Install Python dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install opencv-python mediapipe websockets
```

### 3. Start the hand tracker

```bash
python hand_tracker.py
```

This will:
- Download the hand landmark model (first run only)
- Open your webcam
- Start tracking your hands
- Run a WebSocket server on `ws://localhost:8765`

### 4. Open the frontend

```bash
cd ../frontend
python -m http.server 3000
```

Then open http://localhost:3000 in Chrome.

### 5. Start sculpting! 🎨

Pinch to place your first cube, then build outward!

## 📁 Project Structure

```
hand-sculpt/
├── backend/
│   ├── hand_tracker.py    # MediaPipe hand tracking + WebSocket server
│   └── requirements.txt   # Python dependencies
├── frontend/
│   └── index.html         # Three.js 3D canvas + controls
├── .gitignore
└── README.md
```

## 🛠 Tech Stack

- **Hand Tracking**: MediaPipe Hands (Tasks API)
- **Camera**: OpenCV
- **Communication**: WebSockets
- **3D Rendering**: Three.js
- **Effects**: Unreal Bloom post-processing

## 💡 Tips for Best Results

1. **Good lighting** — face a window or light source
2. **Plain background** — helps with hand detection
3. **Steady hand** — move deliberately for precise placement
4. **Distance** — keep hand 1-2 feet from camera

## 🎨 Ideas to Try

- Build a house
- Sculpt a character
- Create pixel art from an angle
- Make a tower
- Write your name in 3D

## 📹 Recording for Social Media

Perfect for viral content:
1. Screen record with OBS or built-in recorder
2. The webcam PiP shows your hand movements
3. Glow effects look amazing on dark backgrounds
4. Show the build process sped up

## 🔧 Troubleshooting

**Webcam not detected?**
- Make sure no other app is using the camera
- Try changing `cv2.VideoCapture(0)` to `cv2.VideoCapture(1)`

**Hand tracking laggy?**
- Improve lighting
- Reduce camera resolution in `hand_tracker.py`

**Frontend not connecting?**
- Make sure backend is running first
- Check console for WebSocket errors
- Verify you're on `localhost:3000`, not `file://`

---

Built with 🔥 by [Your Name]