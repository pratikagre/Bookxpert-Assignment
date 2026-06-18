import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(BASE_DIR, "db")

# Ingestion & Chunking settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Model configurations
EMBEDDING_MODEL = "models/text-embedding-004"
GENERATIVE_MODEL = "gemini-2.5-flash"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DB_DIR, exist_ok=True)
