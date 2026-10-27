"""Bat Sao: a webcam-controlled catch game built with MediaPipe Hand Landmarker."""

from __future__ import annotations

import argparse
import math
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
WINDOW = "BAT SAO | MediaPipe Hand"
ROUND_SECONDS = 60
START_LIVES = 3


@dataclass
class Star:
    x: float
    y: float
    speed: float
    radius: int


class CatchGame:
    """Game logic separated from camera capture and landmark inference."""

    def __init__(self, width: int, height: int, seed: int | None = None) -> None:
        self.width, self.height = width, height
        self.rng = np.random.default_rng(seed)
        self.paddle_x = width / 2
        self.target_x: float | None = None
        self.stars: list[Star] = []
        self.score = 0
        self.lives = START_LIVES
        self.started_at: float | None = None
        self.finished = False
        self.last_spawn = 0.0
        self.last_catch = 0.0

    def start_or_restart(self, now: float) -> None:
        self.score, self.lives = 0, START_LIVES
        self.stars.clear()
        self.started_at = now
        self.finished = False
        self.last_spawn = now
        self.last_catch = 0.0

    def remaining(self, now: float) -> int:
        if self.started_at is None:
            return ROUND_SECONDS
        return max(0, ROUND_SECONDS - int(now - self.started_at))

    def update(self, now: float, dt: float) -> None:
        if self.started_at is None or self.finished:
            return
        if self.remaining(now) == 0 or self.lives <= 0:
            self.finished = True
            return
        if self.target_x is not None:
            self.paddle_x += 0.32 * (self.target_x - self.paddle_x)
        if now - self.last_spawn >= 0.85 and len(self.stars) < 5:
            self.stars.append(
                Star(
                    x=float(self.rng.uniform(0.12, 0.88) * self.width),
                    y=90.0,
                    speed=float(self.rng.uniform(210, 300)),
                    radius=int(self.rng.integers(13, 19)),
                )
            )
            self.last_spawn = now

        paddle_y = self.height - 92
        paddle_half = 68
        remaining: list[Star] = []
        for star in self.stars:
            star.y += star.speed * dt
            caught = (
                abs(star.x - self.paddle_x) <= paddle_half + star.radius
                and paddle_y - star.radius <= star.y <= paddle_y + 14
            )
            if caught:
                if now - self.last_catch >= 0.12:
                    self.score += 10
                    self.last_catch = now
            elif star.y - star.radius > self.height:
                self.lives -= 1
            else:
                remaining.append(star)
        self.stars = remaining


