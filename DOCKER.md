# 🐳 GUIA DE DESENVOLVIMENTO: SUPPORTE AGENTS 

Este guia orienta o desenvolvedor a subir o ecossistema completo da aplicação localmente usando Docker.
A arquitetura é composta por microsserviços orquestrados por um Gateway (Nginx).

---

## 🏗️ Arquitetura do Sistema

O sistema roda em containers isolados na rede `internal-net` e expõe apenas a porta 80 via Nginx.

1. **Gateway (Nginx):** Porta de entrada (`http://localhost`). Redireciona tráfego HTTP e WebSocket.
2. **Frontend (React):** Serve a interface visual. Acessado internamente pelo Gateway.
3. **Backend Qualidade (FastAPI):** Agentes de IA (Planner, Writer, Critic) e RAG. Porta interna 8000.
4. **Backend Robôs (Flask):** Geradores de documentos e automações. Porta interna 5000.

---

## 📋 1. Pré-requisitos

- **Docker** e **Docker Compose** instalados.
- **Git** instalado.
- **Chaves de API** 

---

## ⚙️ 2. Configuração de Variáveis de Ambiente (.env)

> [!IMPORTANT]
>⚠️ **ATENÇÃO:** Não existe um `.env` global na raiz para a aplicação. Cada backend possui sua própria configuração.
Você deve criar os arquivos `.env` baseados nos exemplos fornecidos (`.env.example`).


Copie o conteúdo de `.env.example` de cada projeto e os deixe nos seus determinados. Configure as chaves necessárias e é só fazer o deploy!

---

## 🚀 3. Subindo o Ambiente

Na raiz do projeto (onde está o `docker-compose.yml`), execute:

```bash
docker-compose up --build -d
```

- `--build`: Garante que as imagens (Python e Node) sejam recompiladas.
- `-d`: Roda em segundo plano (detached mode).

Para verificar se todos os containers subiram:
```bash
docker-compose ps
```
Você deve ver 4 serviços com status "Up": `supporte_gateway`, `supporte_frontend`, `supporte_qualidade_api`, `supporte_robos_api`.

---

## 🔌 4. Acessando a Aplicação (Endpoints)

Toda a comunicação passa pelo **Nginx Gateway** na porta 80. Não tente acessar as portas 8000 ou 5000 diretamente, pois elas estão fechadas na rede interna.

### 🖥️ Frontend (Aplicação Principal)
Acesse: `http://localhost/`

### 🧠 Backend Qualidade (FastAPI)
- **Documentação (Swagger):** `http://localhost/api/qualidade/docs`
- **Endpoint Chat (WebSocket):** `ws://localhost/api/qualidade/ws/chat/{session_id}`
  *(Nota: O Nginx gerencia o upgrade de conexão automaticamente)*

### 🤖 Backend Robôs (Flask)
- **Status/Home:** `http://localhost/api/robos/`
- **API Gerador:** `http://localhost/api/robos/gerar-doc` (Exemplo)

---

## 🔍 5. Monitoramento e Logs

Como os containers rodam em background, use os logs para debugar os Agentes e o fluxo de geração.

### Ver logs de todos os serviços (stream):
```bash
docker-compose logs -f
```

### Ver logs de um serviço específico:

**1. Logs dos Agentes (Planner, Writer, Critic):**
Essenciais para ver o "pensamento" da IA.
```bash
docker-compose logs -f backend-qualidade
```
*Procure por:* `[Planner]`, `[Writer]`, ou JSONs de eventos.

**2. Logs do Nginx (Erros de Roteamento):**
Se der erro 404 ou 502 Bad Gateway.
```bash
docker-compose logs -f nginx-gateway
```

**3. Logs do Frontend (Build/Nginx interno):**
```bash
docker-compose logs -f frontend
```

---

## 🔄 6. Fluxo de Desenvolvimento (Workflow)

### Para alterar código no Backend (Python):
Como o `docker-compose.yml` atual copia o código na hora do build (COPY), para refletir alterações de lógica (`.py`), você precisa reconstruir o container específico:

```bash
# Exemplo: Alterou o agent_1_planner.py
docker-compose up --build -d backend-qualidade
```

### Para alterar código no Frontend (React):
O container atual faz o build de produção (Nginx). Para ver alterações:
1. Altere o código (`.tsx`, `.css`).
2. Rode `docker-compose up --build -d frontend`.

---