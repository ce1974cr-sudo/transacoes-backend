# API de Transações Imobiliárias - Backend

Backend em FastAPI para consulta de transações imobiliárias de São Paulo.

## Tecnologias

- **FastAPI**: Framework web moderno e rápido
- **PostgreSQL**: Banco de dados (hospedado no Aiven)
- **Uvicorn**: Servidor ASGI
- **psycopg2**: Driver PostgreSQL
- **Python**: 3.11 (recomendado para compatibilidade)

## Estrutura do Projeto

```
transacoes-backend/
├── app/
│   ├── __init__.py
│   └── main.py              # Aplicação FastAPI principal
├── requirements.txt         # Dependências Python
├── .python-version          # Versão do Python (3.11)
├── .env.example            # Exemplo de variáveis de ambiente
├── .gitignore              # Arquivos ignorados pelo Git
├── README.md               # Este arquivo
├── render.yaml             # Configuração automática do Render
└── test_api.py             # Script de testes locais
```

## Instalação Local

1. Clone o repositório:
```bash
git clone <seu-repositorio>
cd transacoes-backend
```

2. Crie um ambiente virtual com Python 3.11:
```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas credenciais
```

5. Execute o servidor:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

6. Acesse a documentação interativa:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Endpoints da API

### `GET /`
Informações sobre a API

### `GET /transacoes`
Busca transações com filtros opcionais

**Parâmetros de query:**
- `cadastro_sql` (string, opcional): Parte do número do cadastro SQL
- `numero` (integer, opcional): Número do imóvel
- `area_minima` (float, opcional): Área construída mínima em m²
- `area_maxima` (float, opcional): Área construída máxima em m²
- `limit` (integer, opcional): Limite de resultados (padrão: 1000, máximo: 5000)

**Resposta:**
```json
{
  "transacoes": [...],
  "grafico": [...],
  "total": 12345,
  "limite_aplicado": 1000
}
```

### `GET /stats`
Estatísticas gerais do banco de dados

**Resposta:**
```json
{
  "total_transacoes": 2536292,
  "periodo": {
    "data_minima": "1994-06-23",
    "data_maxima": "2025-10-07"
  },
  "valores": {
    "medio": 350000.50,
    "minimo": 1000.00,
    "maximo": 50000000.00
  },
  "areas": {
    "media": 150.25,
    "minima": 10.00,
    "maxima": 5000.00
  }
}
```

### `GET /health`
Health check do serviço

## Deploy no Render

### Opção 1: Via Interface Web (Recomendado)

1. Crie uma conta no [Render](https://render.com)

2. Crie um novo **Web Service**

3. Conecte seu repositório GitHub

4. Configure o serviço:
   - **Environment**: Python 3
   - **Python Version**: 3.11 (especificado no `.python-version`)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

5. Adicione a variável de ambiente:
   - **Key**: `DATABASE_URL`
   - **Value**: `postgres://avnadmin:AVNS_Bj2e6D_lxvVvyiApBgX@pg-b7344e5-ce1974cr-bedd.g.aivencloud.com:16026/defaultdb?sslmode=require`

6. Clique em **Create Web Service**

7. Aguarde o deploy e anote a URL gerada (ex: `https://seu-app.onrender.com`)

### Opção 2: Via render.yaml

O arquivo `render.yaml` está configurado para deploy automático. Basta conectar o repositório e o Render usará as configurações do arquivo.

## Versão do Python

**Importante**: Este projeto requer Python 3.11 devido à compatibilidade com `psycopg2-binary`.

O arquivo `.python-version` especifica a versão 3.11.0, que o Render usará automaticamente.

Se você encontrar erros relacionados a `_PyInterpreterState_Get`, confirme que está usando Python 3.11 e não 3.13.

## Variáveis de Ambiente

- `DATABASE_URL`: String de conexão PostgreSQL completa

## Desenvolvimento

Para adicionar novos endpoints, edite o arquivo `app/main.py`.

## Troubleshooting

### Erro: ImportError com psycopg2

Se aparecer erro `undefined symbol: _PyInterpreterState_Get`:

1. Verifique se está usando Python 3.11 (não 3.13)
2. Confirme que o arquivo `.python-version` existe
3. No Render, force rebuild do serviço

### Erro de conexão com banco de dados

1. Verifique se a variável `DATABASE_URL` está configurada corretamente
2. Confirme que o serviço PostgreSQL no Aiven está ativo (status: RUNNING)
3. Teste a conexão usando o endpoint `/health`

## Licença

MIT

