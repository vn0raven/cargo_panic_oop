from __future__ import annotations

import math
import os
import platform
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


MODEL_FILENAME = "hand_landmarker.task"


@dataclass(frozen=True, slots=True)
class HandSnapshot:
    detected: bool = False
    x: float = 0.5
    y: float = 0.5
    closed: bool = False
    open_hand: bool = False
    gesture: str = "NONE"
    handedness: str = "Hand"
    fps: float = 0.0
    message: str = "Webcam not started"
    backend: str = ""


def hand_model_path(explicit_path: str | os.PathLike[str] | None = None) -> Path:
    """Resolve the MediaPipe hand model in source and PyInstaller builds."""
    if explicit_path:
        return Path(explicit_path).expanduser().resolve()
    configured = os.environ.get("CARGO_PANIC_HAND_MODEL")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parent / "assets" / MODEL_FILENAME


def _point(landmark: Any) -> tuple[float, float]:
    return float(landmark.x), float(landmark.y)


def _mean_point(landmarks: Sequence[Any], indices: Sequence[int]) -> tuple[float, float]:
    points = [_point(landmarks[index]) for index in indices]
    return (
        sum(point[0] for point in points) / len(points),
        sum(point[1] for point in points) / len(points),
    )


def palm_cursor(landmarks: Sequence[Any]) -> tuple[float, float]:
    """Use palm landmarks for a cursor that does not jump when fingers close."""
    return _mean_point(landmarks, (0, 5, 9, 13, 17))


def classify_hand_pose(landmarks: Sequence[Any]) -> str:
    """Classify OPEN, CLOSED, or NEUTRAL using orientation-independent distances."""
    if len(landmarks) < 21:
        return "NEUTRAL"

    wrist = _point(landmarks[0])
    palm = palm_cursor(landmarks)
    fingers = (
        (5, 6, 8),
        (9, 10, 12),
        (13, 14, 16),
        (17, 18, 20),
    )
    extended = 0
    curled = 0
    for mcp_index, pip_index, tip_index in fingers:
        mcp = _point(landmarks[mcp_index])
        pip = _point(landmarks[pip_index])
        tip = _point(landmarks[tip_index])

        tip_wrist = math.dist(tip, wrist)
        pip_wrist = max(1e-6, math.dist(pip, wrist))
        tip_palm = math.dist(tip, palm)
        pip_palm = max(1e-6, math.dist(pip, palm))
        mcp_palm = max(1e-6, math.dist(mcp, palm))

        if tip_wrist > pip_wrist * 1.12 and tip_palm > max(pip_palm * 1.08, mcp_palm * 1.35):
            extended += 1
        elif tip_wrist < pip_wrist * 1.04 or tip_palm < pip_palm * 1.02:
            curled += 1

    if curled >= 3:
        return "CLOSED"
    if extended >= 3:
        return "OPEN"
    return "NEUTRAL"


