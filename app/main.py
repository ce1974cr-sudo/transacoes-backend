from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date
from decimal import Decimal
import os

app = FastAPI(title="Transações Imobiliárias API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgres://avnadmin:AVNS_Bj2e6D_lxvVvyiApBgX@pg-b7344e5-ce1974cr-bedd.g.aivencloud.com:16026/defaultdb?sslmode=require"
)

def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao conectar ao banco: {str(e)}")

def convert_decimal(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, date):
        return obj.isoformat()
    return obj

@app.get("/")
def read_root():
    return {
        "message": "API de Transações Imobiliárias",
        "version": "1.0.0"
    }

@app.get("/transacoes")
def get_transacoes(
    cadastro_sql: Optional[str] = Query(None),
    numero: Optional[int] = Query(None),
    area_minima: Optional[float] = Query(None),
    area_maxima: Optional[float] = Query(None),
    limit: int = Query(10, le=10000)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

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

        # 🔹 QUERY PRINCIPAL (dados reais)
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

        # 🔹 Lista completa (tabela)
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

        # 🔹 DADOS DO GRÁFICO (SEM AGREGAÇÃO)
        grafico_list = []
        for t in transacoes:
            grafico_list.append({
                "data": convert_decimal(t["data_transacao"]),
                "valor": convert_decimal(t["valor_transacao"])
            })

        # 🔹 TOTAL
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

@app.get("/health")
def health_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
