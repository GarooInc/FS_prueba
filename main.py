from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import uuid
from dotenv import load_dotenv
import mimetypes

# Cargar variables de entorno
load_dotenv()

# Crear instancia de la aplicación FastAPI
app = FastAPI()

# Configurar CORS para permitir peticiones desde cualquier origen (útil para frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes (ajustar en producción)
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos HTTP
    allow_headers=["*"],  # Permitir todos los headers
)

# Definir carpeta de almacenamiento de archivos
FILES_DIR = "files"
AGENTS_DIR = os.path.join(FILES_DIR, "fel-agents")
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(AGENTS_DIR, exist_ok=True)

# Cargar base URL desde variable de entorno
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Sube un archivo al servidor en 'files/'.
    """
    file_path = os.path.join(FILES_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"message": f"Archivo '{file.filename}' subido correctamente"}


@app.post("/upload/fel-agents")
async def upload_fel_agent_file(file: UploadFile = File(...)):
    """
    Sube un archivo al servidor en 'files/fel-agents/'.
    - Cambia el nombre a UUID
    - Devuelve la URL completa para acceder al archivo
    """
    # Crear carpeta fel-agents si no existe
    os.makedirs(AGENTS_DIR, exist_ok=True)

    # Obtener extensión original
    _, ext = os.path.splitext(file.filename)
    # Generar UUID como nuevo nombre de archivo
    new_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(AGENTS_DIR, new_filename)

    # Guardar archivo
    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Construir URL de acceso
    file_url = f"{BASE_URL}/files/fel-agents/{new_filename}"

    return {
        "message": f"Archivo subido correctamente como '{new_filename}'",
        "url": file_url
    }


@app.get("/files", response_model=List[str])
def list_files():
    """
    Lista todos los archivos en la carpeta 'files/'.
    """
    return os.listdir(FILES_DIR)


@app.get("/files/{subdir}/{filename}")
def get_file(subdir: str, filename: str):
    """
    Devuelve un archivo desde la carpeta especificada para visualizarlo en el navegador.
    """
    subdir_path = os.path.join(FILES_DIR, subdir)
    file_path = os.path.join(subdir_path, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    # Detectar el tipo MIME
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"  # fallback

    return FileResponse(
        path=file_path,
        media_type=mime_type
    )