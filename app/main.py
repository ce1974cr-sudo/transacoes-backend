from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date
from decimal import Decimal
import os

app = FastAPI(title="Transações Imobiliárias API", version="1.0.0")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique o domínio do frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração do banco de dados
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgres://avnadmin:AVNS_Bj2e6D_lxvVvyiApBgX@pg-b7344e5-ce1974cr-bedd.g.aivencloud.com:16026/defaultdb?sslmode=require"
)

def get_db_connection():
    """Cria conexão com o banco de dados"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao conectar ao banco: {str(e)}")

def convert_decimal(obj):
    """Converte Decimal para float para serialização JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, date):
        return obj.isoformat()
    return obj

@app.get("/")
def read_root():
    """Endpoint raiz"""
    return {
        "message": "API de Transações Imobiliárias",
        "version": "1.0.0",
        "endpoints": {
            "/transacoes": "Buscar transações com filtros",
            "/stats": "Estatísticas gerais do banco"
        }
    }

@app.get("/transacoes")
def get_transacoes(
    cadastro_sql: Optional[str] = Query(None, description="Parte do número do cadastro SQL"),
    numero: Optional[int] = Query(None, description="Número do imóvel"),
    area_minima: Optional[float] = Query(None, description="Área construída mínima (m²)"),
    area_maxima: Optional[float] = Query(None, description="Área construída máxima (m²)"),
    limit: int = Query(1000, description="Limite de resultados", le=5000)
):
    """
    Busca transações imobiliárias com filtros opcionais
    
    Retorna:
    - transacoes: Lista de transações ordenadas por data (mais recente primeiro)
    - grafico: Dados agregados para o gráfico de barras
    - total: Total de registros encontrados
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Construir query dinamicamente
        where_clauses = []
        params = []
        
        if cadastro_sql:
            where_clauses.append("cadastro_sql LIKE %s")
            params.append(f"%{cadastro_sql}%")
        
        if numero is not None:
            where_clauses.append("numero = %s")
            params.append(numero)
        
        if area_minima is not None:
            where_clauses.append("area_construida >= %s")
            params.append(area_minima)
        
        if area_maxima is not None:
            where_clauses.append("area_construida <= %s")
            params.append(area_maxima)
        
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        
        # Query para buscar transações
        query = f"""
            SELECT 
                id,
                cadastro_sql,
                nome_logradouro,
                numero,
                complemento,
                cep,
                valor_transacao,
                data_transacao,
                area_construida
            FROM transacoes_imobiliarias
            WHERE {where_sql}
            ORDER BY data_transacao DESC
            LIMIT %s
        """
        
        params.append(limit)
        cursor.execute(query, params)
        transacoes = cursor.fetchall()
        
        # Converter para formato serializável
        transacoes_list = []
        for t in transacoes:
            transacoes_list.append({
                "id": t["id"],
                "cadastro_sql": t["cadastro_sql"],
                "nome_logradouro": t["nome_logradouro"],
                "numero": t["numero"],
                "complemento": t["complemento"],
                "cep": t["cep"],
                "valor_transacao": convert_decimal(t["valor_transacao"]),
                "data_transacao": convert_decimal(t["data_transacao"]),
                "area_construida": convert_decimal(t["area_construida"])
            })
        
        # Query para dados do gráfico (agregado por mês)
        query_grafico = f"""
            SELECT 
                DATE_TRUNC('month', data_transacao) as mes,
                COUNT(*) as quantidade,
                AVG(valor_transacao) as valor_medio,
                SUM(valor_transacao) as valor_total
            FROM transacoes_imobiliarias
            WHERE {where_sql}
            GROUP BY DATE_TRUNC('month', data_transacao)
            ORDER BY mes ASC
        """
        
        cursor.execute(query_grafico, params[:-1])  # Sem o limit
        grafico_data = cursor.fetchall()
        
        grafico_list = []
        for g in grafico_data:
            grafico_list.append({
                "mes": convert_decimal(g["mes"]),
                "quantidade": g["quantidade"],
                "valor_medio": convert_decimal(g["valor_medio"]),
                "valor_total": convert_decimal(g["valor_total"])
            })
        
        # Contar total de registros
        query_count = f"""
            SELECT COUNT(*) as total
            FROM transacoes_imobiliarias
            WHERE {where_sql}
        """
        
        cursor.execute(query_count, params[:-1])
        total = cursor.fetchone()["total"]
        
        cursor.close()
        conn.close()
        
        return {
            "transacoes": transacoes_list,
            "grafico": grafico_list,
            "total": total,
            "limite_aplicado": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar transações: {str(e)}")

@app.get("/stats")
def get_stats():
    """Retorna estatísticas gerais do banco de dados"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                COUNT(*) as total_transacoes,
                MIN(data_transacao) as data_minima,
                MAX(data_transacao) as data_maxima,
                AVG(valor_transacao) as valor_medio,
                MIN(valor_transacao) as valor_minimo,
                MAX(valor_transacao) as valor_maximo,
                AVG(area_construida) as area_media,
                MIN(area_construida) as area_minima,
                MAX(area_construida) as area_maxima
            FROM transacoes_imobiliarias
            WHERE data_transacao IS NOT NULL
        """
        
        cursor.execute(query)
        stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            "total_transacoes": stats["total_transacoes"],
            "periodo": {
                "data_minima": convert_decimal(stats["data_minima"]),
                "data_maxima": convert_decimal(stats["data_maxima"])
            },
            "valores": {
                "medio": convert_decimal(stats["valor_medio"]),
                "minimo": convert_decimal(stats["valor_minimo"]),
                "maximo": convert_decimal(stats["valor_maximo"])
            },
            "areas": {
                "media": convert_decimal(stats["area_media"]),
                "minima": convert_decimal(stats["area_minima"]),
                "maxima": convert_decimal(stats["area_maxima"])
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar estatísticas: {str(e)}")

@app.get("/health")
def health_check():
    """Endpoint de health check"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}

