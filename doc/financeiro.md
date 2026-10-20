# Financeiro

Contas a receber e a pagar, parcelas e o registro dos pagamentos (baixas).
Para boletos, remessas e retornos, veja
[cobranca-bancaria.md](cobranca-bancaria.md).

[← Voltar ao menu](sidebar.md)

## Como o financeiro é organizado

```
Categoria ──▶ Conta (contrato) ──▶ Parcelas ──▶ Baixas (pagamentos)
```

- **Conta**: o contrato ou documento (ex.: "Mensalidade 2027 – João",
  "Aluguel março"). É **a receber** (dinheiro que entra) ou **a pagar**
  (dinheiro que sai).
- **Parcela**: cada vencimento da conta, com data e valor.
- **Baixa**: o registro de que uma parcela foi paga, total ou parcialmente.

### Situação das parcelas

| Situação | Significado |
|---|---|
| **Aberto** | Nada pago ainda. |
| **Parcial** | Parte do valor foi paga; ainda há saldo. |
| **Quitado** | Pago por completo. |
| **Cancelado** | Não é mais devido (ex.: matrícula cancelada). |
| **Expirado** | O banco baixou o boleto por falta de pagamento. **A parcela continua devida.** |

Parcelas abertas, parciais e expiradas contam como **pendentes**. Uma parcela
pendente com vencimento antes de hoje aparece como **Vencida**, com a linha em
vermelho.

A situação muda **sozinha** conforme as baixas são lançadas ou excluídas;
não é preciso alterá-la à mão.

### Situação das contas

Calculada a partir das parcelas: **Vencida** (tem parcela vencida),
**Em aberto** (tem parcela pendente), **Quitada** (tudo pago),
**Cancelada** (todas canceladas) ou **Sem parcelas**.

## Categorias financeiras

Classificação das contas, por exemplo Mensalidade, Material didático, Aluguel,
Energia, Salários.

**Pesquisa:** nome. **Filtro:** natureza (A receber / A pagar).

| Campo | Descrição |
|---|---|
| Nome | Não pode repetir. |
| Natureza | **A receber** ou **A pagar**. Só pode ser trocada enquanto a categoria não tiver contas. |

Contas a receber só aceitam categorias "A receber", e contas a pagar só
"A pagar". A categoria **Mensalidade** é criada automaticamente na primeira
matrícula, se ainda não existir.

## Fornecedores

Empresas e pessoas para quem a escola paga contas.

**Pesquisa:** nome, CPF/CNPJ, telefone, e-mail ou observações.

| Campo | Descrição |
|---|---|
| Nome | |
| CPF/CNPJ | Somente números: 11 dígitos (CPF) ou 14 (CNPJ). Opcional, mas não pode repetir. |
| Telefone, E-mail, Observações | |

Um fornecedor com contas lançadas não pode ser excluído.

## Contratos a receber

