from __future__ import annotations

import os
import queue
import time
from multiprocessing.queues import Queue
from typing import Any

import cv2
import mediapipe as mp
import numpy as np


WRIST = 0
PALM_POINTS = np.array([0, 5, 9, 13, 17], dtype=np.intp)
PALM_CENTER_POINTS = np.array([5, 9, 13, 17], dtype=np.intp)
FINGERTIPS = np.array([8, 12, 16, 20], dtype=np.intp)

FINGER_JOINTS = (
    (5, 6, 7, 8),
    (9, 10, 11, 12),
    (13, 14, 15, 16),
    (17, 18, 19, 20),
)

HAND_CONNECTIONS = (
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
)

PREVIEW_COLORS = {
    "Left": (255, 190, 70),
    "Right": (90, 220, 255),
}


def _put_latest(output_queue: Queue, packet: dict[str, Any]) -> None:
    """Keep tracking latency bounded by retaining only recent packets."""
    try:
        output_queue.put_nowait(packet)
        return
    except queue.Full:
        pass

    try:
        output_queue.get_nowait()
    except queue.Empty:
        pass

    try:
        output_queue.put_nowait(packet)
    except queue.Full:
        pass


def _open_camera(camera_index: int) -> cv2.VideoCapture:
    if os.name == "nt":
        capture = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)

        if capture.isOpened():
            return capture

        capture.release()

    return cv2.VideoCapture(camera_index)


def _joint_angle(
    point_a: np.ndarray,
    point_b: np.ndarray,
    point_c: np.ndarray,
) -> float:
    vector_a = point_a - point_b
    vector_c = point_c - point_b

    denominator = float(
        np.linalg.norm(vector_a) * np.linalg.norm(vector_c)
    )

    if denominator <= 1e-8:
        return 0.0

    cosine = float(
        np.clip(
            np.dot(vector_a, vector_c) / denominator,
            -1.0,
            1.0,
        )
    )

    return float(np.degrees(np.arccos(cosine)))


def _finger_extended(
    landmarks: np.ndarray,
    joints: tuple[int, int, int, int],
) -> bool:
    mcp, pip, dip, tip = joints

    pip_angle = _joint_angle(
        landmarks[mcp, :2],
        landmarks[pip, :2],
        landmarks[dip, :2],
    )
    dip_angle = _joint_angle(
        landmarks[pip, :2],
        landmarks[dip, :2],
        landmarks[tip, :2],
    )

    wrist = landmarks[WRIST, :2]
    pip_radius = float(
        np.linalg.norm(landmarks[pip, :2] - wrist)
    )
    tip_radius = float(
        np.linalg.norm(landmarks[tip, :2] - wrist)
    )

    return (
        pip_angle >= 120.0
        and dip_angle >= 112.0
        and tip_radius >= pip_radius * 0.98
    )


def _thumb_extended(
    landmarks: np.ndarray,
    palm_center: np.ndarray,
) -> bool:
    thumb_mcp = landmarks[2, :2]
    thumb_ip = landmarks[3, :2]
    thumb_tip = landmarks[4, :2]

    angle = _joint_angle(
        thumb_mcp,
        thumb_ip,
        thumb_tip,
    )

    ip_radius = float(
        np.linalg.norm(thumb_ip - palm_center)
    )
    tip_radius = float(
        np.linalg.norm(thumb_tip - palm_center)
    )

    return angle >= 137.0 and tip_radius >= ip_radius * 1.06


def classify_hand_state(
    landmarks: np.ndarray,
) -> tuple[str, int, float]:
    """
    Return open, closed, or neutral using two independent signals.

    Joint angles determine how many fingers look extended. A normalized
    fingertip-to-palm distance provides a fallback when perspective makes the
    angles unreliable.
    """
    palm_center = landmarks[PALM_CENTER_POINTS, :2].mean(axis=0)
    palm_scale = float(
        np.linalg.norm(
            landmarks[9, :2] - landmarks[WRIST, :2]
        )
    )
    palm_scale = max(palm_scale, 1e-6)

    fingers = [
        _finger_extended(landmarks, joints)
        for joints in FINGER_JOINTS
    ]
    extended_count = sum(fingers)

    fingertip_distances = np.linalg.norm(
        landmarks[FINGERTIPS, :2] - palm_center,
        axis=1,
    )
    openness = float(
        fingertip_distances.mean() / palm_scale
    )

    # Either a clear finger count or a large/small palm-relative spread is
    # enough to classify the state. The middle band remains neutral.
    if extended_count >= 3 or openness >= 1.34:
        return "open", extended_count, openness

    if extended_count <= 1 and openness <= 1.12:
        return "closed", extended_count, openness

    return "neutral", extended_count, openness


