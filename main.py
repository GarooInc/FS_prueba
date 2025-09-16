from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import uuid
from dotenv import load_dotenv
import mimetypes
from pathlib import Path

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

# Directorios seguros
FILES_DIR = Path("files").resolve()
FEL_AGENTS_DIR = FILES_DIR / "fel-agents"
ITZANA_AGENTS_DIR = FILES_DIR / "itzana-agents"
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(ITZANA_AGENTS_DIR, exist_ok=True)
os.makedirs(FEL_AGENTS_DIR, exist_ok=True)

# Cargar base URL desde variable de entorno
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Tipos MIME permitidos
ALLOWED_MIME_TYPES = [
    "image/jpeg",
    "image/png",
    "application/pdf",
    "text/plain",
    "image/jpg",
    "application/xml",
    "text/xml"
]

# Helper para validar rutas y evitar path traversal
def is_safe_path(base_dir: Path, target: Path) -> bool:
    try:
        return target.resolve().is_relative_to(base_dir)
    except AttributeError:
        # Para Python < 3.9
        return str(target.resolve()).startswith(str(base_dir.resolve()))

# Middleware: bloquear bots y añadir headers de seguridad
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    user_agent = request.headers.get('user-agent', "").lower()
    blacklisted = ["curl", "wget", "httpclient", "python-requests", "scrapy"]
    if any(bot in user_agent for bot in blacklisted):
        return JSONResponse(status_code=403, content={"detail": "Bot not allowed"})

    response = await call_next(request)
    # Añadir headers de seguridad
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Sube un archivo al servidor en 'files/'.
    """
    file_path = FILES_DIR / file.filename
    if file_path.name.startswith("."):
        raise HTTPException(status_code=400, detail="Nombre de archivo no permitido")
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
    # Obtener extensión original
    _, ext = os.path.splitext(file.filename)
    new_filename = f"{uuid.uuid4()}{ext}"
    file_path = FEL_AGENTS_DIR / new_filename

    if file_path.name.startswith("."):
        raise HTTPException(status_code=400, detail="Nombre de archivo no permitido")

    with open(file_path, "wb") as f:
        f.write(await file.read())

    file_url = f"{BASE_URL}/files/fel-agents/{new_filename}"

    return {
        "message": f"Archivo subido correctamente como '{new_filename}'",
        "url": file_url
    }


@app.post("/upload/itzana-agents")
async def upload_fel_agent_file(file: UploadFile = File(...)):
    """
    Sube un archivo al servidor en 'files/itzana-agents/'.
    - Cambia el nombre a UUID
    - Devuelve la URL completa para acceder al archivo
    """
    # Obtener extensión original
    _, ext = os.path.splitext(file.filename)
    new_filename = f"{uuid.uuid4()}{ext}"
    file_path = ITZANA_AGENTS_DIR / new_filename

    if file_path.name.startswith("."):
        raise HTTPException(status_code=400, detail="Nombre de archivo no permitido")

    with open(file_path, "wb") as f:
        f.write(await file.read())

    file_url = f"{BASE_URL}/files/itzana-agents/{new_filename}"

    return {
        "message": f"Archivo subido correctamente como '{new_filename}'",
        "url": file_url
    }

@app.get("/files", response_model=List[str])
def list_files():
    """
    Lista todos los archivos en la carpeta 'files/'.
    """
    return [f.name for f in FILES_DIR.iterdir() if f.is_file()]


@app.get("/files/{subdir}/{filename}")
def get_file(subdir: str, filename: str):
    """
    Devuelve un archivo desde la carpeta especificada para visualizarlo en el navegador.
    """
    subdir_path = FILES_DIR / subdir
    file_path = subdir_path / filename

    if not is_safe_path(FILES_DIR, file_path):
        raise HTTPException(status_code=400, detail="Ruta inválida")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    if file_path.name.startswith("."):
        raise HTTPException(status_code=403, detail="Acceso denegado a archivos ocultos")

    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=403, detail="Tipo de archivo no permitido")

    return FileResponse(
        path=str(file_path),
        media_type=mime_type
    )
