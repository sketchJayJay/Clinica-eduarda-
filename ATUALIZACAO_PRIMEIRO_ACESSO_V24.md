# Atualização V24 - Primeiro acesso personalizado

## O que mudou
- Removido o primeiro acesso fixo `admin/admin123`.
- Quando abrir o sistema pela primeira vez e ainda não existir usuário, aparece uma tela de configuração inicial.
- A clínica escolhe:
  - usuário de entrada do sistema;
  - senha de entrada;
  - senha separada do financeiro.
- Depois disso, o sistema passa a abrir diretamente na tela normal de login.
- A senha do financeiro escolhida passa a valer na proteção do módulo Financeiro.

## Observação Coolify
Se a variável `FINANCE_PASSWORD` estiver configurada no Coolify, ela continua tendo prioridade. Para usar a senha escolhida no sistema, deixe `FINANCE_PASSWORD`/`FINANCE_PASS` vazias ou remova essas variáveis.
