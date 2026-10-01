---
id: ARCH_2026-09-29_timeout_progresso
ciclo: 2026-09-29_timeout_progresso
data_criacao: 2026-09-29
autor: Antigravity (Gemini 3.8 Flash)
prd_referencia: PRD_2026-09-29_timeout_progresso
status: concluido
---

# Arquitetura & Contratos Técnicos: Gestão de Timeout e Progresso

## 1. Módulos e Arquivos Impactados
| Módulo / Arquivo | Ação | Responsabilidade |
| :--- | :---: | :--- |
| `tabulador/static/app.js` | Modificar | Tratar condicionalmente timeout para operações assíncronas com barra de progresso |
| `tabulador/src/llm.py` | Modificar | Elevar timeout do client OpenAI para acomodar lotes pesados |

## 2. Contratos & Assinaturas
### Frontend (`static/app.js`)
```javascript
// Contrato de timeout na função api()
const timeoutMs = opts.timeout ?? (progresso ? 0 : 240000);
// Quando timeoutMs === 0, não registrar setTimeout no AbortController
```

### Backend (`src/llm.py`)
```python
# Timeout configurável com fallback para 240 segundos
timeout = int(os.getenv("TABULADOR_LLM_TIMEOUT", "240"))
```

## 3. Diagrama de Sequência
```mermaid
sequenceDiagram
    autonumber
    actor User as Operador
    participant UI as Browser (app.js)
    participant Flask as Backend (app.py)
    participant LLM as Modelo (AGY / Gemini Pro)

    User->>UI: Clica em "Reclassificar Q35"
    UI->>Flask: POST /api/classificar (progresso=true, timeoutMs=0)
    loop A cada lote de 30 respostas (~33s)
        Flask->>LLM: Invocação de lote
        LLM-->>Flask: Retorno estruturado
        UI->>Flask: GET /api/progresso
        Flask-->>UI: Retorna progresso atualizado (ex: 30/3766)
        UI->>User: Atualiza barra visual e contadores
    end
    Flask-->>UI: Resposta final HTTP 200 OK
    UI-->>User: Exibe notificação de conclusão
```
