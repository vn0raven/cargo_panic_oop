from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HandSnapshot:
    detected: bool = False
    x: float = 0.5
    y: float = 0.5
    closed: bool = False
    handedness: str = "Hand"
    fps: float = 0.0
    message: str = "Webcam not started"


class WebcamHandInput:
    """Optional MediaPipe/OpenCV hand input.

    The game imports webcam dependencies lazily. If they are absent or the camera
    cannot be opened, the UI remains usable with mouse input and exposes a clear
    fallback message instead of crashing.
    """

    def __init__(self, camera_index: int = 0) -> None:
        self.camera_index = camera_index
        self._lock = threading.Lock()
        self._snapshot = HandSnapshot(message="Starting camera…")
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._capture = None
        self.available = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="cargo-panic-webcam", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._capture is not None:
            try:
                self._capture.release()
            except Exception:
                pass
        self._capture = None
        self.available = False

    def snapshot(self) -> HandSnapshot:
        with self._lock:
            return self._snapshot

    def _publish(self, snapshot: HandSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot

    def _run(self) -> None:
        try:
            import cv2  # type: ignore
            import mediapipe as mp  # type: ignore
        except Exception:
            self._publish(
                HandSnapshot(
                    message="Webcam packages missing — mouse fallback active",
                )
            )
            return

        capture = cv2.VideoCapture(self.camera_index)
        self._capture = capture
        if not capture.isOpened():
            self._publish(HandSnapshot(message="Camera unavailable — mouse fallback active"))
            return

        try:
            hands_module = mp.solutions.hands
        except Exception:
            self._publish(
                HandSnapshot(message="MediaPipe Hands unavailable — mouse fallback active")
            )
            capture.release()
            return

        self.available = True
        last_frame_time = time.monotonic()
        fps = 0.0
        with hands_module.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.55,
            min_tracking_confidence=0.55,
        ) as hands:
            while not self._stop.is_set():
                ok, frame = capture.read()
                if not ok:
                    self._publish(HandSnapshot(message="Camera frame lost — mouse fallback active"))
                    time.sleep(0.05)
                    continue

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = hands.process(rgb)
                now = time.monotonic()
                frame_dt = max(1e-6, now - last_frame_time)
                last_frame_time = now
                fps = fps * 0.85 + (1.0 / frame_dt) * 0.15

                if not result.multi_hand_landmarks:
                    self._publish(
                        HandSnapshot(
                            detected=False,
                            fps=fps,
                            message="Show one hand inside the camera frame",
                        )
                    )
                    continue

                landmarks = result.multi_hand_landmarks[0].landmark
                index_tip = landmarks[8]
                wrist = landmarks[0]
                palm = landmarks[9]
                fingertip_indices = (8, 12, 16, 20)
                palm_scale = max(
                    0.03,
                    math.dist((wrist.x, wrist.y), (palm.x, palm.y)),
                )
                folded = 0
                for fingertip_index in fingertip_indices:
                    fingertip = landmarks[fingertip_index]
                    distance = math.dist((fingertip.x, fingertip.y), (palm.x, palm.y))
                    if distance < palm_scale * 1.55:
                        folded += 1
                closed = folded >= 3

                handedness = "Hand"
                if result.multi_handedness:
                    handedness = result.multi_handedness[0].classification[0].label
                self._publish(
                    HandSnapshot(
                        detected=True,
                        x=min(max(index_tip.x, 0.0), 1.0),
                        y=min(max(index_tip.y, 0.0), 1.0),
                        closed=closed,
                        handedness=handedness,
                        fps=fps,
                        message="Closed hand grabs · open hand releases",
                    )
                )

        capture.release()
        self.available = False
