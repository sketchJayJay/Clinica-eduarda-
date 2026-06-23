# Deploy VPS / Coolify

Este projeto foi preparado principalmente para Coolify.

## Coolify

- Build Pack: Dockerfile
- Porta interna: `8000`
- Volume persistente: `/data`

Variáveis:

```env
SECRET_KEY=troque_essa_chave_por_uma_bem_grande
DB_PATH=/data/eduarda_imbelloni_premium.db
UPLOAD_FOLDER=/data/uploads
FINANCE_PASSWORD=eduarda2026
ASAAS_ENV=sandbox
ASAAS_API_KEY=
```

## VPS manual

Use o `docker-compose.yml` da raiz ou da pasta `deploy_vps`.
