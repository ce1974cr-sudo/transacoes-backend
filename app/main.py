
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

# URL do banco IPTU (ATUALIZADO - novo banco com dados filtrados)
IPTU_DATABASE_URL = os.getenv(
    "IPTU_DATABASE_URL",
    "postgres://avnadmin:AVNS_OZCL90XDQn0uXwHTnbV@pg-210ec680-kalcaterra-04c1.d.aivencloud.com:15805/defaultdb?sslmode=require"
)

def get_db_connection():
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao conectar ao banco: {str(e)}")

def get_iptu_connection():
    try:
        return psycopg2.connect(IPTU_DATABASE_URL)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao conectar ao banco IPTU: {str(e)}")

def normalize_contribuinte(numero: str) -> str:
    """
    Converte número de transações para formato IPTU.
    
    Exemplo:
    - Entrada: 10155402756 (11 dígitos, formato transações)
    - Saída: 1015540275-6 (formato IPTU com hífen)
    
    Algoritmo:
    1. Remove espaços, hífens e caracteres especiais
    2. Se tem 11 dígitos: pega os primeiros 10 e adiciona hífen antes do último
    3. Se já tem hífen: retorna como está
    4. Se tem 10 dígitos: retorna como está
    """
    # Remove espaços, hífens e caracteres especiais
    numero_limpo = numero.strip().replace('-', '').replace(' ', '')
    
    # Se tem 11 dígitos (formato transações), converte para formato IPTU
    if len(numero_limpo) == 11:
        # Pega os primeiros 10 dígitos e adiciona hífen antes do último
        return f"{numero_limpo[:10]}-{numero_limpo[10]}"
    
    # Se tem 10 dígitos, retorna como está (pode já estar no formato correto)
    if len(numero_limpo) == 10:
        return numero_limpo
    
    # Se tem hífen, retorna como está
    if '-' in numero:
        return numero_limpo
    
    return numero_limpo

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

    # 🔥 NOVOS FILTROS
    valor_min: Optional[float] = Query(None),
    valor_max: Optional[float] = Query(None),

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

        # 🔥 FILTRO DE VALOR
        if valor_min is not None:
            where_clauses.append("valor_transacao >= %s")
            params.append(valor_min)

        if valor_max is not None:
            where_clauses.append("valor_transacao <= %s")
            params.append(valor_max)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        # 🔹 QUERY PRINCIPAL
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

        # 🔹 LISTA PARA TABELA
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

        # 🔹 DADOS DO GRÁFICO (valores reais)
        grafico_list = []
        for t in transacoes:
            grafico_list.append({
                "data": convert_decimal(t["data_transacao"]),
                "valor": convert_decimal(t["valor_transacao"])
            })

        # 🔹 TOTAL (sem limit)
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

# ============================================================================
# ENDPOINTS IPTU - NOVOS COM NORMALIZAÇÃO CORRIGIDA
# ============================================================================

@app.get("/api/iptu/contribuinte/{numero_contribuinte}")
def get_iptu_by_contribuinte(numero_contribuinte: str):
    """
    Busca dados do IPTU por número de contribuinte.
    
    Aceita formatos:
    - 10155402756 (11 dígitos, formato transações)
    - 1015540275-6 (formato IPTU com hífen)
    
    Exemplo: GET /api/iptu/contribuinte/10155402756
    """
    try:
        conn = get_iptu_connection()
        cursor = conn.cursor()
        
        # Normalizar numero_contribuinte
        numero_normalizado = normalize_contribuinte(numero_contribuinte)
        
        # Query para buscar IPTU
        query = """
            SELECT 
                numero_contribuinte,
                nome_logradouro,
                numero_imovel,
                cep_imovel,
                bairro_imovel,
                area_construida,
                valor_m2_terreno,
                valor_m2_construcao,
                tipo_uso_imovel,
                ano_construcao
            FROM iptu_2026
            WHERE numero_contribuinte = %s
            LIMIT 1
        """
        
        cursor.execute(query, (numero_normalizado,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"IPTU não encontrado para contribuinte: {numero_contribuinte} (normalizado: {numero_normalizado})"
            )
        
        # Converter resultado para dicionário
        iptu_data = {
            "numero_contribuinte": result[0],
            "nome_logradouro": result[1],
            "numero_imovel": result[2],
            "cep_imovel": result[3],
            "bairro_imovel": result[4],
            "area_construida": float(result[5]) if result[5] else None,
            "valor_m2_terreno": float(result[6]) if result[6] else None,
            "valor_m2_construcao": float(result[7]) if result[7] else None,
            "tipo_uso_imovel": result[8],
            "ano_construcao": result[9]
        }
        
        return iptu_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar IPTU: {str(e)}"
        )


