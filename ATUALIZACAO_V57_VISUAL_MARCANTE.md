# V57 — Nova direção visual

Esta versão aplica uma identidade com azul profundo, violeta e rosa aos destaques da clínica.

## O que mudou

- Nova composição da tela inicial, com abertura em degradê e agenda integrada ao destaque.
- Indicadores com cores fortes para pacientes, consultas, retornos e financeiro.
- Menu em azul profundo, com seleção em violeta.
- Fonte Manrope incluída no pacote e títulos com mais peso.
- Cards de acesso rápido, ícones e botões com mais destaque.
- Ficha do paciente com cabeçalho em degradê.
- Financeiro com cores por indicador e resumo em azul profundo.
- Agenda, formulários, login e telas de acesso acompanhando a nova identidade.
- Ajustes para computador e celular e atualização dos arquivos de cache para V57.

## Atualização no Coolify

Atualize os arquivos do aplicativo existente e faça o redeploy.
A porta continua sendo 8000. Preserve o volume /data e as variáveis DB_PATH,
UPLOAD_FOLDER e SECRET_KEY já configuradas no aplicativo atual.

Se a página permanecer com a aparência anterior, use Ctrl+F5 no computador.
No celular, feche e reabra o aplicativo.

A atualização é visual; as regras de negócio e os dados do aplicativo
permanecem no banco já configurado. Este ZIP não contém banco de pacientes,
fotos de atendimento ou dados de demonstração.

## Verificação

As 23 telas e as 11 abas do paciente foram renderizadas com dados fictícios
em uma base temporária. Foram conferidos os templates, os arquivos locais,
a fonte, a sintaxe de CSS/JavaScript e os controles preservados da V56.

A prévia que acompanha a resposta é demonstrativa. Não representa dados
da clínica nem substitui a conferência do aplicativo em um navegador real.
