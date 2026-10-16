# V56 — Novo layout da clínica

Interface renovada em tons de café, marfim e verde sálvia, mantendo a identidade de Eduarda Imbelloni.

## O que mudou

- Menu lateral para computador, com atendimento e gestão organizados por área.
- Navegação inferior para celular e menu completo em “Mais”.
- Página inicial com agenda do dia, indicadores, acesso rápido e lembretes.
- Lista de pacientes com busca em destaque; no celular, os registros viram cartões.
- Ficha do paciente com nova hierarquia visual, abas que deslizam no celular e ações organizadas.
- Financeiro com resumo legível, filtros recolhíveis e cartões de lançamentos no celular.
- Agenda com aparência renovada e legenda de status.
- Odontograma em fundo claro, com melhor aproveitamento do espaço e menu ajustado à largura da tela.
- Tela de login e acesso ao financeiro renovadas, incluindo botão para mostrar/ocultar a senha.
- Estilos, ícones e scripts da interface incluídos no pacote, sem depender de CDN para essas telas.

## Atualizar no Coolify

1. Atualize o código do aplicativo já existente com o conteúdo desta pasta, no mesmo nível do Dockerfile.
2. Mantenha o volume atual montado em /data e preserve as variáveis DB_PATH, UPLOAD_FOLDER e SECRET_KEY já usadas no seu aplicativo. Não é necessário criar outro banco para trocar o layout.
3. Faça o redeploy do aplicativo existente. A porta continua sendo 8000.
4. Reabra a página. Se uma aba antiga continuar mostrando o visual anterior, atualize com Ctrl+F5; no celular, feche e reabra o aplicativo.

O pacote contém código e arquivos da interface. Ele não contém banco de pacientes, fotos de atendimento ou dados de teste.

## Validação realizada

- Renderização dos 33 templates sem erros.
- Login, primeiro acesso e bloqueio/desbloqueio financeiro.
- Cadastro, busca e edição de pacientes.
- As 11 abas do paciente.
- Criação, edição e exclusão de agendamento, mantendo a data e o horário.
- Criação de lançamentos pagos e pendentes, filtros e resumo financeiro com dados fictícios.
- Lembretes de aniversário/cobrança e ações v55 preservadas.
- Exportações PDF e Excel.
- Recursos locais e sintaxe de CSS e JavaScript.
- Persistência e reabertura de registro no odontograma.

As regras de negócio em Python e as configurações de implantação foram preservadas; a versão exibida foi atualizada para V56. A conferência visual e de gestos em navegador real não pôde ser feita neste ambiente. Os testes usaram uma base temporária, separada do pacote.
