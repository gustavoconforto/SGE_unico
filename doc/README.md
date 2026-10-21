# Manual do usuário — Gestão Escolar

O **Gestão Escolar** é o sistema da Único Educacional para cuidar da secretaria
e do financeiro da escola: funcionários, cursos, turmas, alunos e
responsáveis, matrículas, contas a receber e a pagar, e boletos bancários
(Bradesco).

Este manual explica o sistema do ponto de vista de quem usa as telas. Ele está
dividido assim:

| Documento | Conteúdo |
|---|---|
| [sidebar.md](sidebar.md) | Mapa do menu lateral: o que há em cada item e onde ler mais |
| [recursos-humanos.md](recursos-humanos.md) | Usuários, grupos, permissões, cargos e funcionários |
| [configuracao-matriculas.md](configuracao-matriculas.md) | Ano escolar, cursos, tipos de contrato, descontos e documentos exigidos |
| [academico.md](academico.md) | Alunos, responsáveis, turmas (e os alunos de cada turma), matérias e matrículas |
| [financeiro.md](financeiro.md) | Categorias, fornecedores, contas a receber e a pagar, parcelas e baixas |
| [cobranca-bancaria.md](cobranca-bancaria.md) | Boletos Bradesco: configuração, remessas, retornos e acompanhamento |
| [fluxos.md](fluxos.md) | Passo a passo das rotinas mais comuns (início de ano, matrícula, recebimento, cobrança mensal) |

## Entrar no sistema

Abra a tela de login (`/login/`), digite seu **Usuário** e sua **Senha** e
clique em **Entrar**. Se os dados estiverem errados, a mensagem aparece abaixo
dos campos. Quem já está conectado e abre a tela de login vai direto para o
sistema.

As contas são criadas em **Recursos Humanos → Usuários** (veja
[recursos-humanos.md](recursos-humanos.md)).

## Como as telas funcionam

Quase todas as telas do sistema seguem o mesmo padrão. Aprendendo uma, você
sabe usar as outras.

### Listas

Cada item do menu abre uma **lista** de registros, em páginas de 10.

- **Adicionar registro**: botão no alto, à direita, abre o formulário de
  cadastro.
- **Pesquisa**: o campo de busca filtra a lista enquanto você digita (não é
  preciso apertar Enter). O texto de exemplo dentro do campo mostra por quais
  informações é possível pesquisar (nome, CPF, matrícula etc.).
- **Filtros**: algumas listas têm filtros extras (situação, natureza, período
  de datas). O botão **Limpar filtros** volta tudo ao normal.
- **Editar** e **Deletar**: ficam na coluna **Opções**, no fim de cada linha.
- A pesquisa, os filtros e a página atual ficam guardados no endereço da
  página. Você pode recarregar, usar o botão Voltar do navegador ou mandar o
  link para um colega, e a lista abre do mesmo jeito.

### Formulários

- Campos obrigatórios que ficarem vazios, ou valores inválidos, aparecem com a
  mensagem de erro logo abaixo do campo.
- Campos cinza (desabilitados) são preenchidos pelo próprio sistema e não podem
  ser alterados ali.
- Datas usam o seletor de calendário do navegador e são exibidas no formato
  dd/mm/aaaa.
- Valores em dinheiro são digitados com ponto ou vírgula decimal, conforme o
  navegador, e exibidos como `R$ 1234.56`.

### Exclusão

Ao clicar em **Deletar**, o sistema mostra os dados do registro e pergunta
"Deseja, realmente, deletar este registro?". Só depois de confirmar o registro
é apagado.

Registros **em uso** não podem ser apagados. Por exemplo: uma categoria
financeira que já tem contas, ou um fornecedor com contas lançadas. Nesse caso
o sistema avisa e nada é excluído.

### Mensagens

Depois de salvar ou excluir, aparece uma mensagem no alto da tela:

- verde: "Registro cadastrado com sucesso" / "Registro atualizado com sucesso";
- amarela: "Registro deletado com sucesso";
- vermelha: algo impediu a operação, com o motivo.

### Menu lateral

O menu fica à esquerda e é dividido em quatro seções que abrem e fecham com um
clique: **Recursos Humanos**, **Configuração de Matrículas**, **Financeiro** e
**Acadêmico**. Dentro do Acadêmico, o submenu **Edição** também abre e fecha
com um clique. No celular, o menu fica escondido e abre pelo botão de menu no
topo da tela. No rodapé do menu aparece o usuário conectado.

Veja o mapa completo em [sidebar.md](sidebar.md).

## Limitações atuais

- O login ainda **não é obrigatório**: as telas abrem mesmo sem entrar no
  sistema. Também ainda não há botão para sair.
- As permissões e grupos podem ser cadastrados, mas **ainda não restringem o
  acesso às telas**: qualquer pessoa vê e altera tudo.
- O item **Acadêmico → Edição → Notas** ainda não foi implementado.
- A tela **Gerenciamento de turmas** (alunos da turma) ainda não tem item no
  menu.
