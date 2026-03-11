"""
Script de testing para el webhook de Shopify
Ejecutar: python test_webhook.py
"""

import requests
import json
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:8000"

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'


def print_test(name, passed, details=""):
    """Imprime resultado de test con color"""
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"{status} - {name}")
    if details:
        print(f"  {details}")


def test_health_check():
    """Test 1: Verificar que el servidor está funcionando"""
    print(f"\n{YELLOW}Test 1: Health Check{RESET}")
    try:
        response = requests.get(f"{BASE_URL}/health")
        passed = response.status_code == 200
        print_test("Health check", passed, f"Status: {response.status_code}")
        if passed:
            print(f"  Response: {json.dumps(response.json(), indent=2)}")
        return passed
    except Exception as e:
        print_test("Health check", False, f"Error: {str(e)}")
        return False


def test_pickup_caes_no_tag():
    """Test 2: Pickup CAES sin tag existente"""
    print(f"\n{YELLOW}Test 2: Pickup CAES sin tag{RESET}")
    
    order_data = {
        "id": 999001,
        "name": "#TEST001",
        "tags": "",
        "email": "test@example.com",
        "total_price": "100.00",
        "shipping_address": None,
        "shipping_lines": [{
            "id": 1,
            "code": "Injerto Carretera A El Salvador",
            "title": "Injerto Carretera A El Salvador",
            "price": "0.00"
        }],
        "line_items": [{
            "id": 1,
            "name": "Producto Test",
            "price": "100.00",
            "quantity": 1
        }]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhook",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        passed = (
            response.status_code == 200 and
            response.json().get("pickup_caes_detected") == True and
            response.json().get("caes_tag_added") == True
        )
        
        print_test("Pickup CAES detectado", passed)
        print(f"  Response: {json.dumps(response.json(), indent=2)}")
        return passed
        
    except Exception as e:
        print_test("Pickup CAES sin tag", False, f"Error: {str(e)}")
        return False


def test_pickup_caes_with_tag():
    """Test 3: Pickup CAES con tag existente"""
    print(f"\n{YELLOW}Test 3: Pickup CAES con tag existente{RESET}")
    
    order_data = {
        "id": 999002,
        "name": "#TEST002",
        "tags": "CAES, urgente",  # Ya tiene el tag
        "email": "test@example.com",
        "total_price": "100.00",
        "shipping_address": None,
        "shipping_lines": [{
            "id": 1,
            "code": "Injerto Carretera A El Salvador",
            "title": "Injerto Carretera A El Salvador",
            "price": "0.00"
        }]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhook",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        passed = (
            response.status_code == 200 and
            response.json().get("pickup_caes_detected") == True and
            response.json().get("caes_tag_already_present") == True and
            response.json().get("caes_tag_added") == False
        )
        
        print_test("Tag existente no modificado", passed)
        print(f"  Response: {json.dumps(response.json(), indent=2)}")
        return passed
        
    except Exception as e:
        print_test("Pickup CAES con tag", False, f"Error: {str(e)}")
        return False


def test_regular_delivery():
    """Test 4: Delivery regular (NO pickup)"""
    print(f"\n{YELLOW}Test 4: Delivery regular{RESET}")
    
    order_data = {
        "id": 999003,
        "name": "#TEST003",
        "tags": "",
        "email": "test@example.com",
        "total_price": "135.00",
        "shipping_address": {
            "address1": "5ta Avenida",
            "city": "Guatemala",
            "country": "Guatemala"
        },
        "shipping_lines": [{
            "id": 1,
            "code": "Envío Capital",
            "title": "Envío Capital",
            "price": "35.00"  # Tiene costo
        }]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhook",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        passed = (
            response.status_code == 200 and
            response.json().get("pickup_caes_detected") == False and
            response.json().get("caes_tag_added") == False
        )
        
        print_test("Delivery regular (no pickup)", passed)
        print(f"  Response: {json.dumps(response.json(), indent=2)}")
        return passed
        
    except Exception as e:
        print_test("Delivery regular", False, f"Error: {str(e)}")
        return False


def test_delivery_to_caes():
    """Test 5: Delivery a dirección en CAES (NO es pickup pero puede tener tag)"""
    print(f"\n{YELLOW}Test 5: Delivery a CAES{RESET}")
    
    order_data = {
        "id": 999004,
        "name": "#TEST004",
        "tags": "CAES",  # Tag agregado por otra automatización
        "email": "test@example.com",
        "total_price": "135.00",
        "shipping_address": {
            "address1": "Carretera A El Salvador Km 10",
            "city": "Guatemala",
            "country": "Guatemala"
        },
        "shipping_lines": [{
            "id": 1,
            "code": "Envío CAES",
            "title": "Envío CAES",
            "price": "25.00"  # Tiene costo
        }]
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/webhook",
            json=order_data,
            headers={"Content-Type": "application/json"}
        )
        
        # NO debe detectarse como pickup porque tiene shipping_address
        passed = (
            response.status_code == 200 and
            response.json().get("pickup_caes_detected") == False
        )
        
        print_test("Delivery a CAES (no es pickup)", passed)
        print(f"  Response: {json.dumps(response.json(), indent=2)}")
        return passed
        
    except Exception as e:
        print_test("Delivery a CAES", False, f"Error: {str(e)}")
        return False


def main():
    """Ejecutar todos los tests"""
    print("=" * 60)
    print("TESTING WEBHOOK SHOPIFY")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Ejecutar tests
    results.append(("Health Check", test_health_check()))
    results.append(("Pickup CAES sin tag", test_pickup_caes_no_tag()))
    results.append(("Pickup CAES con tag", test_pickup_caes_with_tag()))
    results.append(("Delivery regular", test_regular_delivery()))
    results.append(("Delivery a CAES", test_delivery_to_caes()))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    failed = total - passed
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{status} - {name}")
    
    print("\n" + "-" * 60)
    print(f"Total: {total} | Passed: {GREEN}{passed}{RESET} | Failed: {RED}{failed}{RESET}")
    
    if failed == 0:
        print(f"\n{GREEN}✓ Todos los tests pasaron exitosamente!{RESET}")
    else:
        print(f"\n{RED}✗ {failed} test(s) fallaron{RESET}")
    
    print("\nVerifica los logs en la carpeta test/ para más detalles")


if __name__ == "__main__":
    main()