def get_model(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        print("Đang tải mô hình Hand Landmarker lần đầu...")
        try:
            urllib.request.urlretrieve(MODEL_URL, path)
        except Exception as exc:
            raise RuntimeError(
                "Không tải được model. Hãy kiểm tra Internet hoặc tải file .task "
                f"theo hướng dẫn README. Chi tiết: {exc}"
            ) from exc
    if path.stat().st_size < 1_000_000:
        raise RuntimeError(f"File model không hợp lệ: {path}")
    return path


def make_landmarker(model_path: Path) -> vision.HandLandmarker:
    options = vision.HandLandmarkerOptions(
        base_options=python.BaseOptions(model_asset_path=str(model_path)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=1,
        min_hand_detection_confidence=0.5,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.HandLandmarker.create_from_options(options)


def draw_star(frame: np.ndarray, x: int, y: int, radius: int) -> None:
    points = []
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        r = radius if i % 2 == 0 else radius * 0.45
        points.append((int(x + math.cos(angle) * r), int(y + math.sin(angle) * r)))
    polygon = np.asarray(points, dtype=np.int32)
    cv2.fillPoly(frame, [polygon], (40, 220, 255))
    cv2.polylines(frame, [polygon], True, (255, 255, 255), 2)


def put_text(
    frame: np.ndarray,
    text: str,
    point: tuple[int, int],
    scale: float = 0.7,
    color: tuple[int, int, int] = (245, 248, 255),
    thickness: int = 2,
) -> None:
    cv2.putText(frame, text, point, cv2.FONT_HERSHEY_DUPLEX, scale, (15, 24, 38), thickness + 3, cv2.LINE_AA)
    cv2.putText(frame, text, point, cv2.FONT_HERSHEY_DUPLEX, scale, color, thickness, cv2.LINE_AA)


def render(
    frame: np.ndarray,
    game: CatchGame,
    now: float,
    hand_point: tuple[int, int] | None,
    fps: float,
) -> np.ndarray:
    h, w = frame.shape[:2]
    overlay = frame.copy()
    cv2.rectangle(overlay, (18, 18), (w - 18, h - 18), (13, 25, 42), -1)
    frame = cv2.addWeighted(overlay, 0.43, frame, 0.57, 0)
    cv2.rectangle(frame, (18, 18), (w - 18, h - 18), (90, 190, 255), 2)

    for star in game.stars:
        draw_star(frame, int(star.x), int(star.y), star.radius)
    paddle_y = h - 92
    px = int(np.clip(game.paddle_x, 88, w - 88))
    cv2.rectangle(frame, (px - 68, paddle_y), (px + 68, paddle_y + 20), (55, 210, 170), -1, cv2.LINE_AA)
    cv2.ellipse(frame, (px, paddle_y), (68, 11), 0, 180, 360, (145, 255, 220), 4, cv2.LINE_AA)
    if hand_point:
        cv2.circle(frame, hand_point, 10, (255, 190, 70), -1, cv2.LINE_AA)
        cv2.circle(frame, hand_point, 16, (255, 255, 255), 2, cv2.LINE_AA)

    put_text(frame, f"DIEM: {game.score}", (42, 58), 0.72, (120, 245, 208))
    put_text(frame, f"MANG: {game.lives}", (w // 2 - 68, 58), 0.72, (255, 180, 155))
    put_text(frame, f"THOI GIAN: {game.remaining(now):02d}s", (w - 260, 58), 0.66)
    put_text(frame, f"FPS {fps:.0f}", (w - 115, h - 35), 0.45, (210, 220, 235), 1)
    if hand_point is None and game.started_at is not None and not game.finished:
        put_text(frame, "DUA NGON TRO VAO KHUNG HINH", (w // 2 - 250, 105), 0.58, (255, 210, 120))

    if game.started_at is None:
        put_text(frame, "BAT SAO", (w // 2 - 100, h // 2 - 28), 1.25, (120, 245, 208), 3)
        put_text(frame, "Nhan SPACE de bat dau | Dua ngon tro sang trai/phai de hong ro", (w // 2 - 325, h // 2 + 25), 0.53)
    elif game.finished:
        put_text(frame, "HET LUOT!", (w // 2 - 108, h // 2 - 30), 1.05, (255, 190, 120), 3)
        put_text(frame, f"Tong diem: {game.score}   |   Nhan R de choi lai", (w // 2 - 195, h // 2 + 24), 0.62)
    else:
        put_text(frame, "SPACE: tam dung   R: choi lai   Q/ESC: thoat", (32, h - 32), 0.48)
    return frame


def run(camera_index: int, model_path: Path) -> None:
    model_path = get_model(model_path)
    camera = cv2.VideoCapture(camera_index)
    if not camera.isOpened():
        raise RuntimeError(f"Không mở được camera số {camera_index}. Hãy thử --camera 1 hoặc kiểm tra quyền camera.")
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    with make_landmarker(model_path) as landmarker:
        game: CatchGame | None = None
        last_timestamp_ms = 0
        previous = time.perf_counter()
        fps = 0.0
        paused = False
        paused_at: float | None = None
        try:
            while True:
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError("Không đọc được khung hình từ camera.")
                frame = cv2.flip(frame, 1)
                h, w = frame.shape[:2]
                if game is None or (game.width, game.height) != (w, h):
                    game = CatchGame(w, h)

                now = time.perf_counter()
                dt = min(now - previous, 0.05)
                previous = now
                fps = 0.9 * fps + 0.1 * (1.0 / max(dt, 1e-6))

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                timestamp_ms = max(last_timestamp_ms + 1, int(now * 1000))
                last_timestamp_ms = timestamp_ms
                result = landmarker.detect_for_video(mp_image, timestamp_ms)
                hand_point = None
                if result.hand_landmarks:
                    index_tip = result.hand_landmarks[0][8]
                    hx = int(np.clip(index_tip.x, 0, 1) * w)
                    hy = int(np.clip(index_tip.y, 0, 1) * h)
                    hand_point = (hx, hy)
                    game.target_x = hx
                else:
                    game.target_x = None

                if not paused:
                    game.update(now, dt)
                cv2.imshow(WINDOW, render(frame, game, now, hand_point, fps))
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == 32:
                    if game.started_at is None or game.finished:
                        game.start_or_restart(now)
                        paused = False
                        paused_at = None
                    elif paused:
                        if paused_at is not None:
                            game.started_at += now - paused_at
                        paused = False
                        paused_at = None
                    else:
                        paused = True
                        paused_at = now
                if key == ord("r"):
                    game.start_or_restart(now)
                    paused = False
                    paused_at = None
        finally:
            camera.release()
            cv2.destroyAllWindows()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bắt sao bằng đầu ngón trỏ và MediaPipe Hands")
    parser.add_argument("--camera", type=int, default=0, help="Chỉ số webcam (mặc định: 0)")
    parser.add_argument("--model", type=Path, default=Path("models/hand_landmarker.task"), help="Đường dẫn model .task")
    args = parser.parse_args()
    try:
        run(args.camera, args.model)
    except Exception as exc:
        print(f"Lỗi: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
