import cv2
import numpy as np
from ultralytics import YOLO
from deep_sort_realtime.deepsort_tracker import DeepSort
import pandas as pd
from typing import List, Dict, Set, Tuple
import os


class VideoProcessor:
    def __init__(self, model_path: str, threshold: int):
        """Initialize the video processor with YOLO model and threshold."""
        self.model = YOLO(model_path)
        self.threshold = threshold
        self.tracker = DeepSort(
            max_age=30, n_init=3, nms_max_overlap=1.0, max_cosine_distance=0.2
        )

    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, List, bool, List]:
        """Process a single frame and return the annotated frame with detections."""
        frame = cv2.resize(frame, (1020, 500))
        h, w, _ = frame.shape
        results = self.model.predict(frame, conf=0.5, iou=0.4)

        detections = []
        pothole_bboxes = []

        for r in results:
            if r.masks is not None:
                self._process_detections(r, frame, h, w, detections, pothole_bboxes)

        pothole_bboxes = self._apply_nms(np.array(pothole_bboxes))
        is_critical = len(pothole_bboxes) > self.threshold

        tracks = self.tracker.update_tracks(detections, frame=frame)
        self._draw_tracks(frame, tracks)

        return frame, pothole_bboxes, is_critical, tracks

    def _process_detections(self, result, frame, h, w, detections, pothole_bboxes):
        """Process detection results and update frame annotations."""
        for seg, box in zip(result.masks.data.cpu().numpy(), result.boxes):
            if int(box.cls) == 0:  # Assuming 0 is pothole class
                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                pothole_bboxes.append([x1, y1, x2, y2])
                detections.append([[x1, y1, x2, y2], float(box.conf)])

                seg_resized = cv2.resize(seg, (w, h)).astype(np.uint8)
                contours, _ = cv2.findContours(
                    seg_resized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                )
                for contour in contours:
                    cv2.polylines(frame, [contour], True, (0, 255, 0), 2)

    def _apply_nms(self, boxes: np.ndarray) -> np.ndarray:
        """Apply Non-Maximum Suppression to bounding boxes."""
        if len(boxes) == 0:
            return boxes

        indices = cv2.dnn.NMSBoxes(
            boxes.tolist(), [1.0] * len(boxes), 0.5, 0.3  # Dummy confidences
        )
        return boxes[indices.flatten()]

    def _draw_tracks(self, frame: np.ndarray, tracks: List) -> Set[int]:
        """Draw tracking information on frame and return unique track IDs."""
        unique_tracks = set()
        for track in tracks:
            if track.is_confirmed():
                x1, y1, x2, y2 = map(int, track.to_ltrb())
                unique_tracks.add(track.track_id)
                cv2.putText(
                    frame,
                    f"Pothole ID: {track.track_id}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                )
        return unique_tracks
