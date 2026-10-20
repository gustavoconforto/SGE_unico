# Acadêmico

Alunos, responsáveis, turmas, matérias e matrículas: o dia a dia da
secretaria. Turmas, Matérias e Notas ficam no submenu **Acadêmico → Edição**.

[← Voltar ao menu](sidebar.md)

## Responsáveis

Pais, mães e demais responsáveis pelos alunos. Um mesmo responsável pode estar
ligado a vários alunos (irmãos), então cadastre-o só uma vez.

**Pesquisa:** nome ou CPF.

O formulário tem três abas:

| Aba | Campos |
|---|---|
| Dados pessoais | Nome, sexo, CPF, RG, estado civil, órgão emissor, data de nascimento, nacionalidade, naturalidade |
| Contato | Telefone, celular, e-mail |
| Endereço | Endereço, bairro, cidade, UF, CEP |

> Para quem vai pagar por **boleto**, CPF, endereço e CEP precisam estar
> corretos: sem eles o boleto não é gerado (veja
> [cobranca-bancaria.md](cobranca-bancaria.md)).

## Alunos

Cadastro do aluno e ligação com seus responsáveis.

**Pesquisa:** nome, nome social, matrícula ou CPF.

| Aba | Campos |
|---|---|
| Dados pessoais | Nome, nome social e opção "Usar nome social", matrícula, foto, sexo, CPF, RG, órgão emissor, data de nascimento, nacionalidade, naturalidade |
| Contato | Telefone, celular, e-mail |
| Endereço | Endereço, bairro, cidade, UF, CEP |
| Responsáveis | Os responsáveis do aluno (veja abaixo) |

- **Matrícula** (número do aluno): gerado automaticamente no formato ano +
  sequência, por exemplo `202600001`. Não pode ser editado.
- **Nome social**: com "Usar nome social" marcado, o sistema mostra o nome
  social do aluno nas listas e telas.
- **Foto**: imagem JPG, PNG ou WEBP. Ao trocar a foto, a anterior é apagada.
  Sem foto, aparece uma imagem padrão.

### Responsáveis do aluno

Na aba de responsáveis, escolha cada responsável (já cadastrado em
**Responsáveis**) e informe:

| Campo | Significado |
|---|---|
| Parentesco | Pai, Mãe, Avô/Avó, Tio(a), Irmão(ã), Padrasto/Madrasta, Tutor(a) legal, Outro |
| Responsável financeiro | Quem paga. **Obrigatório ter pelo menos um para matricular o aluno.** O primeiro responsável financeiro é quem aparece na conta a receber e no boleto. |
| Contato principal | Quem a escola procura primeiro. |
| Mora com o aluno(a) | |
| Autorizado a buscar o aluno | Pode retirar o aluno da escola. |

Um mesmo responsável não pode ser ligado duas vezes ao mesmo aluno.

## Turmas

Turmas de cada curso em cada ano escolar.

**Pesquisa:** nome da turma, curso ou ano.

| Campo | Descrição |
|---|---|
| Curso | Curso da turma. |
| Ano letivo | Ano escolar da turma. |
| Série | 1, 2 ou 3 (opcional). |
| Nome | Ex.: "A", "Inspiração". Não pode repetir no mesmo curso e ano. |
| Vagas | Capacidade da turma (opcional). |

Na matrícula, cada turma aparece com a ocupação, por exemplo
`2° Inspiração - 2027 (12/50)`: 12 alunos ativos de 50 vagas.

### Alunos da turma

A tela **Gerenciamento de turmas** mostra a lista de alunos de uma turma. Ela
ainda não tem item no menu; abra pelo endereço `/classes/detail/`.

1. Em **Ano letivo**, escolha o ano. A lista de **Turmas** passa a mostrar só
   as turmas desse ano.
2. Em **Turmas**, escolha a turma. Aparecem os alunos com matrícula **ativa**
   nela, em ordem alfabética, em páginas de 10.

