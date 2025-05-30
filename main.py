from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import List

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
os.makedirs(FILES_DIR, exist_ok=True)  # Crear carpeta si no existe


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Sube un archivo al servidor.

    - file: archivo enviado por el cliente en el cuerpo de la petición (multipart/form-data)
    - Guarda el archivo en la carpeta 'files/'
    - Devuelve un mensaje de éxito
    """
    file_path = os.path.join(FILES_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return {"message": f"Archivo '{file.filename}' subido correctamente"}


@app.get("/files", response_model=List[str])
def list_files():
    """
    Lista todos los nombres de archivos almacenados en la carpeta 'files/'.

    - Devuelve una lista de strings con los nombres de los archivos.
    """
    return os.listdir(FILES_DIR)


@app.get("/files/{filename}")
def get_file(filename: str):
    """
    Descarga un archivo específico por su nombre.

    - filename: nombre del archivo solicitado
    - Devuelve el archivo como una respuesta para descarga (con encabezado 'Content-Disposition')
    - Si el archivo no existe, devuelve un error 404
    """
    file_path = os.path.join(FILES_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='application/octet-stream',
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