def _draw_hand(
    frame: np.ndarray,
    landmarks: np.ndarray,
    handedness: str,
    state: str,
    palm: np.ndarray,
    openness: float,
) -> None:
    height, width = frame.shape[:2]
    color = PREVIEW_COLORS.get(handedness, (150, 240, 150))

    points = np.empty((21, 2), dtype=np.int32)
    points[:, 0] = np.clip(
        landmarks[:, 0] * width,
        0,
        width - 1,
    ).astype(np.int32)
    points[:, 1] = np.clip(
        landmarks[:, 1] * height,
        0,
        height - 1,
    ).astype(np.int32)

    for start, end in HAND_CONNECTIONS:
        cv2.line(
            frame,
            tuple(points[start]),
            tuple(points[end]),
            color,
            2,
            cv2.LINE_AA,
        )

    for index, point in enumerate(points):
        radius = 6 if index in (4, 8, 12, 16, 20) else 4

        cv2.circle(
            frame,
            tuple(point),
            radius,
            color,
            -1,
            cv2.LINE_AA,
        )

    palm_point = (
        int(np.clip(palm[0] * width, 0, width - 1)),
        int(np.clip(palm[1] * height, 0, height - 1)),
    )

    cv2.circle(
        frame,
        palm_point,
        16,
        color,
        3,
        cv2.LINE_AA,
    )

    label_position = (
        max(8, palm_point[0] - 70),
        max(28, palm_point[1] - 24),
    )

    cv2.putText(
        frame,
        f"{handedness}: {state.upper()}  {openness:.2f}",
        label_position,
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        color,
        2,
        cv2.LINE_AA,
    )


