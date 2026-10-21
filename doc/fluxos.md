# Rotinas passo a passo

Roteiros das tarefas mais comuns, indicando o caminho no menu lateral.

[← Voltar ao menu](sidebar.md)

## 1. Preparar um novo ano letivo

Faça antes de abrir as matrículas do ano.

1. **Configuração de Matrículas → Ano escolar**: cadastre o ano com as datas
   de início e fim e dos bimestres.
2. **Configuração de Matrículas → Cursos oferecidos**: confira se todos os
   cursos existem.
3. **Acadêmico → Edição → Turmas**: cadastre as turmas do novo ano, com série
   e vagas. Em **Acadêmico → Edição → Matérias**, confira se as matérias do
   ano estão cadastradas.
4. **Configuração de Matrículas → Tipos de contratos**: cadastre um contrato
   para cada curso e série do novo ano, com o valor anual e o desconto de
   pontualidade.
5. **Configuração de Matrículas → Tipos de descontos** e **Documentos
   Necessários**: revise se algo mudou.

## 2. Matricular um aluno

1. **Acadêmico → Responsáveis**: pesquise pelo CPF. Se o responsável não
   existir, cadastre-o com CPF, endereço e CEP completos (necessários para o
   boleto).
2. **Acadêmico → Alunos**: pesquise o aluno. Se for novo, cadastre-o.
   Na aba **Responsáveis**, ligue o responsável e marque **Responsável
   financeiro**.
3. **Acadêmico → Matrículas → Adicionar registro**: escolha o aluno, o tipo
   de contrato, a turma, o desconto (se houver) e o dia de vencimento. Salve.
4. Na tela de edição que abre:
   - marque os **documentos** já entregues;
   - confira as **parcelas** geradas;
   - clique em **Imprimir** para gerar o contrato em PDF e colher as
     assinaturas.
5. Se a primeira parcela for paga na hora, registre em
   **Financeiro → Baixa de matrícula**.

## 3. Receber uma mensalidade no balcão

1. **Financeiro → Balanço**: pesquise pelo nome do aluno ou do responsável.
2. Clique em **Baixar** na parcela.
3. Confira o valor (vem preenchido com o saldo), informe multa e juros se
   houver atraso, escolha a forma de pagamento e salve.
4. Se a parcela já tinha **boleto registrado**, inclua o pedido de baixa do
   boleto na próxima remessa (passo 5.2).

## 4. Pagar uma conta de fornecedor

1. **Financeiro → Fornecedores**: cadastre o fornecedor, se necessário.
2. **Financeiro → Contratos a pagar → Adicionar registro**: informe
   descrição, categoria, fornecedor, valor, número de parcelas e primeiro
   vencimento.
3. No dia do pagamento: **Financeiro → Pagamento de contas**, busque a
   parcela pelo fornecedor e registre o pagamento.

## 5. Ciclo mensal de boletos

### 5.1 Gerar e enviar a remessa

1. **Financeiro → Remessas → Gerar remessa**.
2. Filtre pelo vencimento do próximo mês.
3. Veja as parcelas com problema (responsável sem CPF, endereço ou CEP) e
   corrija os cadastros em **Acadêmico → Responsáveis**.
4. Marque as parcelas e os pedidos de baixa e confirme.
5. Na lista de remessas, clique em **Baixar arquivo** e envie o `.REM` pelo
   site do Bradesco.

### 5.2 Pedir baixa de boletos

Na mesma tela **Gerar remessa**, os boletos de parcelas canceladas ou pagas de
outra forma aparecem como pedidos de baixa. Inclua-os na remessa.

### 5.3 Importar os retornos

Faça sempre que o banco disponibilizar um novo retorno (de preferência
diariamente).

1. Baixe o arquivo `.RET` no site do banco.
2. **Financeiro → Retornos → Importar retorno** e envie o arquivo.
3. Confira o resumo. Se houver ocorrências **com erro**, abra o detalhe e
   acerte as parcelas no **Balanço**.
4. Em **Financeiro → Boletos**, filtre por **Rejeitado** para ver boletos que
   o banco recusou e reenvie-os na próxima remessa depois de corrigir o
   cadastro.

## 6. Aluno transferido ou desistente

1. **Acadêmico → Matrículas**: abra a matrícula e mude a **Situação** para
   Transferida, Desistente ou Cancelada. Salve.
2. O sistema cancela as mensalidades em aberto a partir de hoje. As vencidas
   continuam cobráveis.
3. **Financeiro → Remessas → Gerar remessa**: inclua os pedidos de baixa dos
   boletos dessas parcelas.

## 7. Acompanhar a inadimplência

1. **Financeiro → Balanço**.
2. Filtre **Natureza: A receber** e **Situação: Vencidas**.
3. O total faltante no topo mostra o valor em atraso. Use a pesquisa para ver
   um responsável ou aluno específico.