class WebcamHandInput:
    """MediaPipe/OpenCV hand input with current Tasks API and legacy fallback."""

    def __init__(
        self,
        camera_index: int = 0,
        model_path: str | os.PathLike[str] | None = None,
    ) -> None:
        self.camera_index = camera_index
        self.model_path = hand_model_path(model_path)
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
        self._thread = threading.Thread(
            target=self._run,
            name="cargo-panic-webcam",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._release_capture()
        self.available = False

    def snapshot(self) -> HandSnapshot:
        with self._lock:
            return self._snapshot

    def _publish(self, snapshot: HandSnapshot) -> None:
        with self._lock:
            self._snapshot = snapshot

    def _release_capture(self) -> None:
        if self._capture is not None:
            try:
                self._capture.release()
            except Exception:
                pass
        self._capture = None

    def _open_capture(self, cv2: Any) -> tuple[Any | None, str]:
        candidates: list[tuple[int | None, str]] = []
        if platform.system() == "Windows":
            if hasattr(cv2, "CAP_DSHOW"):
                candidates.append((cv2.CAP_DSHOW, "DirectShow"))
            if hasattr(cv2, "CAP_MSMF"):
                candidates.append((cv2.CAP_MSMF, "Media Foundation"))
        candidates.append((None, "Default"))

        for backend, label in candidates:
            capture = (
                cv2.VideoCapture(self.camera_index, backend)
                if backend is not None
                else cv2.VideoCapture(self.camera_index)
            )
            if not capture.isOpened():
                capture.release()
                continue
            capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            capture.set(cv2.CAP_PROP_FPS, 30)
            if hasattr(cv2, "CAP_PROP_BUFFERSIZE"):
                capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            # Some Windows cameras report opened before their first usable frame.
            for _ in range(12):
                ok, _frame = capture.read()
                if ok:
                    return capture, label
                time.sleep(0.04)
            capture.release()
        return None, ""

    def _create_detector(self, mp: Any) -> tuple[Any, str]:
        tasks = getattr(mp, "tasks", None)
        vision = getattr(tasks, "vision", None) if tasks is not None else None
        if vision is not None and hasattr(vision, "HandLandmarker") and self.model_path.is_file():
            options = vision.HandLandmarkerOptions(
                base_options=tasks.BaseOptions(model_asset_path=str(self.model_path)),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=1,
                min_hand_detection_confidence=0.55,
                min_hand_presence_confidence=0.50,
                min_tracking_confidence=0.50,
            )
            return vision.HandLandmarker.create_from_options(options), "tasks"

        solutions = getattr(mp, "solutions", None)
        if solutions is not None and hasattr(solutions, "hands"):
            detector = solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=1,
                min_detection_confidence=0.55,
                min_tracking_confidence=0.55,
            )
            return detector, "legacy"

        if vision is not None and hasattr(vision, "HandLandmarker"):
            raise FileNotFoundError(
                f"Missing {MODEL_FILENAME}. Run START_GAME.bat or BUILD_EXE.bat first."
            )
        raise RuntimeError("Installed MediaPipe has no Hand Landmarker API")

    @staticmethod
    def _detect(detector: Any, api: str, mp: Any, rgb: Any, timestamp_ms: int) -> tuple[Sequence[Any] | None, str]:
        if api == "tasks":
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = detector.detect_for_video(image, timestamp_ms)
            if not result.hand_landmarks:
                return None, "Hand"
            handedness = "Hand"
            if result.handedness and result.handedness[0]:
                category = result.handedness[0][0]
                handedness = (
                    getattr(category, "category_name", None)
                    or getattr(category, "display_name", None)
                    or "Hand"
                )
            return result.hand_landmarks[0], handedness

        result = detector.process(rgb)
        if not result.multi_hand_landmarks:
            return None, "Hand"
        handedness = "Hand"
        if result.multi_handedness:
            handedness = result.multi_handedness[0].classification[0].label
        return result.multi_hand_landmarks[0].landmark, handedness

    def _run(self) -> None:
        detector = None
        try:
            try:
                import cv2  # type: ignore
                import mediapipe as mp  # type: ignore
            except Exception as exc:
                self._publish(
                    HandSnapshot(
                        message=f"Webcam packages unavailable ({type(exc).__name__}) — mouse active",
                    )
                )
                return

            capture, capture_backend = self._open_capture(cv2)
            self._capture = capture
            if capture is None:
                self._publish(
                    HandSnapshot(
                        message=f"Camera {self.camera_index} unavailable — try --camera 1",
                    )
                )
                return

            detector, detector_api = self._create_detector(mp)
            self.available = True
            started = time.monotonic()
            last_frame_time = started
            fps = 0.0

            while not self._stop.is_set():
                ok, frame = capture.read()
                if not ok:
                    self._publish(
                        HandSnapshot(
                            message="Camera frame lost — mouse fallback active",
                            backend=capture_backend,
                        )
                    )
                    time.sleep(0.05)
                    continue

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp_ms = int((time.monotonic() - started) * 1000)
                landmarks, handedness = self._detect(detector, detector_api, mp, rgb, timestamp_ms)

                now = time.monotonic()
                frame_dt = max(1e-6, now - last_frame_time)
                last_frame_time = now
                measured_fps = 1.0 / frame_dt
                fps = measured_fps if fps == 0.0 else fps * 0.85 + measured_fps * 0.15

                if landmarks is None:
                    self._publish(
                        HandSnapshot(
                            detected=False,
                            fps=fps,
                            message="Show one hand inside the camera frame",
                            backend=capture_backend,
                        )
                    )
                    continue

                x, y = palm_cursor(landmarks)
                gesture = classify_hand_pose(landmarks)
                self._publish(
                    HandSnapshot(
                        detected=True,
                        x=min(max(x, 0.0), 1.0),
                        y=min(max(y, 0.0), 1.0),
                        closed=gesture == "CLOSED",
                        open_hand=gesture == "OPEN",
                        gesture=gesture,
                        handedness=handedness,
                        fps=fps,
                        message=f"{gesture.title()} hand · {fps:.0f} FPS · {capture_backend}",
                        backend=capture_backend,
                    )
                )
        except FileNotFoundError as exc:
            self._publish(HandSnapshot(message=str(exc)))
        except Exception as exc:
            self._publish(
                HandSnapshot(
                    message=f"Webcam error: {type(exc).__name__}: {exc}",
                )
            )
        finally:
            if detector is not None:
                try:
                    detector.close()
                except Exception:
                    pass
            self._release_capture()
            self.available = False
