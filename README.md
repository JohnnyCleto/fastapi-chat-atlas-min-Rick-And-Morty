# FastAPI Chat (mínimo) + MongoDB Atlas

## Passos
1. Crie um cluster gratuito no **MongoDB Atlas** (https://cloud.mongodb.com).
2. Em **Database Access**, crie um usuário e senha.
3. Em **Network Access**, libere seu IP (ou 0.0.0.0/0 para testes).
4. Copie a **Connection String** (driver MongoDB, `mongodb+srv://...`).
5. Faça uma cópia de `.env.example` para `.env` e cole sua string na `MONGO_URL`.
6. Rode localmente:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abra: http://localhost:8000  (cliente simples)
Docs: http://localhost:8000/docs

## Endpoints principais
- **WebSocket**: `ws://localhost:8000/ws/{room}`
- **Histórico REST**: `GET /rooms/{room}/messages?limit=20`
- **Enviar (REST)**: `POST /rooms/{room}/messages`

> Observação: a primeira conexão cria a coleção automaticamente.
