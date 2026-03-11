# Quick Start - Webhook Shopify

Guía rápida de 5 minutos para poner en marcha el webhook.

## 📦 Instalación Rápida

```bash
# 1. Clonar/crear proyecto
mkdir webhook-shopify && cd webhook-shopify

# 2. Crear entorno virtual
python -m venv .venv

# 3. Activar
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# 4. Instalar dependencias
pip install fastapi uvicorn httpx python-dotenv
```

## ⚙️ Configuración

Crear archivo `.env`:

```env
BASE_URL=http://localhost:8000
API_BASE_URL=http://tu-api.com/ApiShopify
API_USER=tu_usuario
API_PASSWORD=tu_password
```

## 🚀 Ejecutar

```bash
uvicorn main:app --reload
```

El servidor estará disponible en: `http://localhost:8000`

## 🧪 Probar

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

## 📋 Verificar

- ✅ Response 200 OK
- ✅ `pickup_caes_detected: true`
- ✅ `caes_tag_added: true`
- ✅ Archivo creado en `test/webhook_*.txt`

## 📖 Documentación Completa

Ver [WEBHOOK_DOCUMENTATION.md](./WEBHOOK_DOCUMENTATION.md) para detalles completos.

## ❓ Problemas Comunes

### Error: "Variables de entorno no configuradas"
➡️ Verifica que el archivo `.env` existe y tiene las variables correctas

### Error: "Address already in use"
➡️ Usa otro puerto: `uvicorn main:app --port 8001`

### Tag CAES no se agrega
➡️ Revisa el log en `test/` para ver qué condición falló

## 📞 Ayuda

Para más ayuda, consulta la documentación completa o revisa los logs en la carpeta `test/`.
