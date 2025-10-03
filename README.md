# Chat Multiverso – FastAPI + MongoDB + Redis

> Um chat em tempo real inspirado em **Rick & Morty**, onde você escolhe seu personagem e entra em salas públicas ou privadas. Agora com **Redis** para cache, presença online, rate limit e distribuição de mensagens em tempo real.

---

## 🌟 Funcionalidades do Projeto

* Escolha seu **personagem favorito do Rick & Morty** como avatar e apelido.
* Criação de **salas públicas e privadas** com senha.
* **Mensagens em tempo real** usando WebSockets.
* **Histórico de mensagens** carregado via REST + cache no Redis.
* Perfil salvo localmente para fácil reconexão.
* **Presença online** dos usuários em cada sala via Redis (SET + TTL).
* **Rate limiting** para controlar envio excessivo de mensagens.
* **Pub/Sub do Redis** para distribuição de mensagens em tempo real.
---

## 📸 Como ficou o projeto

![Chat Multiverso Rick & Morty](./screenshot.png)

---

## ⚡ Tecnologias Utilizadas

* **Back-end:** FastAPI
* **Banco de dados:** MongoDB Atlas (persistência durável)
* **Armazenamento quente:** Redis (cache, Pub/Sub, rate limit, presença)
* **Front-end:** HTML, CSS e JavaScript (vanilla)
* **Comunicação em tempo real:** WebSockets
* **Containerização:** Docker Compose

---

## 🚀 Passos para rodar localmente

### 1. Pré-requisitos

* Python 3.10+
* Docker e Docker Compose instalados

### 2. Variáveis de ambiente

Copie o arquivo `.env.example` para `.env` e configure:

```env
MONGO_URL=mongodb+srv://<usuario>:<senha>@cluster0.mongodb.net/?retryWrites=true&w=majority
REDIS_URL=redis://redis:6379/0
```

### 3. Rodar via Docker Compose

```bash
docker-compose up --build
```

Isso irá subir:

* **FastAPI** (porta 8000)
* **MongoDB Atlas** (externo, configure no .env)
* **Redis** (porta 6379)

### 4. Acessar aplicação

* Cliente web: [http://localhost:8000](http://localhost:8000)
* Documentação da API: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🔗 Endpoints principais

| Tipo      | Endpoint                          | Descrição                                    |
| --------- | --------------------------------- | -------------------------------------------- |
| WebSocket | `ws://localhost:8000/ws/{room}`   | Conexão em tempo real em uma sala            |
| REST GET  | `/rooms/{room}/messages?limit=20` | Histórico (MongoDB + cache Redis)            |
| REST POST | `/rooms/{room}/messages`          | Envia mensagem (opcional)                    |
| Redis     | `chat:{room}:recent`              | LIST com últimas 50 mensagens                |
| Redis     | `chat:{room}:online`              | SET com usuários ativos (TTL para expiração) |
| Redis     | Pub/Sub `chat:{room}`             | Canal de mensagens em tempo real             |

---

## 📝 Observações

* **Redis** mantém em memória o histórico recente (últimas 50 mensagens por sala).
* **MongoDB** garante persistência completa de todas as mensagens.
* **Rate limiting** é implementado com chaves expiráveis em Redis.
* **Presença online** é gerenciada por TTL em chaves Redis para saber quem está conectado.
