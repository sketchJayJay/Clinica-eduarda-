# Eduarda Imbelloni Clínica Especializada - Sistema Completo

Sistema baseado no painel completo da Eduarda Imbelloni, personalizado para a identidade visual da Eduarda Imbelloni.

## Módulos inclusos

- Dashboard/painel principal
- Cadastro e busca de pacientes
- Painel individual do paciente
- Agenda
- Anamnese
- Plano/ficha clínica
- Odontograma
- Orçamentos e impressões
- Financeiro completo
- Caixa
- Categorias
- Profissionais
- Repasses
- Aniversários com atalho para WhatsApp
- Botão preparado para cobrança Asaas no financeiro

## Coolify

Use Dockerfile ou Docker Compose. Porta interna: `5000`.

Variáveis recomendadas:

```env
FLASK_ENV=production
SECRET_KEY=troque-por-uma-chave-grande
DB_PATH=/data/eduarda_imbelloni.db
CLINIC_NAME=Eduarda Imbelloni Clínica Especializada
FINANCE_PASSWORD=eduarda2026
ASAAS_API_KEY=
ASAAS_ENV=sandbox
```

Volume persistente:

```txt
/data
```

## Acesso inicial

Usuário: `admin`
Senha: `admin123`

Depois altere em Configurações.

## Asaas

O botão **Asaas** aparece em lançamentos de entrada pendentes. Sem `ASAAS_API_KEY`, ele avisa que falta configurar. Com a chave configurada, tenta gerar uma cobrança do tipo boleto no Asaas.
