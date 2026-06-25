# Eduarda Imbelloni Clínica Especializada - Luxo Clean V14

Sistema em Flask pronto para Coolify, com painel completo personalizado para a identidade da Eduarda Imbelloni.

## Login inicial

- Usuário: `admin`
- Senha: `admin123`
- Senha do financeiro: `eduarda2026`

Troque as senhas em **Configurações** depois do primeiro acesso.

## Porta no Coolify

Use a porta interna:

```txt
8000
```

## Volume persistente

Crie um volume persistente para não perder dados:

```txt
/data
```

O banco e uploads ficam em `/data`.

## Variáveis recomendadas no Coolify

```env
SECRET_KEY=coloque-uma-chave-grande-aqui
DB_PATH=/data/eduarda_imbelloni_premium_v4.db
UPLOAD_FOLDER=/data/uploads
FINANCE_PASSWORD=eduarda2026
ASAAS_ENV=sandbox
ASAAS_API_KEY=
```

Quando for usar Asaas real, altere:

```env
ASAAS_ENV=production
ASAAS_API_KEY=sua_chave_real
```

## Melhorias da versão Luxo Clean V14

- CRM de relacionamento com pacientes
- Controle de leads e possíveis pacientes
- Tarefas e retornos por paciente
- Pacientes para resgatar automaticamente, sem retorno há muito tempo
- Painel inicial com agenda do dia, tarefas do dia, leads e orçamentos abertos
- Menu inferior no celular, com cara de aplicativo
- PWA preparado: pode instalar no celular como app pelo navegador
- Catálogo inicial de procedimentos para agilizar orçamentos
- Cobranças vencidas visíveis no CRM com botão WhatsApp
- Cards operacionais para recepção trabalhar mais rápido
- Dashboard mais completo e mais comercial

## Já vinha da versão Luxo Clean V14

- Painel do paciente com resumo premium
- Linha do tempo do paciente
- Fotos do tratamento com upload
- Cadastro completo: CPF, e-mail e endereço
- Agenda com status: agendada, confirmada, compareceu, faltou e cancelada
- Botões de WhatsApp para lembrete e cobrança
- Financeiro com link Asaas salvo no lançamento
- Botões para gerar cobrança via Boleto ou Pix no Asaas
- Configurações da clínica dentro do sistema
- Senha do financeiro editável pelo painel
- Mensagens padrão de WhatsApp editáveis
- Usuários com permissões: administrador, recepção, profissional e financeiro
- Backup do banco e uploads pelo painel
- Registro de ações importantes
- Tema visual ajustado para a logo da Eduarda

## Observação sobre Asaas

O local da integração já está pronto. Sem a chave `ASAAS_API_KEY`, o sistema só avisa que falta configurar. Após colocar a chave no Coolify ou em Configurações, os botões de boleto/Pix tentam gerar a cobrança via Asaas.


## Visual Luxo Clean V14

Esta versão recebeu um redesenho visual com menu lateral, login premium, cards em vidro suave, cores da identidade Eduarda Imbelloni e polimento mobile/PWA.


## Atualização Visual Luxo Clean V14

Redesign visual completo com layout mais limpo, menu lateral refinado, cards mais leves, tela de login premium, tabelas mais elegantes e ajustes de responsividade. Mantém o mesmo banco/volume, sem apagar dados.


## Atualização Visual Luxo Clean V14

Redesign completo do layout para um visual mais limpo, sofisticado e alinhado à identidade visual da Eduarda Imbelloni Clínica Especializada. Inclui sidebar compacta, dashboard premium, cards refinados, tabelas mais modernas, login elegante e ajustes de responsividade.


## Atualização Visual Luxo Clean V14

Refino visual geral do sistema com foco em leveza, sofisticação e aspecto de clínica premium. Nova sidebar clara, dashboard mais enxuto, formulários e tabelas mais elegantes, login minimalista e hierarquia visual mais fina.


## Atualização Visual Luxo Clean V14

Home simplificada com menos informação, ícones restaurados no menu e nos atalhos, e visual mais leve.


## Atualização Visual Luxo Clean V14

Topo da home simplificado, com remoção do texto grande e inclusão de mais cor nos elementos do dashboard.


## Atualização Visual Luxo Clean V14

Mensagem da Home removida, reforço de cores no dashboard e inclusão de microinterações/animações suaves.


## Atualização Visual Luxo Clean V14

Refino visual com mais cor e um pacote maior de microanimações no dashboard, botões, cards, menu e listas.


## Atualização App Premium V14

Versão com mais cor e animações: transição de páginas, barra de carregamento, entrada dos cards, hover animado, modais mais suaves e microinterações em botões, menus, tabelas e abas.


## V14 - Documentos e Assinatura

Adicionada aba Documentos no painel do paciente, com contrato, termo de consentimento, termo de uso de imagem, assinatura digital na tela e impressão/PDF.


## V14 - Assinatura manual e digital

A aba Documentos agora permite escolher entre imprimir o modelo para assinatura em mãos ou abrir a assinatura digital na tela.
