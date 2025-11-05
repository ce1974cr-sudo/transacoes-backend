#!/usr/bin/env python3
"""
Script para testar a API localmente
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_root():
    """Testa endpoint raiz"""
    print("Testando GET /")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def test_health():
    """Testa health check"""
    print("Testando GET /health")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def test_stats():
    """Testa estatísticas"""
    print("Testando GET /stats")
    response = requests.get(f"{BASE_URL}/stats")
    print(f"Status: {response.status_code}")
    print(f"Resposta: {json.dumps(response.json(), indent=2)}")
    print("-" * 50)

def test_transacoes():
    """Testa busca de transações"""
    print("Testando GET /transacoes")
    
    # Teste 1: Sem filtros
    print("\n1. Sem filtros (limit=10)")
    response = requests.get(f"{BASE_URL}/transacoes", params={"limit": 10})
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total encontrado: {data['total']}")
    print(f"Transações retornadas: {len(data['transacoes'])}")
    print(f"Dados do gráfico: {len(data['grafico'])} meses")
    
    # Teste 2: Com filtro de cadastro
    print("\n2. Com filtro de cadastro (cadastro_sql=01)")
    response = requests.get(f"{BASE_URL}/transacoes", params={"cadastro_sql": "01", "limit": 10})
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total encontrado: {data['total']}")
    print(f"Transações retornadas: {len(data['transacoes'])}")
    
    # Teste 3: Com filtro de área
    print("\n3. Com filtro de área (100-200 m²)")
    response = requests.get(f"{BASE_URL}/transacoes", params={
        "area_minima": 100,
        "area_maxima": 200,
        "limit": 10
    })
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total encontrado: {data['total']}")
    print(f"Transações retornadas: {len(data['transacoes'])}")
    
    if data['transacoes']:
        print("\nPrimeira transação:")
        print(json.dumps(data['transacoes'][0], indent=2))
    
    print("-" * 50)

if __name__ == "__main__":
    print("="*50)
    print("TESTE DA API DE TRANSAÇÕES IMOBILIÁRIAS")
    print("="*50)
    print()
    
    try:
        test_root()
        test_health()
        test_stats()
        test_transacoes()
        
        print("\n✓ Todos os testes concluídos!")
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Erro: Não foi possível conectar à API")
        print("Certifique-se de que o servidor está rodando:")
        print("uvicorn app.main:app --reload")
    except Exception as e:
        print(f"\n✗ Erro: {str(e)}")

