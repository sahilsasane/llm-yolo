import shutil
import chardet
import pandas as pd
from pathlib import Path


class FileHandler:
    @staticmethod
    def detect_encoding(file_path: str) -> str:
        with open(file_path, "rb") as f:
            result = chardet.detect(f.read())
        return result["encoding"]

    @staticmethod
    def save_upload_file(upload_file, file_path: str):
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)

    @staticmethod
    def read_dataframe(file_path: str, file_type: str) -> pd.DataFrame:
        encoding = FileHandler.detect_encoding(file_path)
        if file_type == "csv":
            return pd.read_csv(file_path, encoding=encoding)
        elif file_type == "xlsx":
            return pd.read_excel(file_path, encoding=encoding)
        raise ValueError(f"Unsupported file type: {file_type}")
