from fastapi import (
    APIRouter,
    File,
    UploadFile,
    WebSocket,
    HTTPException,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
import pandas as pd
from uuid import uuid4
import os
from config.settings import Settings
from schemas.requests import QueryRequest
import numpy as np
from ultralytics import YOLO
import cv2
from utils.file_handler import GoogleDriveManager
from deep_sort_realtime.deepsort_tracker import DeepSort

router = APIRouter()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_id = str(uuid4())
        file_path = os.path.join(Settings.UPLOAD_DIR, f"{file_id}.mp4")

        os.makedirs(Settings.UPLOAD_DIR, exist_ok=True)
        os.makedirs(Settings.OUTPUT_DIR, exist_ok=True)
        with open(file_path, "wb") as f:
            f.write(file.file.read())

        return {"file_id": file_id, "filename": file.filename}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to upload file: {str(e)}")


@router.post("/process")
async def process_video(process_request: QueryRequest):
    try:
        manager = GoogleDriveManager()
        file_id = process_request.file_id
        threshold = process_request.threshold
        model = YOLO(os.path.join(Settings.MODEL_DIR, "best.pt"))
        input_video_path = os.path.join(Settings.UPLOAD_DIR, f"{file_id}.mp4")
        if not os.path.exists(input_video_path):
            raise FileNotFoundError(f"Video file '{input_video_path}' does not exist.")

        # Define video capture and output
        cap = cv2.VideoCapture(input_video_path)
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(
            os.path.join(Settings.OUTPUT_DIR, f"{file_id}.mp4"),
            fourcc,
            cap.get(cv2.CAP_PROP_FPS),
            (1020, 500),
        )

        # Initialize DeepSORT tracker
        tracker = DeepSort(
            max_age=30, n_init=3, nms_max_overlap=1.0, max_cosine_distance=0.2
        )

        frame_data = []  # To store JSON information
        frame_count = 0
        unique_potholes = set()  # To store unique pothole IDs across frames
        critical_frames = []

        while True:
            critical = False
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            frame = cv2.resize(frame, (1020, 500))
            h, w, _ = frame.shape
            results = model.predict(frame, conf=0.5, iou=0.4)

            detections = []  # List to store detections in correct format for DeepSORT

            pothole_bboxes = []
            for r in results:
                boxes = r.boxes
                masks = r.masks  # Get segmentation masks if available

                if masks is not None:
                    masks = masks.data.cpu().numpy()
                    for seg, box in zip(masks, boxes):
                        cls = int(box.cls)
                        score = float(box.conf)

                        # Assuming "pothole" corresponds to a specific class ID (e.g., 0)
                        if cls == 0:
                            # Get coordinates and convert to integers
                            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                            pothole_bboxes.append([x1, y1, x2, y2])

                            # Format detection for DeepSORT: [[x1, y1, x2, y2], confidence_score]
                            detections.append([[x1, y1, x2, y2], score])

                            # Resize mask to frame size and find contours
                            seg_resized = cv2.resize(seg, (w, h)).astype(np.uint8)
                            contours, _ = cv2.findContours(
                                seg_resized, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
                            )

                            # Draw polygons (contours) on the frame
                            for contour in contours:
                                cv2.polylines(
                                    frame,
                                    [contour],
                                    isClosed=True,
                                    color=(0, 255, 0),
                                    thickness=2,
                                )
            pothole_bboxes = np.array(pothole_bboxes)
            if len(pothole_bboxes) > 0:
                indices = cv2.dnn.NMSBoxes(
                    pothole_bboxes.tolist(),  # Convert to list
                    [score for _ in pothole_bboxes],  # Dummy confidences for NMS
                    score_threshold=0.5,
                    nms_threshold=0.3,
                )
                pothole_bboxes = pothole_bboxes[indices.flatten()]

            if len(pothole_bboxes) > threshold:
                critical = True
                critical_frames.append(f"Frame {frame_count}")

            # Update DeepSORT tracker with detections
            tracks = tracker.update_tracks(detections, frame=frame)

            for track in tracks:
                if not track.is_confirmed():  # Skip unconfirmed tracks
                    continue

                track_id = track.track_id
                ltrb = track.to_ltrb()  # Get bounding box in LTRB format

                # Convert to integers for drawing
                x1, y1, x2, y2 = map(int, ltrb)

                # Check if this pothole ID is already counted
                if track_id not in unique_potholes:
                    unique_potholes.add(track_id)
                cv2.putText(
                    frame,
                    f"Pothole ID: {track_id}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    1,
                )

            frame_data.append(
                {
                    "frame": frame_count,
                    "potholes": len(pothole_bboxes),
                    "critical": critical,
                }
            )
            out.write(frame)
        cap.release()
        out.release()
        df = pd.DataFrame(frame_data, index=None)
        df.to_csv(f"outputs/{file_id}.csv", index=False)
        uploaded_file = []
        df_file = manager.upload_file(f"outputs/{file_id}.csv")
        video_file = manager.upload_file(f"outputs/{file_id}.mp4")
        uploaded_file.append(df_file)
        uploaded_file.append(video_file)
        # os.remove(f"outputs/{file_id}_annotated.mp4")
        total_potholes = len(unique_potholes)
        response = {
            "total_potholes": total_potholes,
            "critical_zones": critical_frames,
        }

        return {
            "file_id": file_id,
            "response": response,
            "uploaded_file": uploaded_file,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {str(e)}")


@router.get("/download/{file_id}")
async def download_video(file_id: str):
    try:
        output_video_path = os.path.join(Settings.OUTPUT_DIR, f"{file_id}.mp4")

        # Check if the file exists
        if not os.path.exists(output_video_path):
            raise FileNotFoundError(f"File '{file_id}.mp4' not found.")

        # Return the file as a response
        return FileResponse(
            output_video_path,
            headers={"Content-Disposition": f"attachment; filename={file_id}.mp4"},
            media_type="video/mp4",
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"File download failed: {str(e)}")
