# Configuração de Matrículas

Cadastros que servem de base para as matrículas. Precisam estar prontos antes
de matricular os alunos e costumam ser revistos uma vez por ano, antes do
período de matrículas.

[← Voltar ao menu](sidebar.md)

## Ano escolar

Define o calendário do ano letivo. O ano exibido nas listas (ex.: "2027") é o
ano da data de início.

**Pesquisa:** data de início ou de fim.

| Campo | Descrição |
|---|---|
| Data de início / Data de fim | Começo e fim do ano letivo. |
| Início e fim do 1º ao 4º bimestre | Datas de cada bimestre (opcionais). |

O ano escolar é usado em vários lugares:

- as **turmas** e os **tipos de contrato** pertencem a um ano escolar;
- o **início e fim do contrato** de matrícula são, por padrão, as datas do ano
  escolar;
- as **mensalidades** vencem nos meses do ano escolar (veja
  [academico.md](academico.md#mensalidades-geradas-automaticamente)).

## Cursos oferecidos

Os cursos da escola, por exemplo **Ensino Médio**, **Pré UNB** e **Pré ENEM**.
Basta o nome, que não pode se repetir.

**Pesquisa:** nome.

Um curso com turmas ou tipos de contrato não pode ser excluído.

## Tipos de contratos

O tipo de contrato é o "modelo de preço" da matrícula: diz quanto custa um
curso, numa série, num ano escolar. Toda matrícula escolhe um tipo de
contrato.

**Pesquisa:** curso, descrição ou ano escolar.

| Campo | Descrição |
|---|---|
| Curso | Curso do contrato. |
| Série | 1ª, 2ª ou 3ª série. Deixe vazio para cursos sem série (ex.: pré-vestibular). |
| Ano escolar | Ano letivo do contrato. |
| Valor total | Valor do contrato no ano inteiro, antes de descontos. É dividido em mensalidades. |
| Desconto de pontualidade | Valor em R$ abatido de **cada parcela paga por boleto até o vencimento** (padrão R$ 90,00). |
| Descrição | Observação livre. |
| Início / Fim do contrato | Preenchidos automaticamente com as datas do ano escolar. |

> Alterar o valor de um tipo de contrato **não muda** as matrículas já feitas:
> cada matrícula guarda o valor e o desconto do dia em que foi criada.

## Tipos de descontos

Descontos que podem ser aplicados a uma matrícula, como "Irmãos", "Bolsa
50%", "Funcionário".

**Pesquisa:** descrição.

| Campo | Descrição |
|---|---|
| Descrição | Nome do desconto. |
| Percentual | Entre 0 e 100. É aplicado sobre o valor total do contrato. |

Assim como o valor do contrato, o percentual fica gravado na matrícula no
momento em que ela é criada.

## Documentos Necessários

Lista de documentos que o aluno deve entregar na matrícula (ex.: certidão de
nascimento, histórico escolar, comprovante de residência, foto 3x4).

**Pesquisa:** descrição.

Toda matrícula recebe uma lista de conferência com **todos** os documentos
cadastrados aqui, que a secretaria marca como entregues na tela da matrícula.
Um documento novo cadastrado depois também aparece nas matrículas existentes
na próxima vez que forem abertas.