@app.get("/api/iptu/cep/{cep}")
def get_iptu_by_cep(cep: str):
    """
    Busca todos os IPTUs para um determinado CEP.
    
    Exemplo: GET /api/iptu/cep/05516000
    """
    try:
        conn = get_iptu_connection()
        cursor = conn.cursor()
        
        # Normalizar CEP (remover hífen)
        cep_normalizado = cep.replace('-', '').replace(' ', '')
        
        query = """
            SELECT 
                numero_contribuinte,
                nome_logradouro,
                numero_imovel,
                cep_imovel,
                bairro_imovel,
                area_construida,
                valor_m2_terreno,
                valor_m2_construcao,
                tipo_uso_imovel,
                ano_construcao
            FROM iptu_2026
            WHERE cep_imovel = %s
            ORDER BY nome_logradouro, numero_imovel
            LIMIT 100
        """
        
        cursor.execute(query, (cep_normalizado,))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhum IPTU encontrado para CEP: {cep}"
            )
        
        iptu_list = []
        for row in results:
            iptu_list.append({
                "numero_contribuinte": row[0],
                "nome_logradouro": row[1],
                "numero_imovel": row[2],
                "cep_imovel": row[3],
                "bairro_imovel": row[4],
                "area_construida": float(row[5]) if row[5] else None,
                "valor_m2_terreno": float(row[6]) if row[6] else None,
                "valor_m2_construcao": float(row[7]) if row[7] else None,
                "tipo_uso_imovel": row[8],
                "ano_construcao": row[9]
            })
        
        return iptu_list
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar IPTU por CEP: {str(e)}"
        )


@app.get("/api/iptu/bairro/{bairro}")
def get_iptu_by_bairro(bairro: str):
    """
    Busca todos os IPTUs para um determinado bairro.
    
    Exemplo: GET /api/iptu/bairro/SANTA%20EFIGENIA
    """
    try:
        conn = get_iptu_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                numero_contribuinte,
                nome_logradouro,
                numero_imovel,
                cep_imovel,
                bairro_imovel,
                area_construida,
                valor_m2_terreno,
                valor_m2_construcao,
                tipo_uso_imovel,
                ano_construcao
            FROM iptu_2026
            WHERE UPPER(bairro_imovel) LIKE UPPER(%s)
            ORDER BY nome_logradouro
            LIMIT 100
        """
        
        cursor.execute(query, (f"%{bairro}%",))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhum IPTU encontrado para bairro: {bairro}"
            )
        
        iptu_list = []
        for row in results:
            iptu_list.append({
                "numero_contribuinte": row[0],
                "nome_logradouro": row[1],
                "numero_imovel": row[2],
                "cep_imovel": row[3],
                "bairro_imovel": row[4],
                "area_construida": float(row[5]) if row[5] else None,
                "valor_m2_terreno": float(row[6]) if row[6] else None,
                "valor_m2_construcao": float(row[7]) if row[7] else None,
                "tipo_uso_imovel": row[8],
                "ano_construcao": row[9]
            })
        
        return iptu_list
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar IPTU por bairro: {str(e)}"
        )
