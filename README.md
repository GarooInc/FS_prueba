# Webhook Shopify - Sistema de Facturación

Sistema automatizado de procesamiento de webhooks de Shopify con detección inteligente de Pickup CAES e integración con API de facturación externa.

## 🎯 Funcionalidades

- ✅ **Recepción de webhooks** de Shopify
- ✅ **Detección automática** de órdenes Pickup CAES
- ✅ **Agregado inteligente de tags** (evita duplicados)
- ✅ **Integración con API externa** de facturación
- ✅ **Sistema completo de logs** para auditoría
- ✅ **Manejo robusto de errores**

## 📖 Documentación

### Para empezar rápido (5 minutos)
📄 [QUICK_START.md](./QUICK_START.md)

### Documentación completa
📚 [WEBHOOK_DOCUMENTATION.md](./WEBHOOK_DOCUMENTATION.md) - Incluye:
- Instalación detallada
- Configuración paso a paso
- Lógica de negocio completa
- Código explicado línea por línea
- Ejemplos de uso
- Sistema de logs
- Troubleshooting
- Deployment en producción

## 🚀 Inicio Rápido

```bash
# 1. Instalar dependencias
pip install fastapi uvicorn httpx python-dotenv

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 3. Ejecutar servidor
uvicorn main:app --reload
```

Servidor disponible en: `http://localhost:8000`

## 🧪 Testing

```bash
# Ejecutar suite de tests
python test_webhook.py
```

O manualmente:

```bash
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"id": 123, "tags": "", "shipping_address": null, "shipping_lines": [{"code": "Injerto Carretera A El Salvador", "title": "Injerto Carretera A El Salvador", "price": "0.00"}]}'
```

## 📊 Estructura del Proyecto

```
webhook-shopify/
├── main.py                        # Código principal de la API
├── requirements.txt               # Dependencias de Python
├── .env                          # Variables de entorno (no incluir en git)
├── .env.example                  # Ejemplo de configuración
├── test_webhook.py               # Script de testing
├── README.md                     # Este archivo
├── QUICK_START.md                # Guía rápida
├── WEBHOOK_DOCUMENTATION.md      # Documentación completa
└── test/                         # Carpeta de logs
    ├── webhook_*.txt             # Logs exitosos
    └── webhook_error_*.txt       # Logs con errores
```

## 🔑 Variables de Entorno

```env
BASE_URL=http://localhost:8000
API_BASE_URL=http://tu-api.com/ApiShopify
API_USER=tu_usuario
API_PASSWORD=tu_password
```

Ver [.env.example](./.env.example) para más detalles.

## 🔁 Flujo del Sistema

```
┌─────────────┐
│   Shopify   │
│    Order    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│  POST /webhook                      │
│  ├─ 1. Recibir JSON                 │
│  ├─ 2. Detectar Pickup CAES         │
│  ├─ 3. Agregar tag si aplica        │
│  ├─ 4. Obtener token JWT            │
│  ├─ 5. Enviar a API facturación     │
│  └─ 6. Guardar logs                 │
└──────┬──────────────────────────────┘
       │
       ├──────────► test/webhook_*.txt (logs)
       │
       ▼
┌─────────────┐
│ API Externa │
│ Facturación │
└─────────────┘
```

## 🎯 Detección de Pickup CAES

Una orden se detecta como **Pickup CAES** cuando cumple:

1. ✅ `shipping_address` es `null`
2. ✅ `shipping_lines` existe
3. ✅ `shipping_lines[0].price` es `"0.00"`
4. ✅ `code` y `title` son `"Injerto Carretera A El Salvador"`

Si cumple todas las condiciones Y NO tiene el tag "CAES" → se agrega automáticamente.

## 📝 Ejemplo de Response

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

## 📊 Sistema de Logs

Cada webhook genera un archivo JSON en `test/` con:

- ✅ Request original recibido
- ✅ Detección de Pickup CAES
- ✅ Tags (originales y finales)
- ✅ Request/Response del token
- ✅ Payload exacto enviado a API
- ✅ Response de la API de facturación
- ✅ Errores (si los hay)

Ejemplo: `test/webhook_20260311_152030_a1b2c3d4.txt`

## 🛠️ Tecnologías

- **FastAPI** - Framework web moderno y rápido
- **httpx** - Cliente HTTP asíncrono
- **Python 3.9+** - Lenguaje base
- **uvicorn** - Servidor ASGI

## 📦 Dependencias

```txt
fastapi
uvicorn
python-multipart
aiofiles
python-dotenv
httpx
```

## 🚢 Deployment

### Desarrollo
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Producción
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Ver [WEBHOOK_DOCUMENTATION.md](./WEBHOOK_DOCUMENTATION.md#deployment) para opciones de deployment (Docker, AWS, etc.).

## ⚠️ Notas Importantes

1. **Integridad de datos**: El payload enviado a la API externa es el original de Shopify, solo se modifica el campo `tags` si aplica.

2. **No duplicar tags**: Si la orden ya trae el tag "CAES" (por otra automatización), NO se modifica.

3. **Logging completo**: Cada webhook se registra completamente para auditoría y debugging.

4. **Manejo de errores**: Errores se capturan y registran sin detener el servicio.

## 🔍 Troubleshooting Rápido

### Servidor no inicia
```bash
# Verificar puerto disponible
lsof -i :8000
# Usar otro puerto
uvicorn main:app --port 8001
```

### Tag no se agrega
➡️ Revisar logs en `test/` para ver qué condición falló

### Error de API externa
➡️ Verificar credenciales en `.env`
➡️ Verificar conectividad: `curl http://tu-api.com/health`

## 📞 Recursos

- 🚀 [Quick Start](./QUICK_START.md) - Comienza en 5 minutos
- 📚 [Documentación Completa](./WEBHOOK_DOCUMENTATION.md) - Todo lo que necesitas saber
- 🧪 [Test Script](./test_webhook.py) - Suite de tests automatizados
- ⚙️ [Configuración](/.env.example) - Ejemplo de variables de entorno

## 🤝 Contribuir

1. Hacer fork del proyecto
2. Crear branch de feature (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📄 Licencia

Proyecto de uso interno. Todos los derechos reservados.

---

**Última actualización**: 11 de marzo de 2026  
**Versión**: 1.0.0  
**Contacto**: dev@example.com