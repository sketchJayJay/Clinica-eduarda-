# Correção V51 - Financeiro não abria

## Corrigido
- A tela do financeiro podia cair ao abrir por causa de uma variável `today` enviada sem definição na rota de lançamentos.
- Corrigido para usar a data atual corretamente.
- Mantida a lógica do financeiro mensal da V50.

## Importante
Essa versão mantém:
- orçamento fora do financeiro;
- plano aprovado fora do financeiro;
- entrada financeira somente quando houver cobrança/pagamento.
