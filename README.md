# Sistema Eduarda Imbelloni - Clínica Especializada

Sistema web pronto para clínica, no mesmo padrão do projeto New Clínica, adaptado para Eduarda Imbelloni.

## Módulos inclusos
- Dashboard
- Cadastro e busca de pacientes
- Agenda com confirmação via WhatsApp
- Anamnese digital
- Planos de tratamento
- Ortodontia com manutenção, pagamento e próxima consulta
- Financeiro com pendências, recibo e marcação de pagamento
- Profissionais e repasse mensal
- Lugar preparado para integração Asaas: botão "Emitir boleto"

## Rodar localmente
```bash
pip install -r requirements.txt
python app.py
```
Acesse: http://localhost:8080

## Publicar no Coolify
1. Suba esta pasta para um repositório no GitHub.
2. No Coolify, crie um novo app pelo repositório.
3. Use Dockerfile.
4. Configure volume persistente:
   - Caminho no container: `/app/instance`
5. Variáveis de ambiente:
   - `SECRET_KEY=uma_chave_segura`
   - `ASAAS_API_KEY=` deixe vazio até vincular o Asaas
   - `ASAAS_ENV=sandbox` ou `production`
   - `CLINIC_WHATSAPP=55DDDNUMERO`

## Asaas
O lugar já está pronto no financeiro. Quando configurar a API Key real do Asaas, o botão "Emitir boleto" passa a tentar criar cobrança.

Antes de usar em produção, confirme na conta Asaas:
- API Key correta
- Ambiente sandbox ou produção
- Dados do paciente com CPF/CNPJ válido
- Tipo de cobrança desejado: boleto, Pix ou cartão

