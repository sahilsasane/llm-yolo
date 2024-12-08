from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))
    UPLOAD_DIR = "files"
    OUTPUT_DIR = "outputs"
    MODEL_NAME = "gemini-1.5-flash"


settings = Settings()
