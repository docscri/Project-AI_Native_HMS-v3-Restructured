from app import config

DATA_DIR = config.data_dir()
DB_PATH = DATA_DIR / "clinic.db"
UPLOAD_DIR = DATA_DIR / "uploads"
DATABASE_URL = config.secret("DATABASE_URL")
