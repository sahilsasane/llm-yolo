from fastapi import (
    APIRouter,
    File,
    UploadFile,
    HTTPException,
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
from services.google_drive_manager import GoogleDriveManager
from deep_sort_realtime.deepsort_tracker import DeepSort
from core.video_processor import VideoProcessor

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
async def process_video(
    process_request: QueryRequest,
):
    """Process video to detect and track potholes."""
    try:
        drive_manager = GoogleDriveManager()
        processor = VideoProcessor(
            os.path.join(Settings.MODEL_DIR, "best.pt"), process_request.threshold
        )

        video_path = os.path.join(Settings.UPLOAD_DIR, f"{process_request.file_id}.mp4")
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        output_path = os.path.join(
            Settings.OUTPUT_DIR, f"{process_request.file_id}.mp4"
        )
        out = cv2.VideoWriter(
            output_path,
            cv2.VideoWriter_fourcc(*"mp4v"),
            cap.get(cv2.CAP_PROP_FPS),
            (1020, 500),
        )

        frame_data = []
        frame_count = 0
        unique_potholes = set()
        critical_frames = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            processed_frame, pothole_bboxes, is_critical, tracks = (
                processor.process_frame(frame)
            )

            if is_critical:
                critical_frames.append(f"Frame {frame_count}")

            for track in tracks:
                if track.is_confirmed():
                    unique_potholes.add(track.track_id)

            frame_data.append(
                {
                    "frame": frame_count,
                    "potholes": len(pothole_bboxes),
                    "critical": is_critical,
                }
            )

            out.write(processed_frame)

        cap.release()
        out.release()

        # Save and upload results
        df = pd.DataFrame(frame_data)
        df.to_csv(f"outputs/{process_request.file_id}.csv", index=False)

        uploaded_files = [
            drive_manager.upload_file(f"outputs/{process_request.file_id}.csv"),
            drive_manager.upload_file(f"outputs/{process_request.file_id}.mp4"),
        ]

        return {
            "file_id": process_request.file_id,
            "response": {
                "total_potholes": len(unique_potholes),
                "critical_zones": critical_frames,
            },
            "uploaded_files": uploaded_files,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query failed: {str(e)}")
