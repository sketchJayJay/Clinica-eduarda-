# Eduarda Imbelloni Clínica Especializada - Luxo Clean V36

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

## Melhorias da versão Luxo Clean V36

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

## Já vinha da versão Luxo Clean V36

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


## Visual Luxo Clean V36

Esta versão recebeu um redesenho visual com menu lateral, login premium, cards em vidro suave, cores da identidade Eduarda Imbelloni e polimento mobile/PWA.


## Atualização Visual Luxo Clean V36

Redesign visual completo com layout mais limpo, menu lateral refinado, cards mais leves, tela de login premium, tabelas mais elegantes e ajustes de responsividade. Mantém o mesmo banco/volume, sem apagar dados.


## Atualização Visual Luxo Clean V36

Redesign completo do layout para um visual mais limpo, sofisticado e alinhado à identidade visual da Eduarda Imbelloni Clínica Especializada. Inclui sidebar compacta, dashboard premium, cards refinados, tabelas mais modernas, login elegante e ajustes de responsividade.


## Atualização Visual Luxo Clean V36

Refino visual geral do sistema com foco em leveza, sofisticação e aspecto de clínica premium. Nova sidebar clara, dashboard mais enxuto, formulários e tabelas mais elegantes, login minimalista e hierarquia visual mais fina.


## Atualização Visual Luxo Clean V36

Home simplificada com menos informação, ícones restaurados no menu e nos atalhos, e visual mais leve.


## Atualização Visual Luxo Clean V36

Topo da home simplificado, com remoção do texto grande e inclusão de mais cor nos elementos do dashboard.


## Atualização Visual Luxo Clean V36

Mensagem da Home removida, reforço de cores no dashboard e inclusão de microinterações/animações suaves.


## Atualização Visual Luxo Clean V36

Refino visual com mais cor e um pacote maior de microanimações no dashboard, botões, cards, menu e listas.


## Atualização App Premium V36

Versão com mais cor e animações: transição de páginas, barra de carregamento, entrada dos cards, hover animado, modais mais suaves e microinterações em botões, menus, tabelas e abas.


## V36 - Documentos e Assinatura

Adicionada aba Documentos no painel do paciente, com contrato, termo de consentimento, termo de uso de imagem, assinatura digital na tela e impressão/PDF.


## V36 - Assinatura manual e digital

A aba Documentos agora permite escolher entre imprimir o modelo para assinatura em mãos ou abrir a assinatura digital na tela.


## V36 - Correção do menu inferior no mobile

Ajustado o espaçamento do conteúdo para o dock inferior do celular não cobrir botões e formulários, especialmente na aba Documentos.


## V36 - Correção forte do dock inferior

O menu inferior agora só aparece no celular e não fica mais por cima dos botões em telas maiores. Também foi adicionado espaço extra no final da aba Documentos.


## V36 - Nome clicável na agenda

Na agenda, o nome do paciente dentro do evento agora abre diretamente o painel do paciente. Clicar no restante do evento continua abrindo a edição do agendamento.


## V36 - Contrato de fidelidade

Adicionado modelo de contrato de fidelidade/tratamento completo na aba Documentos, com valor total do tratamento, condições de pagamento e cláusula de multa por quebra de contrato.


## V36 - Percentual da multa

Adicionados campos próprios no contrato de fidelidade para percentual da multa, base de cálculo da multa e valor fixo opcional.


## V36 - Orçamentos

Adicionadas opções de editar/excluir orçamento e explicação clara: aprovar orçamento envia para Plano/Ficha do paciente, não para o financeiro. Para cobrança, usar Nova cobrança no financeiro.


## V36 - Vínculo financeiro com Plano/Ficha

Agora lançamentos financeiros podem ser vinculados a itens do Plano/Ficha, abatendo recebidos e saldo diretamente na ficha do paciente.


## V36 - Correção editar financeiro

Corrigida queda ao clicar em Editar no financeiro e ajustado salvamento de lançamentos vinculados ao Plano/Ficha.


## V36 - Marcar pago no financeiro

Renomeado o botão Baixar para Marcar pago e ajustadas ações da tabela financeira: pagamento parcial para pendentes e ver pagamentos para já pagos.


## V36 - Primeiro acesso personalizado

Agora, na primeira abertura sem usuário cadastrado, o sistema pede para a clínica escolher usuário, senha de entrada e senha separada do financeiro. Removido o primeiro acesso fixo admin/admin123.


## V36 - Primeiro acesso forçado quando existe admin padrão

Se o banco tiver apenas o usuário padrão `admin`, o sistema mostra a tela de primeiro acesso para a clínica escolher usuário, senha de entrada e senha do financeiro.


## V36 - Plano completo, parcelas e baixa pela ficha

Agora a ficha permite lançar pagamento do tratamento completo, criar parcelas com vencimento, dar baixa com valor/data real e aprovar todos os orçamentos para o plano.


## V36 - Alertas de cobrança e aniversários

A Home mostra cobranças vencendo hoje/vencidas, com WhatsApp pronto, marcar como enviado e acesso para dar baixa. Aniversários continuam com lembrete e WhatsApp.


## V36 - Excluir item do plano

Adicionado botão para excluir item do Plano/Ficha. Lançamentos financeiros vinculados são preservados e o orçamento de origem volta para aberto.


## V36 - Linha do tempo clínica separada

Adicionada linha do tempo clínica separada para registrar manutenções, procedimentos realizados e evoluções por data, sem misturar com financeiro.


## V36 - Excluir paciente

Adicionado botão Excluir paciente no painel do paciente, com confirmação e preservação dos lançamentos financeiros.


## V36 - Ficha de evolução detalhada

Nova aba Evolução clínica com descrição completa do atendimento, materiais, intercorrências, conduta, retorno, visualização e impressão.


## V36 - Agenda rápida e boleto

A agenda aceita paciente novo sem cadastro prévio, criando cadastro básico automaticamente. A ficha ganhou botão Novo boleto/parcela e a forma de pagamento Boleto bancário.


## V36 - Correção clique na agenda

Corrigido clique no nome do paciente dentro da agenda: abre a ficha diretamente e evita modal escuro/travado.


## V36 - Busca por paciente na agenda

O agendamento agora usa busca por nome no lugar do select de paciente, deixando o fluxo mais rápido.


## V36 - Autocomplete na agenda

Busca de paciente na agenda ganhou autocomplete visual com nome e telefone, no Criar rápido e no modal de agendamento.


## V36 - Agenda limpa

Removido painel lateral da agenda, deixando o calendário mais largo e os eventos mais compactos. O agendamento passa a ser feito pelo botão superior ou clicando em um horário vazio.
