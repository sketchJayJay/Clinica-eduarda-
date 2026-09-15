# Correção V43 - Build no Coolify

## O que mudou
- Requirements foram travados em versões estáveis.
- ReportLab foi fixado em versão 4.2.5 para evitar quebra pegando versão nova automaticamente.
- Dockerfile agora atualiza pip/setuptools/wheel antes de instalar dependências.
- Timeout do pip aumentado para 120 segundos.

## Motivo
O log do Coolify mostrou falha durante a etapa de instalação das dependências Python.
