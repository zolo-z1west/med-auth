# facial-recognition/app.py
import os, time, json, sqlite3
from typing import List
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
import numpy as np, cv2, mediapipe as mp, onnxruntime as ort

# ----------------------------- config -----------------------------
DB_PATH = "/Users/umangsharma/Desktop/med-auth/facial-recognition/db.sqlite"
MODEL_PATH = "/Users/umangsharma/Desktop/med-auth/facial-recognition/models/MobileFaceNet.onnx"
THRESHOLD = 0.4

app = FastAPI(title="Local Facial Recognition Service")

# ----------------------------- database -----------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS faces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            embedding TEXT,
            created_at REAL
        )
    """)
    conn.commit()
    conn.close()

def save_embedding(user_id: str, embedding: np.ndarray):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO faces (user_id, embedding, created_at) VALUES (?, ?, ?)",
        (user_id, json.dumps(embedding.tolist()), time.time()),
    )
    conn.commit()
    conn.close()

def load_embeddings():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, embedding FROM faces")
    rows = cur.fetchall()
    conn.close()
    return [(r[0], np.array(json.loads(r[1]), dtype=np.float32)) for r in rows]

init_db()

# ----------------------------- model + detector -----------------------------
sess = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
input_name, output_name = "input0", "output0"
mp_fd = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.25)

def bgr_from_bytes(data: bytes):
    arr = np.frombuffer(data, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)

def detect_face(img_bgr):
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    res = mp_fd.process(img_rgb)
    if not res.detections:
        return None
    d = res.detections[0].location_data.relative_bounding_box
    h, w = img_bgr.shape[:2]
    x, y = int(d.xmin * w), int(d.ymin * h)
    ww, hh = int(d.width * w), int(d.height * h)
    pad = 0.2
    x0, y0 = max(0, int(x - ww * pad)), max(0, int(y - hh * pad))
    x1, y1 = min(w, int(x + ww + ww * pad)), min(h, int(y + hh + hh * pad))
    return img_bgr[y0:y1, x0:x1]

def preprocess(face_bgr):
    img = cv2.resize(face_bgr, (112, 112))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32)
    img = (img - 127.5) / 128.0
    img = np.transpose(img, (2, 0, 1))[None, :]
    return img.astype(np.float32)

def embed(face_bgr):
    x = preprocess(face_bgr)
    out = sess.run([output_name], {input_name: x})[0]
    v = out.flatten().astype(np.float32)
    return v / (np.linalg.norm(v) + 1e-10)

# ----------------------------- API endpoints -----------------------------
@app.post("/enroll")
async def enroll(user_id: str = Form(...), images: List[UploadFile] = File(...)):
    if not user_id or not images:
        raise HTTPException(status_code=400, detail="Missing user_id or images")

    count = 0
    for img_file in images:
        try:
            data = await img_file.read()
            bgr = bgr_from_bytes(data)
            if bgr is None:
                continue
            face = detect_face(bgr)
            if face is None:
                continue
            emb = embed(face)
            save_embedding(user_id, emb)
            count += 1
        except Exception as e:
            continue

    if count == 0:
        raise HTTPException(status_code=400, detail="No valid faces detected")
    return {"status": "ok", "saved": count}

@app.post("/capture")
async def capture(file: UploadFile = File(...)):
    data = await file.read()
    open("/tmp/esp_last.jpg", "wb").write(data)
    bgr = bgr_from_bytes(data)
    if bgr is None:
        raise HTTPException(status_code=400, detail="Invalid image")

    face = detect_face(bgr)
    if face is None:
        return {"decision": "deny", "reason": "no_face"}

    emb = embed(face)
    db = load_embeddings()
    if not db:
        return {"decision": "deny", "reason": "no_enrollments"}

    best_score, best_user = -1.0, None
    for user_id, db_emb in db:
        s = float(np.dot(emb, db_emb))
        if s > best_score:
            best_score, best_user = s, user_id

    if best_score >= THRESHOLD:
        return {"decision": "allow", "user": best_user, "score": round(best_score, 3)}
    else:
        return {"decision": "deny", "score": round(best_score, 3)}

@app.get("/list")
def list_users():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT user_id, COUNT(*) FROM faces GROUP BY user_id")
    out = [{"user_id": r[0], "count": r[1]} for r in cur.fetchall()]
    conn.close()
    return {"users": out}

@app.delete("/delete/{user_id}")
def delete_user(user_id: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM faces WHERE user_id = ?", (user_id,))
    count = cur.rowcount
    conn.commit()
    conn.close()
    if count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": count, "user_id": user_id}

@app.delete("/clear")
def clear_all():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM faces")
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "All records cleared"}

# ----------------------------- main -----------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000)