def vision_worker(
    output_queue: Queue,
    stop_event: Any,
    model_path: str,
    camera_index: int = 0,
    capture_width: int = 640,
    capture_height: int = 480,
    capture_fps: int = 30,
    inference_width: int = 448,
) -> None:
    """Track up to two hands and publish palm positions and open/closed states."""
    if not os.path.exists(model_path):
        _put_latest(
            output_queue,
            {
                "fatal": f"MediaPipe model not found: {model_path}",
                "timestamp_ns": time.perf_counter_ns(),
                "hands": [],
            },
        )
        return

    capture = _open_camera(camera_index)

    capture.set(
        cv2.CAP_PROP_FOURCC,
        cv2.VideoWriter_fourcc(*"MJPG"),
    )
    capture.set(cv2.CAP_PROP_FRAME_WIDTH, capture_width)
    capture.set(cv2.CAP_PROP_FRAME_HEIGHT, capture_height)
    capture.set(cv2.CAP_PROP_FPS, capture_fps)
    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if hasattr(cv2, "CAP_PROP_AUTOFOCUS"):
        capture.set(cv2.CAP_PROP_AUTOFOCUS, 1)

    if not capture.isOpened():
        _put_latest(
            output_queue,
            {
                "fatal": f"Unable to open camera index {camera_index}",
                "timestamp_ns": time.perf_counter_ns(),
                "hands": [],
            },
        )
        return

    actual_width = max(
        1,
        int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
    )
    actual_height = max(
        1,
        int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    )
    aspect = actual_width / actual_height
    inference_height = max(
        180,
        int(round(inference_width / aspect)),
    )

    options = mp.tasks.vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path=model_path,
        ),
        running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.56,
        min_hand_presence_confidence=0.56,
        min_tracking_confidence=0.62,
    )

    last_timestamp_ms = 0
    previous_time = time.perf_counter()
    displayed_fps = 0.0
    smoothed_palms: dict[str, np.ndarray] = {}

    try:
        with mp.tasks.vision.HandLandmarker.create_from_options(
            options
        ) as landmarker:
            while not stop_event.is_set():
                ok, frame_bgr = capture.read()

                if not ok:
                    time.sleep(0.005)
                    continue

                frame_bgr = cv2.flip(frame_bgr, 1)

                inference_frame = cv2.resize(
                    frame_bgr,
                    (inference_width, inference_height),
                    interpolation=cv2.INTER_AREA,
                )
                frame_rgb = cv2.cvtColor(
                    inference_frame,
                    cv2.COLOR_BGR2RGB,
                )
                mp_image = mp.Image(
                    image_format=mp.ImageFormat.SRGB,
                    data=frame_rgb,
                )

                timestamp_ms = (
                    time.perf_counter_ns() // 1_000_000
                )

                if timestamp_ms <= last_timestamp_ms:
                    timestamp_ms = last_timestamp_ms + 1

                last_timestamp_ms = timestamp_ms

                result = landmarker.detect_for_video(
                    mp_image,
                    timestamp_ms,
                )

                now = time.perf_counter()
                frame_duration = now - previous_time
                previous_time = now

                if frame_duration > 0:
                    instantaneous_fps = 1.0 / frame_duration
                    displayed_fps = (
                        displayed_fps * 0.90
                        + instantaneous_fps * 0.10
                    )

                published_hands: list[dict[str, Any]] = []
                used_names: set[str] = set()

                for index, detected_hand in enumerate(
                    result.hand_landmarks
                ):
                    landmarks = np.asarray(
                        [
                            (
                                landmark.x,
                                landmark.y,
                                landmark.z,
                            )
                            for landmark in detected_hand
                        ],
                        dtype=np.float32,
                    )

                    handedness = "Hand"

                    if index < len(result.handedness):
                        categories = result.handedness[index]

                        if categories:
                            category = categories[0]
                            handedness = (
                                getattr(
                                    category,
                                    "category_name",
                                    None,
                                )
                                or getattr(
                                    category,
                                    "display_name",
                                    None,
                                )
                                or "Hand"
                            )

                    handedness = str(handedness).title()

                    hand_id = handedness

                    if hand_id in used_names:
                        hand_id = f"{handedness}-{index + 1}"

                    used_names.add(hand_id)

                    (
                        state,
                        extended_count,
                        openness,
                    ) = classify_hand_state(landmarks)

                    raw_palm = landmarks[PALM_POINTS].mean(axis=0)

                    previous_palm = smoothed_palms.get(hand_id)

                    if previous_palm is None:
                        smooth_palm = raw_palm.copy()
                    else:
                        # Moderate smoothing is acceptable because cargo dragging
                        # is intentionally slower than a slicing gesture.
                        smooth_palm = (
                            previous_palm * 0.68
                            + raw_palm * 0.32
                        )

                    smoothed_palms[hand_id] = smooth_palm

                    handedness_score = 0.0

                    if index < len(result.handedness):
                        categories = result.handedness[index]

                        if categories:
                            handedness_score = float(
                                getattr(categories[0], "score", 0.0)
                            )

                    published_hands.append(
                        {
                            "id": hand_id,
                            "handedness": handedness,
                            "handedness_score": handedness_score,
                            "state": state,
                            "extended_count": extended_count,
                            "openness": openness,
                            "palm": smooth_palm.astype(
                                np.float32,
                                copy=False,
                            ),
                            "landmarks": landmarks,
                        }
                    )

                    _draw_hand(
                        frame_bgr,
                        landmarks,
                        handedness,
                        state,
                        smooth_palm,
                        openness,
                    )

                active_ids = {
                    hand["id"]
                    for hand in published_hands
                }

                for missing_id in list(smoothed_palms):
                    if missing_id not in active_ids:
                        del smoothed_palms[missing_id]

                _put_latest(
                    output_queue,
                    {
                        "fatal": None,
                        "timestamp_ns": time.perf_counter_ns(),
                        "hands": published_hands,
                        "tracking_fps": displayed_fps,
                    },
                )

                cv2.putText(
                    frame_bgr,
                    f"Hands: {len(published_hands)}/2",
                    (14, 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame_bgr,
                    f"Tracking FPS: {displayed_fps:.1f}",
                    (14, frame_bgr.shape[0] - 36),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.52,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame_bgr,
                    "Open = release | Closed = grab | Q = quit",
                    (14, frame_bgr.shape[0] - 13),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48,
                    (255, 255, 255),
                    1,
                    cv2.LINE_AA,
                )

                cv2.imshow(
                    "Cargo Panic - Two-Hand Tracking",
                    frame_bgr,
                )

                key = cv2.waitKey(1) & 0xFF

                if key in (ord("q"), 27):
                    stop_event.set()
                    break

    except Exception as error:
        _put_latest(
            output_queue,
            {
                "fatal": f"Vision worker failed: {error}",
                "timestamp_ns": time.perf_counter_ns(),
                "hands": [],
            },
        )

    finally:
        capture.release()
        cv2.destroyAllWindows()
