from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List
import os
import uuid
from dotenv import load_dotenv
import mimetypes
from pathlib import Path
import json
from datetime import datetime
import httpx

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
TEST_DIR = Path("test").resolve()
os.makedirs(FILES_DIR, exist_ok=True)
os.makedirs(ITZANA_AGENTS_DIR, exist_ok=True)
os.makedirs(FEL_AGENTS_DIR, exist_ok=True)
os.makedirs(TEST_DIR, exist_ok=True)

# Cargar base URL desde variable de entorno
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Variables de la API externa
API_BASE_URL = os.getenv("API_BASE_URL", "")
API_USER = os.getenv("API_USER", "")
API_PASSWORD = os.getenv("API_PASSWORD", "")

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


@app.post("/webhook")
async def webhook(request: Request):
    """
    Endpoint webhook que:
    1. Recibe un POST con body JSON (datos de Shopify)
    2. Obtiene un token de autenticación de la API
    3. Envía los datos a la API de facturación
    4. Guarda todo el proceso en un archivo txt
    """
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "request_received": None,
        "token_request": None,
        "facturar_request": None,
        "facturar_response": None,
        "error": None
    }
    
    try:
        # 1. Recibir el body JSON
        body = await request.json()
        log_data["request_received"] = body
        
        # Validar que tenemos las credenciales configuradas
        if not API_BASE_URL or not API_USER or not API_PASSWORD:
            raise HTTPException(
                status_code=500, 
                detail="Variables de entorno de la API no configuradas"
            )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 2. Obtener token de autenticación
            token_url = f"{API_BASE_URL}/api/Token"
            token_payload = {
                "usuario": API_USER,
                "clave": API_PASSWORD
            }
            
            log_data["token_request"] = {
                "url": token_url,
                "payload": {"usuario": API_USER, "clave": "***"}
            }
            
            token_response = await client.post(
                token_url,
                json=token_payload,
                headers={"Content-Type": "application/json"}
            )
            
            if token_response.status_code != 200:
                raise HTTPException(
                    status_code=token_response.status_code,
                    detail=f"Error obteniendo token: {token_response.text}"
                )
            
            token_data = token_response.json()
            access_token = token_data.get("data")
            
            if not access_token:
                raise HTTPException(
                    status_code=500,
                    detail="Token no recibido en la respuesta"
                )
            
            log_data["token_request"]["status"] = token_response.status_code
            log_data["token_request"]["success"] = True
            log_data["token_request"]["response"] = {
                "headers": dict(token_response.headers),
                "body": token_data
            }
            
            # 3. Enviar datos a /api/Facturar
            facturar_url = f"{API_BASE_URL}/api/Facturar"
            
            # Asegurarnos de que body sea un array
            payload = body if isinstance(body, list) else [body]
            
            log_data["facturar_request"] = {
                "url": facturar_url,
                "payload_count": len(payload)
            }
            
            facturar_response = await client.post(
                facturar_url,
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {access_token}"
                }
            )
            
            # Intentar parsear el response como JSON
            try:
                facturar_response_body = facturar_response.json()
            except:
                facturar_response_body = facturar_response.text
            
            log_data["facturar_response"] = {
                "status_code": facturar_response.status_code,
                "headers": dict(facturar_response.headers),
                "body": facturar_response_body,
                "raw_text": facturar_response.text
            }
            
            if facturar_response.status_code not in [200, 201]:
                log_data["error"] = f"Error en facturación: Status {facturar_response.status_code}"
        
        # 4. Guardar log completo en archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"webhook_{timestamp}_{uuid.uuid4().hex[:8]}.txt"
        file_path = TEST_DIR / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        return {
            "message": "Webhook procesado correctamente",
            "filename": filename,
            "facturar_status": log_data["facturar_response"]["status_code"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_data["error"] = str(e)
        
        # Guardar log con error
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"webhook_error_{timestamp}_{uuid.uuid4().hex[:8]}.txt"
        file_path = TEST_DIR / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        raise HTTPException(status_code=500, detail=f"Error procesando webhook: {str(e)}")