Alunos com matrícula transferida, desistente, concluída ou cancelada não
aparecem. Ao trocar o ano, a lista de alunos é limpa até você escolher uma nova
turma. O ano e a turma ficam no endereço da página, então recarregar ou mandar
o link abre a mesma turma.

## Matérias

As disciplinas ensinadas na escola (Português, Matemática, Física…). Hoje é
só um cadastro; elas serão usadas no lançamento de notas.

**Pesquisa:** nome da matéria.

| Campo | Descrição |
|---|---|
| Nome | Nome da matéria. Não pode repetir. |

## Matrículas

A matrícula liga um aluno a um tipo de contrato (curso, série e ano) e,
opcionalmente, a uma turma. É a partir dela que o sistema gera a cobrança das
mensalidades.

**Pesquisa:** nome ou nome social do aluno, matrícula do aluno, turma ou curso.

### Cadastrar uma matrícula

| Campo | Descrição |
|---|---|
| Aluno | O aluno precisa ter **pelo menos um responsável financeiro**. |
| Tipo de contrato | Curso, série e ano. Ao escolher, a lista de turmas se atualiza. |
| Turma | Só aparecem turmas do mesmo ano, curso e série do contrato. |
| Situação | Ativa (padrão), Transferida, Desistente, Concluída, Cancelada. |
| Desconto | Tipo de desconto, se houver. |
| Dia de vencimento | Dia do mês em que as mensalidades vencem (1 a 28; padrão 10). |
| Data da matrícula, Valor bruto, Percentual de desconto | Preenchidos automaticamente. |

Um aluno não pode ter duas matrículas no mesmo tipo de contrato.

### O que acontece ao salvar

Ao criar a matrícula, o sistema faz sozinho:

1. cria uma **conta a receber** na categoria "Mensalidade", em nome do
   primeiro responsável financeiro do aluno, com o valor do contrato menos o
   desconto;
2. gera as **mensalidades** (parcelas) dessa conta;
3. cria a **lista de documentos** a entregar.

Depois de salvar, a tela de edição da matrícula é aberta.

### Mensalidades geradas automaticamente

- A **1ª parcela** vence na data da matrícula.
- As demais vencem no **dia de vencimento** escolhido, nos meses do ano
  escolar, até dezembro. Se o dia cair em sábado ou domingo, passa para a
  segunda-feira.
- Matrícula **durante o ano**: uma parcela por mês restante.
  Ex.: matrícula em setembro → setembro, outubro, novembro e dezembro.
- Matrícula **antecipada** (ex.: em novembro de 2026 para 2027): 12 parcelas,
  a 1ª na data da matrícula e as outras de fevereiro a dezembro de 2027.
- O valor é dividido igualmente; os centavos que sobram vão para a 1ª
  parcela, para que a soma bata exatamente com o valor do contrato.

### Editar uma matrícula

A tela de edição mostra, além dos dados da matrícula:

- **Documentos**: a lista de conferência; marque "Entregue" em cada documento
  recebido.
- **Parcelas**: as mensalidades da matrícula, com vencimento e valor.
- **Imprimir**: abre o contrato de prestação de serviços em uma nova
  aba, com os dados do aluno, do responsável financeiro, valores e
  parcelamento, e permite baixar em PDF.

Tudo é salvo de uma vez pelo botão **Salvar**.

### Mudar a situação da matrícula

Ao mudar a situação para **Transferida**, **Desistente** ou **Cancelada**, o
sistema **cancela as mensalidades em aberto** que vencem de hoje em diante.
Parcelas já vencidas continuam devidas, e parcelas pagas em parte são
mantidas.

Boletos já registrados no banco para parcelas canceladas devem ter a baixa
pedida na próxima remessa (veja
[cobranca-bancaria.md](cobranca-bancaria.md#pedido-de-baixa)).

## Notas

Item reservado no menu (**Acadêmico → Edição → Notas**); o lançamento de notas
ainda não foi implementado.
