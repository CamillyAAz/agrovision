# AgroVision AI - Monitoramento de Tráfego com Agente IA

Evolução do projeto AgroVision para monitoramento de tráfego com câmera pública, integração Ollama para IA local, e agente de IA para análise operacional.

## 1) Requisitos

- Python 3.10+ (64 bits)
- Ollama instalado e rodando
- VS Code + extensões Python e Pylance
- Terminal PowerShell (Windows) ou zsh/bash (Linux/macOS)

## 2) Estrutura do projeto

```text
agrovision_ia/
├── .env
├── .venv/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── detections.db
├── yolo11n.pt
├── services/
│   ├── __init__.py
│   ├── config.py
│   ├── schemas.py
│   ├── event_repository.py
│   ├── capture_store.py
│   ├── video_monitor.py
│   ├── ollama_client.py
│   └── monitoring_agent.py
├── static/
│   ├── style.css
│   ├── dashboard.js
│   └── captures/
├── templates/
│   └── index.html
├── uploads/
├── models/
├── runs/
└── dataset_agro/
    ├── images/
    │   ├── train/
    │   └── val/
    ├── labels/
    │   ├── train/
    │   └── val/
    └── data.yaml
```

## 3) Instalar Ollama

### Windows
1. Baixar de https://ollama.com/download
2. Instalar e executar
3. Baixar modelo: `ollama pull llama3`

### Linux/macOS
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3
```

Verificar: `ollama list` e testar API em http://127.0.0.1:11434/api/tags

## 4) Criar e ativar ambiente virtual

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Se houver bloqueio de script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## 5) Instalar dependências

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 6) Configurar .env

O arquivo `.env` já está criado com configurações padrão. Verificar:

```
OLLAMA_URL=http://127.0.0.1:11434/api/chat
OLLAMA_MODEL=llama3
CAMERA_SOURCE=https://wzmedia.dot.ca.gov/D11/C214_SB_5_at_Via_De_San_Ysidro.stream/playlist.m3u8
```

## 7) Rodar a aplicação

```bash
python -m uvicorn app:app --reload
```

Acesse:

- **Dashboard**: http://127.0.0.1:8000
- **Health check**: http://127.0.0.1:8000/health
- **Camera status**: http://127.0.0.1:8000/camera/status
- **Agent status**: http://127.0.0.1:8000/agent/status
- **Events**: http://127.0.0.1:8000/events

## 8) Testar funcionalidades

1. **Câmera**: Verificar stream em `/camera/status`
2. **YOLO**: Eventos aparecem em `/events` quando objetos são detectados
3. **Agente**: No dashboard, perguntar "Leia os eventos recentes, avalie o risco e recomende a próxima ação"

## 9) YOLO11

Por padrão usa `yolo11n.pt` (baixado automaticamente).

Para trocar modelo, editar `.env`:

```
MODEL_PATH=yolov8n.pt
```

## 10) Troubleshooting

- **Ollama não responde**: Verificar se está rodando (`ollama serve`)
- **Câmera não conecta**: Verificar internet e URL em `.env`
- **Modelo não carrega**: Verificar se `yolo11n.pt` existe
- **Chat não funciona**: Verificar `/agent/status` para contexto
```

## 7) Fluxo de teste em aula

1. Subir o app com Uvicorn.
2. Abrir a página principal no navegador.
3. Verificar o stream da câmera.
4. Observar os eventos detectados na tabela.
5. Abrir as evidências salvas em `static/captures/`.
