# Documentación Completa: Endpoint Webhook de Facturación Shopify

## 📋 Índice
1. [Descripción General](#descripción-general)
2. [Requisitos del Sistema](#requisitos-del-sistema)
3. [Instalación y Configuración](#instalación-y-configuración)
4. [Estructura del Proyecto](#estructura-del-proyecto)
5. [Lógica de Negocio](#lógica-de-negocio)
6. [Código Completo](#código-completo)
7. [Variables de Entorno](#variables-de-entorno)
8. [Endpoint /webhook](#endpoint-webhook)
9. [Ejemplos de Uso](#ejemplos-de-uso)
10. [Sistema de Logs](#sistema-de-logs)
11. [Manejo de Errores](#manejo-de-errores)
12. [Testing](#testing)
13. [Deployment](#deployment)
14. [Troubleshooting](#troubleshooting)

---

## 📖 Descripción General

Este endpoint webhook recibe órdenes de Shopify, detecta si son pickups en la ubicación CAES (Carretera A El Salvador), agrega automáticamente un tag si aplica, y envía los datos a una API externa de facturación.

### Flujo del Sistema

```
Shopify Order → Webhook Endpoint → Detección CAES → Obtener Token → 
Enviar a API Facturación → Guardar Logs → Responder
```

### Características Principales

- ✅ Recepción de webhooks de Shopify
- ✅ Detección automática de Pickup CAES
- ✅ Agregado inteligente de tags (solo si no existe)
- ✅ Autenticación JWT con API externa
- ✅ Sistema completo de logging
- ✅ Manejo robusto de errores
- ✅ Validación de integridad de datos

---

## 🖥️ Requisitos del Sistema

### Software Requerido

```
Python: 3.9+
FastAPI: 0.104.0+
uvicorn: 0.24.0+
httpx: 0.28.0+
python-dotenv: 1.0.0+
```

### Hardware Mínimo

- **CPU**: 1 core
- **RAM**: 512 MB
- **Disco**: 1 GB (para logs)
- **Red**: Conexión estable a internet

---

## 🚀 Instalación y Configuración

### 1. Crear Proyecto

```bash
# Crear directorio del proyecto
mkdir webhook-shopify
cd webhook-shopify

# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

### 2. Instalar Dependencias

Crear `requirements.txt`:

```txt
fastapi
uvicorn
python-multipart
aiofiles
python-dotenv
httpx
```

Instalar:

```bash
pip install -r requirements.txt
```

### 3. Estructura de Directorios

```
webhook-shopify/
├── .env                    # Variables de entorno
├── main.py                 # Código principal
├── requirements.txt        # Dependencias
├── test/                   # Carpeta para logs (se crea automáticamente)
└── .gitignore             # Archivos a ignorar
```

Crear `.gitignore`:

```
.venv/
__pycache__/
*.pyc
.env
test/*.txt
files/
```

---

## 📁 Estructura del Proyecto

### Organización de Carpetas

El sistema crea automáticamente las siguientes carpetas:

```
├── test/                   # Logs de webhooks
│   ├── webhook_20260311_150423_a1b2c3d4.txt
│   └── webhook_error_20260311_160530_e5f6g7h8.txt
├── files/                  # Archivos subidos (opcional)
│   ├── fel-agents/
│   └── itzana-agents/
```

---

## 🧠 Lógica de Negocio

### Detección de Pickup CAES

Una orden se considera **Pickup CAES** cuando cumple **TODAS** estas condiciones:

#### Condición 1: shipping_address es null

```json
"shipping_address": null
```

#### Condición 2: shipping_lines existe y no está vacío

```json
"shipping_lines": [
  {
    ...
  }
]
```

#### Condición 3: Precio de envío es "0.00"

```json
"shipping_lines": [
  {
    "price": "0.00"
  }
]
```

#### Condición 4: Code y Title específicos

```json
"shipping_lines": [
  {
    "code": "Injerto Carretera A El Salvador",
    "title": "Injerto Carretera A El Salvador"
  }
]
```

### Reglas de Agregado de Tag

| Condición | Tag "CAES" Presente | Acción |
|-----------|---------------------|--------|
| Es Pickup CAES | ❌ No | ✅ Agregar tag |
| Es Pickup CAES | ✅ Sí | ⏭️ No modificar |
| NO es Pickup CAES | ❌ No | ⏭️ No modificar |
| NO es Pickup CAES | ✅ Sí | ⏭️ No modificar |

**Nota**: Puede haber órdenes con tag "CAES" que NO sean Pickup (ejemplo: delivery a dirección en CAES agregado por otra automatización).

---

## 💻 Código Completo

### main.py

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import uuid
from dotenv import load_dotenv
from pathlib import Path
import json
from datetime import datetime
import httpx
import copy

# Cargar variables de entorno
load_dotenv()

# Crear instancia de la aplicación FastAPI
app = FastAPI(
    title="Shopify Webhook API",
    description="API para procesar webhooks de Shopify y enviar a facturación",
    version="1.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ajustar en producción
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directorios
TEST_DIR = Path("test").resolve()
os.makedirs(TEST_DIR, exist_ok=True)

# Variables de la API externa
API_BASE_URL = os.getenv("API_BASE_URL", "")
API_USER = os.getenv("API_USER", "")
API_PASSWORD = os.getenv("API_PASSWORD", "")


# ========== FUNCIONES AUXILIARES ==========

def is_pickup_caes(order: dict) -> bool:
    """
    Detecta si una orden es Pickup CAES según las reglas:
    - shipping_address es null
    - shipping_lines existe y tiene al menos 1 elemento
    - shipping_lines[0].price es "0.00"
    - code y title son "Injerto Carretera A El Salvador"
    
    Args:
        order (dict): Orden de Shopify
        
    Returns:
        bool: True si es Pickup CAES, False en caso contrario
    """
    shipping_address = order.get("shipping_address")
    shipping_lines = order.get("shipping_lines") or []

    # Verificar que no haya dirección de envío
    if shipping_address is not None:
        return False
    
    # Verificar que existan líneas de envío
    if not shipping_lines:
        return False

    sl = shipping_lines[0]

    # Verificar todas las condiciones
    return (
        str(sl.get("price")) == "0.00"
        and sl.get("code") == "Injerto Carretera A El Salvador"
        and sl.get("title") == "Injerto Carretera A El Salvador"
    )


def add_caes_tag(order: dict) -> dict:
    """
    Agrega el tag "CAES" a una orden si no lo tiene ya.
    Shopify tags es un string tipo "tag1, tag2".
    
    Args:
        order (dict): Orden de Shopify
        
    Returns:
        dict: Orden con el tag "CAES" agregado
    """
    tags_str = (order.get("tags") or "").strip()

    # Convertir a lista limpia
    tags = [t.strip() for t in tags_str.split(",") if t.strip()]

    # Evitar duplicados
    if "CAES" not in tags:
        tags.append("CAES")

    order["tags"] = ", ".join(tags)
    return order


# ========== ENDPOINT WEBHOOK ==========

@app.post("/webhook")
async def webhook(request: Request):
    """
    Endpoint webhook que:
    1. Recibe un POST con body JSON (datos de Shopify)
    2. Detecta Pickup CAES y agrega tag "CAES" SOLO si no existe ya
    3. Obtiene un token de autenticación de la API
    4. Envía los datos (con tag CAES agregado si aplicó) a la API de facturación
    5. Guarda todo el proceso en un archivo txt
    
    IMPORTANTE: Si la orden YA trae el tag "CAES", NO se modifica nada.
    Solo se agrega el tag si es Pickup CAES y aún no lo tiene.
    """
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "request_received": None,
        "pickup_caes_detected": False,
        "caes_tag_already_present": False,
        "caes_tag_added": False,
        "original_tags": "",
        "final_tags": "",
        "token_request": None,
        "facturar_request": None,
        "payload_sent_to_api": None,
        "facturar_response": None,
        "error": None
    }
    
    try:
        # ===== PASO 1: Recibir el body JSON =====
        body = await request.json()
        log_data["request_received"] = copy.deepcopy(body)
        log_data["original_tags"] = body.get("tags", "")
        
        # ===== PASO 2: Detectar y procesar Pickup CAES =====
        if is_pickup_caes(body):
            log_data["pickup_caes_detected"] = True
            original_tags = body.get("tags", "")
            
            # Verificar si ya tiene el tag CAES
            existing_tags = [t.strip() for t in original_tags.split(",") if t.strip()]
            if "CAES" in existing_tags:
                log_data["caes_tag_already_present"] = True
                log_data["caes_tag_added"] = False
                log_data["final_tags"] = original_tags
            else:
                # Solo agregar si no existe
                body = add_caes_tag(body)
                log_data["caes_tag_added"] = True
                log_data["final_tags"] = body.get("tags", "")
        
        # ===== PASO 3: Validar credenciales =====
        if not API_BASE_URL or not API_USER or not API_PASSWORD:
            raise HTTPException(
                status_code=500, 
                detail="Variables de entorno de la API no configuradas"
            )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # ===== PASO 4: Obtener token de autenticación =====
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
            
            # ===== PASO 5: Enviar datos a /api/Facturar =====
            facturar_url = f"{API_BASE_URL}/api/Facturar"
            
            # Asegurarnos de que body sea un array
            payload = body if isinstance(body, list) else [body]
            
            # Guardar el payload EXACTO que se envía (para verificación)
            log_data["payload_sent_to_api"] = copy.deepcopy(payload)
            
            log_data["facturar_request"] = {
                "url": facturar_url,
                "payload_count": len(payload),
                "note": "Payload includes CAES tag if detected"
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
        
        # ===== PASO 6: Guardar log completo en archivo =====
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"webhook_{timestamp}_{uuid.uuid4().hex[:8]}.txt"
        file_path = TEST_DIR / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)
        
        return {
            "message": "Webhook procesado correctamente",
            "filename": filename,
            "pickup_caes_detected": log_data["pickup_caes_detected"],
            "caes_tag_already_present": log_data["caes_tag_already_present"],
            "caes_tag_added": log_data["caes_tag_added"],
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


# ========== ENDPOINT DE SALUD ==========

@app.get("/health")
async def health_check():
    """Endpoint para verificar que el servicio está funcionando"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "api_configured": bool(API_BASE_URL and API_USER and API_PASSWORD)
    }


# ========== INICIO DEL SERVIDOR ==========

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 🔐 Variables de Entorno

### Archivo .env

Crear archivo `.env` en la raíz del proyecto:

```env
# URL base de tu servidor (para desarrollo local)
BASE_URL=http://localhost:8000

# Configuración de la API externa de facturación
API_BASE_URL=http://44.241.185.89/ApiShopify
API_USER=Fenix
API_PASSWORD=d5b8f9vviGIOKp/R3wJqfQ==
```

### Explicación de Variables

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `BASE_URL` | URL de tu servidor local/producción | `http://localhost:8000` |
| `API_BASE_URL` | URL base de la API de facturación | `http://api.example.com/ApiShopify` |
| `API_USER` | Usuario para autenticación | `usuario123` |
| `API_PASSWORD` | Contraseña para autenticación | `password_encriptado` |

### ⚠️ Seguridad

- **NUNCA** subir el archivo `.env` al repositorio
- Usar un gestor de secretos en producción (AWS Secrets Manager, Azure Key Vault, etc.)
- Rotar credenciales regularmente

---

## 🔌 Endpoint /webhook

### Información General

- **URL**: `POST /webhook`
- **Content-Type**: `application/json`
- **Timeout**: 30 segundos
- **En producción**: Usar HTTPS

### Request

#### Headers

```http
POST /webhook HTTP/1.1
Host: tu-servidor.com
Content-Type: application/json
User-Agent: Shopify/1.0
```

#### Body (Ejemplo)

```json
{
  "id": 7110744637533,
  "name": "#1010",
  "email": "cliente@example.com",
  "total_price": "124.00",
  "currency": "GTQ",
  "tags": "",
  "shipping_address": null,
  "shipping_lines": [
    {
      "id": 6167144431709,
      "code": "Injerto Carretera A El Salvador",
      "title": "Injerto Carretera A El Salvador",
      "price": "0.00"
    }
  ],
  "line_items": [...],
  "customer": {...}
}
```

### Response

#### Success (200 OK)

```json
{
  "message": "Webhook procesado correctamente",
  "filename": "webhook_20260311_152030_a1b2c3d4.txt",
  "pickup_caes_detected": true,
  "caes_tag_already_present": false,
  "caes_tag_added": true,
  "facturar_status": 200
}
```

#### Error (500 Internal Server Error)

```json
{
  "detail": "Error procesando webhook: Connection timeout"
}
```

### Campos del Response

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `message` | string | Mensaje de éxito |
| `filename` | string | Nombre del archivo de log generado |
| `pickup_caes_detected` | boolean | Si se detectó como Pickup CAES |
| `caes_tag_already_present` | boolean | Si el tag CAES ya existía |
| `caes_tag_added` | boolean | Si se agregó el tag CAES |
| `facturar_status` | integer | Código HTTP de respuesta de la API de facturación |

---

## 📝 Ejemplos de Uso

### Ejemplo 1: Pickup CAES sin tag

**Request:**
```json
{
  "id": 123456,
  "tags": "",
  "shipping_address": null,
  "shipping_lines": [{
    "code": "Injerto Carretera A El Salvador",
    "title": "Injerto Carretera A El Salvador",
    "price": "0.00"
  }]
}
```

**Response:**
```json
{
  "pickup_caes_detected": true,
  "caes_tag_already_present": false,
  "caes_tag_added": true,
  "facturar_status": 200
}
```

**Payload enviado a API:**
```json
{
  "id": 123456,
  "tags": "CAES",  // ← Tag agregado
  "shipping_address": null,
  ...
}
```

### Ejemplo 2: Pickup CAES con tag existente

**Request:**
```json
{
  "id": 123457,
  "tags": "CAES, urgente",
  "shipping_address": null,
  "shipping_lines": [{
    "code": "Injerto Carretera A El Salvador",
    "title": "Injerto Carretera A El Salvador",
    "price": "0.00"
  }]
}
```

**Response:**
```json
{
  "pickup_caes_detected": true,
  "caes_tag_already_present": true,
  "caes_tag_added": false,  // ← NO se modificó
  "facturar_status": 200
}
```

### Ejemplo 3: Delivery a CAES (NO es pickup)

**Request:**
```json
{
  "id": 123458,
  "tags": "CAES",
  "shipping_address": {
    "address1": "Carretera A El Salvador",
    "city": "Guatemala"
  },
  "shipping_lines": [{
    "price": "35.00"  // ← Tiene costo de envío
  }]
}
```

**Response:**
```json
{
  "pickup_caes_detected": false,  // ← NO es pickup
  "caes_tag_already_present": false,
  "caes_tag_added": false,
  "facturar_status": 200
}
```

### Ejemplo 4: Orden normal

**Request:**
```json
{
  "id": 123459,
  "tags": "",
  "shipping_address": {
    "address1": "5ta Avenida",
    "city": "Guatemala"
  },
  "shipping_lines": [{
    "code": "Envío Capital",
    "price": "35.00"
  }]
}
```

**Response:**
```json
{
  "pickup_caes_detected": false,
  "caes_tag_already_present": false,
  "caes_tag_added": false,
  "facturar_status": 200
}
```

---

## 📊 Sistema de Logs

### Ubicación

Los logs se guardan en: `test/webhook_YYYYMMDD_HHMMSS_XXXXXXXX.txt`

### Estructura del Log

```json
{
  "timestamp": "2026-03-11T15:20:30.123456",
  "request_received": {
    // Datos originales recibidos del webhook
  },
  "pickup_caes_detected": true,
  "caes_tag_already_present": false,
  "caes_tag_added": true,
  "original_tags": "",
  "final_tags": "CAES",
  "token_request": {
    "url": "http://api.example.com/api/Token",
    "payload": {"usuario": "Fenix", "clave": "***"},
    "status": 200,
    "success": true,
    "response": {
      "headers": {...},
      "body": {"data": "eyJhbGc..."}
    }
  },
  "facturar_request": {
    "url": "http://api.example.com/api/Facturar",
    "payload_count": 1,
    "note": "Payload includes CAES tag if detected"
  },
  "payload_sent_to_api": [
    {
      // Payload EXACTO enviado a la API
    }
  ],
  "facturar_response": {
    "status_code": 200,
    "headers": {...},
    "body": {...},
    "raw_text": "..."
  },
  "error": null
}
```

### Tipos de Logs

1. **Logs exitosos**: `webhook_YYYYMMDD_HHMMSS_XXXXXXXX.txt`
2. **Logs con error**: `webhook_error_YYYYMMDD_HHMMSS_XXXXXXXX.txt`

### Rotación de Logs

Se recomienda implementar rotación de logs:

```python
# Agregar al código (opcional)
from logging.handlers import RotatingFileHandler
import logging

# Configurar logging
logging.basicConfig(
    handlers=[RotatingFileHandler('logs/app.log', maxBytes=10000000, backupCount=5)],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

---

## ⚠️ Manejo de Errores

### Errores Comunes

#### 1. Variables de entorno no configuradas

**Error:**
```json
{
  "detail": "Variables de entorno de la API no configuradas"
}
```

**Solución:**
- Verificar que el archivo `.env` existe
- Verificar que las variables están correctamente definidas
- Reiniciar el servidor después de cambiar `.env`

#### 2. Error al obtener token

**Error:**
```json
{
  "detail": "Error obteniendo token: Unauthorized"
}
```

**Solución:**
- Verificar credenciales (`API_USER` y `API_PASSWORD`)
- Verificar que la API externa está funcionando
- Verificar conectividad de red

#### 3. Error en facturación

**Error en log:**
```json
{
  "facturar_response": {
    "status_code": 400,
    "body": {
      "Validacion": ["El total de la factura no coincide"]
    }
  },
  "error": "Error en facturación: Status 400"
}
```

**Solución:**
- Revisar el `payload_sent_to_api` en el log
- Verificar que los datos de Shopify son correctos
- Contactar al equipo de la API externa

#### 4. Timeout

**Error:**
```json
{
  "detail": "Error procesando webhook: Connection timeout"
}
```

**Solución:**
- Aumentar el timeout (actual: 30s)
- Verificar conectividad con la API externa
- Implementar reintentos (retry)

### Códigos de Estado HTTP

| Código | Significado | Acción |
|--------|-------------|--------|
| 200 | OK | Todo funcionó correctamente |
| 400 | Bad Request | Datos inválidos en el request |
| 401 | Unauthorized | Credenciales incorrectas |
| 500 | Internal Server Error | Error en el servidor |
| 503 | Service Unavailable | API externa no disponible |

---

## 🧪 Testing

### Testing Manual con cURL

#### Test 1: Pickup CAES

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "id": 123456,
    "tags": "",
    "shipping_address": null,
    "shipping_lines": [{
      "code": "Injerto Carretera A El Salvador",
      "title": "Injerto Carretera A El Salvador",
      "price": "0.00"
    }]
  }'
```

#### Test 2: Health Check

```bash
curl http://localhost:8000/health
```

### Testing con Python

```python
import requests
import json

# Configuración
BASE_URL = "http://localhost:8000"

# Test data
order_data = {
    "id": 123456,
    "tags": "",
    "shipping_address": None,
    "shipping_lines": [{
        "code": "Injerto Carretera A El Salvador",
        "title": "Injerto Carretera A El Salvador",
        "price": "0.00"
    }]
}

# Enviar request
response = requests.post(
    f"{BASE_URL}/webhook",
    json=order_data,
    headers={"Content-Type": "application/json"}
)

# Verificar respuesta
print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")

# Verificaciones
assert response.status_code == 200
assert response.json()["pickup_caes_detected"] == True
assert response.json()["caes_tag_added"] == True
```

### Unit Tests

```python
import pytest
from main import is_pickup_caes, add_caes_tag

def test_is_pickup_caes_true():
    order = {
        "shipping_address": None,
        "shipping_lines": [{
            "code": "Injerto Carretera A El Salvador",
            "title": "Injerto Carretera A El Salvador",
            "price": "0.00"
        }]
    }
    assert is_pickup_caes(order) == True

def test_is_pickup_caes_false_with_address():
    order = {
        "shipping_address": {"city": "Guatemala"},
        "shipping_lines": [{
            "code": "Injerto Carretera A El Salvador",
            "title": "Injerto Carretera A El Salvador",
            "price": "0.00"
        }]
    }
    assert is_pickup_caes(order) == False

def test_add_caes_tag():
    order = {"tags": ""}
    result = add_caes_tag(order)
    assert result["tags"] == "CAES"

def test_add_caes_tag_no_duplicate():
    order = {"tags": "CAES, urgente"}
    result = add_caes_tag(order)
    assert result["tags"] == "CAES, urgente"
```

---

## 🚢 Deployment

### Opción 1: Servidor Local/VPS

#### Paso 1: Configurar el servidor

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python
sudo apt install python3.9 python3-pip python3-venv -y

# Clonar proyecto
git clone https://tu-repo.git
cd webhook-shopify

# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

#### Paso 2: Configurar servicio systemd

Crear `/etc/systemd/system/webhook.service`:

```ini
[Unit]
Description=Webhook Shopify API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/webhook-shopify
Environment="PATH=/path/to/webhook-shopify/.venv/bin"
ExecStart=/path/to/webhook-shopify/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable webhook
sudo systemctl start webhook
sudo systemctl status webhook
```

#### Paso 3: Configurar Nginx (opcional)

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Opción 2: Docker

#### Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  webhook:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./test:/app/test
    env_file:
      - .env
    restart: unless-stopped
```

### Opción 3: Cloud (AWS, Azure, GCP)

#### AWS Elastic Beanstalk

```bash
# Instalar EB CLI
pip install awsebcli

# Inicializar
eb init -p python-3.9 webhook-shopify

# Crear entorno
eb create webhook-production

# Desplegar
eb deploy
```

#### Variables de entorno en AWS

```bash
eb setenv API_BASE_URL=http://api.example.com API_USER=usuario API_PASSWORD=password
```

---

## 🔍 Troubleshooting

### Problema: El servidor no inicia

**Síntomas:**
```
ERROR:    [Errno 98] Address already in use
```

**Solución:**
```bash
# Encontrar proceso usando el puerto
sudo lsof -i :8000

# Matar proceso
kill -9 <PID>

# O usar otro puerto
uvicorn main:app --port 8001
```

### Problema: Logs no se guardan

**Síntomas:**
- Carpeta `test/` vacía
- Error de permisos

**Solución:**
```bash
# Verificar permisos
ls -la test/

# Dar permisos
chmod 755 test/

# Verificar que la carpeta existe
mkdir -p test
```

### Problema: API externa no responde

**Síntomas:**
```json
{
  "detail": "Error procesando webhook: Connection timeout"
}
```

**Solución:**
1. Verificar conectividad:
   ```bash
   curl http://44.241.185.89/ApiShopify/api/Token
   ```

2. Verificar firewall

3. Aumentar timeout:
   ```python
   async with httpx.AsyncClient(timeout=60.0) as client:
   ```

### Problema: Tag CAES no se agrega

**Diagnóstico:**

1. Revisar el log generado
2. Verificar `pickup_caes_detected`
3. Verificar condiciones de detección

**Debug:**
```python
# Agregar prints temporales
print(f"shipping_address: {order.get('shipping_address')}")
print(f"shipping_lines: {order.get('shipping_lines')}")
```

---

## 📚 Referencias

### APIs Utilizadas

- **FastAPI**: https://fastapi.tiangolo.com/
- **httpx**: https://www.python-httpx.org/
- **Shopify Webhooks**: https://shopify.dev/docs/api/admin-rest/2024-01/resources/webhook

### Recursos Adicionales

- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Python Async/Await](https://docs.python.org/3/library/asyncio.html)
- [JWT Authentication](https://jwt.io/)

---

## 📞 Soporte

### Checklist antes de reportar un problema

- [ ] Revisar logs en `test/webhook_error_*.txt`
- [ ] Verificar variables de entorno
- [ ] Verificar conectividad con API externa
- [ ] Revisar esta documentación
- [ ] Intentar con datos de ejemplo

### Información a incluir en reporte

1. Versión de Python
2. Contenido del archivo `.env` (sin passwords)
3. Logs completos del error
4. Payload de ejemplo que causó el error
5. Resultado esperado vs resultado actual

---

## 📄 Licencia

Este proyecto es de uso interno. Todos los derechos reservados.

---

## 🔄 Changelog

### v1.0.0 (2026-03-11)
- ✨ Implementación inicial del webhook
- ✨ Detección de Pickup CAES
- ✨ Integración con API de facturación
- ✨ Sistema completo de logging
- 📝 Documentación completa

---

**Última actualización**: 11 de marzo de 2026
**Autor**: Equipo de Desarrollo
**Contacto**: dev@example.com