Contas que a escola tem a receber. As contas das **matrículas são criadas
automaticamente** (veja [academico.md](academico.md#o-que-acontece-ao-salvar));
aqui também é possível lançar outras receitas, como venda de material ou
uniforme.

**Pesquisa:** descrição, responsável, aluno, observações.
**Filtros:** categoria, situação (Em aberto, Vencidas, Quitadas, Canceladas) e
período de emissão.

### Cadastrar

| Campo | Descrição |
|---|---|
| Descrição | Ex.: "Material didático 2027 – Maria". |
| Categoria | Somente categorias "A receber". |
| Responsável financeiro | Quem vai pagar. |
| Data de emissão | Padrão: hoje. |
| Valor bruto | Valor total. |
| Desconto (R$) | Não pode passar do valor bruto. |
| Número de parcelas | De 1 a 120. |
| Primeiro vencimento | As demais parcelas vencem mês a mês a partir dessa data. |
| Observações | |

O valor líquido (bruto − desconto) é dividido igualmente entre as parcelas; os
centavos que sobram vão para a primeira.

### Editar

- **Valor bruto** e **desconto** ficam bloqueados depois do cadastro, porque
  já foram divididos em parcelas.
- A tela mostra as parcelas da conta. Em cada parcela pendente há o botão
  **Baixar**, que abre o registro de pagamento já preenchido.
- **Adicionar parcela** cria uma parcela extra na conta.

### Excluir

Uma conta só pode ser excluída se **não tiver nenhuma baixa**. Exclua as
baixas antes. Ao excluir, as parcelas vão junto.

## Contratos a pagar

Igual aos contratos a receber, mas para despesas: o campo **Responsável** é
trocado por **Fornecedor**, e só aparecem categorias "A pagar".

**Pesquisa:** descrição, fornecedor, CPF/CNPJ do fornecedor, observações.
**Filtros:** os mesmos dos contratos a receber.

## Baixa de matrícula

Registra o **recebimento** de uma parcela a receber, por exemplo uma
mensalidade paga em PIX, dinheiro ou cartão no balcão.

> Mensalidades pagas por **boleto** não precisam ser baixadas à mão: a
> importação do arquivo de retorno faz isso (veja
> [cobranca-bancaria.md](cobranca-bancaria.md#retornos)).

| Campo | Descrição |
|---|---|
| Parcela | Digite parte da descrição da conta ou o nome do responsável e escolha a parcela na lista. Só aparecem parcelas pendentes. |
| Data do pagamento | |
| Valor pago | **Total recebido**, já incluindo multa, juros e correção. |
| Multa, Juros, Correção monetária | A parte do valor pago que é encargo. |
| Desconto | Valor abatido sem ser recebido (ex.: desconto de pontualidade). Opcional. |
| Forma de pagamento | PIX, Boleto, Dinheiro, Cartão de crédito, Cartão de débito, Transferência, Cheque. |
| Observações | |

**Como o sistema calcula o que foi abatido da parcela:**

```
valor abatido = valor pago − multa − juros − correção + desconto
```

Exemplo: parcela de R$ 500,00, paga com atraso. O responsável pagou
R$ 515,00, sendo R$ 10,00 de multa e R$ 5,00 de juros:
515 − 10 − 5 = **R$ 500,00 abatidos** → parcela **Quitada**.

Regras:

- O valor abatido não pode ser maior que o saldo da parcela.
- O valor pago mais o desconto precisa ser maior que a soma dos encargos.
- Se o valor abatido for menor que o saldo, a parcela fica **Parcial** e
  continua pendente pelo restante.

Ao clicar em **Baixar** em uma parcela (no Balanço ou na conta), o formulário
já vem com a parcela, o saldo e a data de hoje preenchidos.

## Pagamento de contas

O mesmo formulário da baixa de matrícula, mas para parcelas **a pagar**
(contas de fornecedores). Na busca da parcela, pesquise pela descrição da
conta, nome do fornecedor ou CPF/CNPJ.

## Baixas (histórico)

Lista de todas as baixas e pagamentos já registrados, aberta depois de salvar
uma baixa (endereço `/accounts/payments/list/`).

**Pesquisa:** descrição da conta, responsável, fornecedor ou observações.
**Filtros:** natureza, forma de pagamento e período do pagamento.

Editar ou excluir uma baixa recalcula a situação da parcela automaticamente:
excluir a única baixa de uma parcela quitada faz ela voltar para **Aberto**.

## Balanço

Visão de **todas as parcelas**, a receber e a pagar, para acompanhar o que
vence, o que foi pago e o que falta.

**Pesquisa:** descrição da conta, responsável, fornecedor, nome ou matrícula
do aluno.
**Filtros:** natureza, situação (Pendentes, Vencidas, Aberto, Parcial,
Quitado, Cancelado, Expirado) e período de vencimento.

Colunas: vencimento, natureza, conta, nº da parcela, responsável/fornecedor,
valor, **faltante** (saldo) e situação.

No topo aparecem os **totais de todo o resultado filtrado** (não só da página
atual), separados entre a receber e a pagar: valor total, quanto foi
quitado e quanto falta.

Exemplos de uso:

- **Inadimplência**: Natureza "A receber" + Situação "Vencidas".
- **Contas da semana**: Natureza "A pagar" + vencimento de segunda a sexta.
- **Previsão do mês**: Situação "Pendentes" + vencimento do dia 1 ao último dia
  do mês.

Cada parcela pendente tem o botão **Baixar** para registrar o pagamento.
