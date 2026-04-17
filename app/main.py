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

def normalize_cep(cep: str) -> str:
    """
    Normaliza CEP removendo caracteres especiais e convertendo para texto.
    
    Processo:
    1. Remove caracteres especiais (hífens, espaços, etc)
    2. Converte para número (remove zeros à esquerda)
    3. Converte de volta para texto SEM adicionar zeros
    
    Exemplos:
    - Entrada: "01001901" → Saída: "1001901"
    - Entrada: "05516000" → Saída: "5516000"
    - Entrada: "01-001-901" → Saída: "1001901"
    """
    if not cep:
        return None
    
    # Remove espaços, hífens e outros caracteres especiais
    cep_limpo = cep.strip().replace('-', '').replace(' ', '').replace('.', '')
    
    # Remove caracteres não numéricos
    cep_numerico = ''.join(filter(str.isdigit, cep_limpo))
    
    # Converte para número (remove zeros à esquerda)
    try:
        cep_int = int(cep_numerico)
    except ValueError:
        return None
    
    # Converte de volta para texto SEM adicionar zeros
    cep_normalizado = str(cep_int)
    
    return cep_normalizado

def normalize_contribuinte(numero: str) -> str:
    """
    Converte número de transações para formato IPTU.
    
    Exemplo:
    - Entrada: 10155402756 (11 dígitos, formato transações)
    - Saída: 1015540275-6 (formato IPTU com hífen)
    """
    numero_limpo = numero.strip().replace('-', '').replace(' ', '')
    
    if len(numero_limpo) == 11:
        return f"{numero_limpo[:10]}-{numero_limpo[10]}"
    
    if len(numero_limpo) == 10:
        return numero_limpo
    
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
    endereco: Optional[str] = Query(None),
    cep: Optional[str] = Query(None),
    area_minima: Optional[float] = Query(None),
    area_maxima: Optional[float] = Query(None),
    valor_min: Optional[float] = Query(None),
    valor_max: Optional[float] = Query(None),
    limit: int = Query(50, le=10000)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        where_clauses = []
        params = []

        # 🔹 CADASTRO SQL (busca parcial)
        if cadastro_sql:
            where_clauses.append("cadastro_sql LIKE %s")
            params.append(f"%{cadastro_sql}%")

        # 🔹 NÚMERO (busca exata, APENAS se preenchido)
        # ✅ IMPORTANTE: Só adiciona se numero foi explicitamente passado
        if numero is not None and numero != 0:
            where_clauses.append("numero = %s")
            params.append(numero)

        # 🔹 ENDEREÇO (busca parcial, case-insensitive)
        # ✅ NÚMERO É OPCIONAL PARA ENDEREÇO
        if endereco:
            where_clauses.append("nome_logradouro ILIKE %s")
            params.append(f"%{endereco}%")

        # 🔹 CEP (busca exata, NORMALIZADO - sem adicionar zeros)
        # ✅ NÚMERO É OPCIONAL PARA CEP
        if cep:
            cep_normalizado = normalize_cep(cep)
            if cep_normalizado:
                where_clauses.append("cep = %s")
                params.append(cep_normalizado)

        # 🔹 ÁREA MÍNIMA
        if area_minima is not None:
            where_clauses.append("area_construida >= %s")
            params.append(area_minima)

        # 🔹 ÁREA MÁXIMA
        if area_maxima is not None:
            where_clauses.append("area_construida <= %s")
            params.append(area_maxima)

        # 🔹 VALOR MÍNIMO
        if valor_min is not None:
            where_clauses.append("valor_transacao >= %s")
            params.append(valor_min)

        # 🔹 VALOR MÁXIMO
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
# ENDPOINTS IPTU
# ============================================================================

@app.get("/api/iptu/contribuinte/{numero_contribuinte}")
def get_iptu_by_contribuinte(numero_contribuinte: str):
    """
    Busca dados do IPTU por número de contribuinte.
    
    Aceita formatos:
    - 10155402756 (11 dígitos, formato transações)
    - 1015540275-6 (formato IPTU com hífen)
    """
    try:
        conn = get_iptu_connection()
        cursor = conn.cursor()
        
        numero_normalizado = normalize_contribuinte(numero_contribuinte)
        
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
                detail=f"IPTU não encontrado para contribuinte: {numero_contribuinte}"
            )
        
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
    """
    try:
        conn = get_iptu_connection()
        cursor = conn.cursor()
        
        cep_normalizado = normalize_cep(cep)
        
        if not cep_normalizado:
            raise HTTPException(
                status_code=400,
                detail=f"CEP inválido: {cep}"
            )
        
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
        for result in results:
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
            iptu_list.append(iptu_data)
        
        return {
            "cep": cep_normalizado,
            "total": len(iptu_list),
            "imoveis": iptu_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar IPTU por CEP: {str(e)}"
        )


@app.get("/api/iptu/endereco/{endereco}")
def get_iptu_by_endereco(endereco: str):
    """
    Busca todos os IPTUs para um determinado endereço.
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
            WHERE nome_logradouro ILIKE %s
            ORDER BY numero_imovel
            LIMIT 100
        """
        
        cursor.execute(query, (f"%{endereco}%",))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Nenhum IPTU encontrado para endereço: {endereco}"
            )
        
        iptu_list = []
        for result in results:
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
            iptu_list.append(iptu_data)
        
        return {
            "endereco": endereco,
            "total": len(iptu_list),
            "imoveis": iptu_list
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar IPTU por endereço: {str(e)}"
        )
