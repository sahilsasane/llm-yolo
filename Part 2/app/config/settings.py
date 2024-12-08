from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    UPLOAD_DIR = "files"
    OUTPUT_DIR = "outputs"
    MODEL_DIR = "models"
    CREDENTIALS_DIR = "utils"


settings = Settings()
