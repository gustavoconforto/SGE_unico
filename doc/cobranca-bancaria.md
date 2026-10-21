# Cobrança bancária (boletos Bradesco)

Os itens **Remessas**, **Retornos** e **Boletos** do menu Financeiro cuidam
dos boletos de mensalidade registrados no Bradesco (cobrança no padrão
CNAB 400).

[← Voltar ao menu](sidebar.md)

## Como funciona a troca de arquivos com o banco

```
 Sistema                         Bradesco
 ───────                         ────────
 1. Gera remessa (.REM)  ──────▶  registra os boletos / baixas
                                   o responsável paga o boleto
 2. Importa retorno (.RET) ◀────  informa o que aconteceu
    → baixas lançadas sozinhas
```

1. A escola gera no sistema um **arquivo de remessa** e o envia pelo site ou
   aplicativo do banco.
2. O banco processa e, nos dias seguintes, disponibiliza **arquivos de
   retorno** com o que aconteceu com cada boleto: registrado, rejeitado, pago,
   vencido, baixado.
3. A escola baixa o retorno do banco e o importa no sistema. Os pagamentos
   são lançados automaticamente nas parcelas.

## Configuração bancária

Acesse pelo botão **Configuração bancária** na tela de Remessas. Precisa ser
preenchida antes da primeira remessa.

| Campo | Descrição |
|---|---|
| Código da empresa | Código do beneficiário informado pelo Bradesco (só números). |
| Razão social | Nome da escola como cadastrado no banco. |
| Carteira | Carteira de cobrança (2 dígitos; padrão 09). |
| Agência / Conta corrente / Dígito da conta | Sem o dígito na agência e na conta. |
| Multa (%) | Multa por atraso impressa no boleto (padrão 2%). |
| Juros ao mês (%) | Juros por atraso (padrão 1% ao mês, cobrados por dia). |
| Número da última remessa | Número da última remessa enviada ao banco; a próxima usa o seguinte. Só altere se o banco pedir. |

## Remessas

Lista das remessas já geradas, com número, data, quantidade de boletos, valor
total e quantidade de pedidos de baixa.

**Pesquisa:** número da remessa.

Em cada remessa:

- **Baixar arquivo**: faz o download do arquivo `.REM` (ex.: `00000123.REM`)
  para enviar ao banco.
- **Deletar**: só é possível enquanto o banco ainda não processou a remessa
  (nenhum boleto registrado). Use se gerou a remessa por engano. Os pedidos de
  baixa voltam para "Registrado" e, se era a última remessa, o número é
  reaproveitado.

### Gerar remessa

O botão **Gerar remessa** mostra as parcelas que podem receber boleto:

- parcelas **a receber** e **pendentes**, com saldo;
- que ainda **não têm boleto ativo** no banco.

**Pesquisa:** descrição da conta, responsável, nome ou matrícula do aluno.
**Filtro:** período de vencimento.

Para cada parcela aparecem o valor do boleto (saldo da parcela) e o desconto
de pontualidade. Parcelas com problema aparecem na lista, mas **não podem ser
enviadas** até serem corrigidas:

| Problema | Como resolver |
|---|---|
| Responsável sem CPF válido, endereço ou CEP | Corrija o cadastro em **Responsáveis**. |
| Vencimento já passou | O banco não aceita boleto vencido; receba de outra forma ou ajuste a parcela. |

Marque as parcelas desejadas (e os pedidos de baixa, se houver) e confirme.
O sistema gera a remessa e mostra quantos boletos e pedidos de baixa ela
contém.

**Valores do boleto:**

- valor = saldo da parcela;
- desconto de pontualidade = o valor definido no tipo de contrato da matrícula,
  válido até o vencimento (só para mensalidades);
- multa e juros = os da configuração bancária.

### Pedido de baixa

Quando uma parcela que já tem boleto registrado no banco é **cancelada** ou
**paga de outra forma** (ex.: em dinheiro na secretaria), o boleto precisa
ser retirado do banco, senão o responsável ainda pode pagá-lo.

Esses boletos aparecem na tela **Gerar remessa** como pedidos de baixa. Ao
incluí-los na remessa, ficam como **Baixa solicitada**. Só depois que o banco
confirmar a baixa (no retorno) a parcela pode receber um boleto novo — por
exemplo, pelo saldo restante de uma parcela paga em parte.

## Retornos

Lista dos arquivos de retorno já importados, com a quantidade de ocorrências,
quantas tiveram erro e o total pago.

**Pesquisa:** nome do arquivo.

### Importar retorno

Clique em **Importar retorno** e envie o arquivo `.RET` baixado do banco
(até 5 MB). O sistema:

- recusa arquivos de outra empresa (código diferente) e arquivos já
  importados;
- ignora linhas já processadas em retornos anteriores;
- processa cada linha separadamente: um erro numa linha não impede as demais.

Ao final aparece o resumo: quantas ocorrências foram **processadas**, quantas
tiveram **erro** e quantas foram **ignoradas**, e abre-se o detalhe do
retorno.

### O que cada ocorrência faz

| Ocorrência do banco | O que o sistema faz |
|---|---|
| 02 – Entrada confirmada | Boleto passa a **Registrado**. |
| 03 – Entrada rejeitada | Boleto **Rejeitado**; a parcela pode ir em nova remessa. |
| 06, 15, 17 – Liquidação | Lança a **baixa** na parcela (forma Boleto) com juros e desconto informados pelo banco. Boleto **Liquidado**. |
| 22, 40 – Pagamento cancelado / estornado | Exclui a baixa; a parcela volta a ficar pendente. |
| 09 – Baixado por decurso de prazo | Boleto expirou sem pagamento; parcela fica **Expirado** (continua devida). |
| 10 – Baixado pela agência | Confirma o pedido de baixa. Se a parcela ainda tiver saldo, o sistema avisa para enviá-la novamente. |
| 27 – Baixa rejeitada | O pedido de baixa foi recusado; o boleto volta a **Registrado**. |
| Outras | Guardadas como **ignoradas**. |

Linhas de boletos do sistema anterior também são marcadas como ignoradas.

### Ocorrências com erro

Algumas situações exigem conferência manual e ficam marcadas como **erro** no
detalhe do retorno:

- o valor pago é maior que o saldo da parcela (ex.: já foi baixada à mão);
- a parcela está cancelada;
- o boleto já tinha sido liquidado.

Nesses casos, verifique a parcela no **Balanço** e acerte as baixas
manualmente.

## Boletos

Lista de todos os boletos gerados, do mais recente para o mais antigo, com
nosso número, parcela, responsável, vencimento, valor e situação.

**Pesquisa:** nosso número, descrição da conta, responsável ou aluno.
**Filtros:** situação e período de vencimento.

| Situação do boleto | Significado |
|---|---|
| **Gerado** | Incluído numa remessa, ainda não confirmado pelo banco. |
| **Registrado** | Aceito pelo banco; pode ser pago. |
| **Baixa solicitada** | Pedido de baixa enviado, aguardando confirmação. |
| **Rejeitado** | O banco recusou o boleto. |
| **Liquidado** | Pago. |
| **Baixado por decurso de prazo** | Venceu e o banco o retirou sem pagamento. |
| **Baixado pela agência** | Retirado a pedido da escola. |
| **Pagamento estornado** | O pagamento foi cancelado pelo banco. |

Boletos **Gerado**, **Registrado** e **Baixa solicitada** são considerados
**ativos**: enquanto houver um, a parcela não recebe outro boleto.
