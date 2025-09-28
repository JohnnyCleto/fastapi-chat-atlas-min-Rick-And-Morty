# Chat Multiverso – FastAPI + MongoDB Atlas

> Um chat em tempo real inspirado em **Rick & Morty**, onde você escolhe seu personagem e entra em salas públicas ou privadas. Salve seu perfil localmente, converse com outros usuários e explore múltiplos universos!

---

## 🌟 Funcionalidades do Projeto

* Escolha seu **personagem favorito do Rick & Morty** como avatar e apelido.
* Criação de **salas públicas e privadas** com senha.
* **Mensagens em tempo real** usando WebSockets.
* **Histórico de mensagens** carregado via REST.
* Perfil salvo localmente para fácil reconexão.
* Interface responsiva, dark mode e bolhas de chat customizadas.

---

## 📸 Como ficou o projeto

![Chat Multiverso Rick & Morty](./screenshot.png)
---

## ⚡ Tecnologias Utilizadas

* **Back-end:** FastAPI
* **Banco de dados:** MongoDB Atlas
* **Front-end:** HTML, CSS e JavaScript (vanilla)
* **Comunicação em tempo real:** WebSockets

---

## 🚀 Passos para rodar localmente

1. Crie um cluster gratuito no [MongoDB Atlas](https://cloud.mongodb.com).
2. Em **Database Access**, crie um usuário e senha.
3. Em **Network Access**, libere seu IP (ou `0.0.0.0/0` para testes).
4. Copie a **Connection String** (`mongodb+srv://...`).
5. Faça uma cópia de `.env.example` para `.env` e cole sua string na variável:

```env
MONGO_URL=mongodb+srv://<usuario>:<senha>@cluster0.mongodb.net/?retryWrites=true&w=majority
```

6. Crie e ative o ambiente virtual:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

7. Instale dependências e rode o servidor:

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

8. Abra o navegador: [http://localhost:8000](http://localhost:8000)

   * Cliente web simples
   * Docs da API: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔗 Endpoints principais

| Tipo      | Endpoint                          | Descrição                         |
| --------- | --------------------------------- | --------------------------------- |
| WebSocket | `ws://localhost:8000/ws/{room}`   | Conexão em tempo real em uma sala |
| REST GET  | `/rooms/{room}/messages?limit=20` | Histórico das últimas mensagens   |
| REST POST | `/rooms/{room}/messages`          | Envia mensagem (opcional)         |

> A primeira conexão cria automaticamente a coleção da sala no MongoDB.

---

## 📝 Observações

* O **perfil** é salvo localmente no navegador (`localStorage`).
* Você pode **entrar em salas públicas** ou **criar salas privadas** com senha.
* Ideal para experimentos, aprendizado de WebSockets e MongoDB.
