# Menu lateral

O menu lateral é o ponto de partida de todas as telas do sistema. Ele é
dividido em quatro seções; clique no nome da seção para abrir ou fechar seus
itens. No celular, o menu abre pelo botão no topo da tela e fecha pelo **X**.

No topo do menu aparecem o nome do sistema (Gestão Escolar), a versão e a
escola (Único Educacional). No rodapé aparecem o nome e o e-mail do usuário
conectado.

Para o funcionamento geral das listas, pesquisas e formulários, veja
[README.md](README.md#como-as-telas-funcionam).

```
Recursos Humanos              Configuração de Matrículas
├── Usuários                  ├── Ano escolar
├── Grupos                    ├── Cursos oferecidos
├── Permissões                ├── Tipos de contratos
├── Cargos                    ├── Tipos de descontos
└── Funcionários              └── Documentos Necessários

Financeiro                    Acadêmico
├── Categorias financeiras    ├── Edição
├── Fornecedores              │   ├── Turmas
├── Contratos a receber       │   ├── Matérias
├── Contratos a pagar         │   └── Notas (em construção)
├── Baixa de matrícula        ├── Matrículas
├── Pagamento de contas       ├── Alunos
├── Balanço                   └── Responsáveis
├── Remessas
├── Retornos
└── Boletos
```

## Recursos Humanos

Pessoas que trabalham na escola e quem pode entrar no sistema.
Detalhes em [recursos-humanos.md](recursos-humanos.md).

| Item | Para que serve |
|---|---|
| **Usuários** | Contas de acesso ao sistema: nome, usuário de login, e-mail e se a conta está ativa, é da equipe ou é superusuário. |
| **Grupos** | Conjuntos de permissões (ex.: "Secretaria", "Financeiro") para atribuir a vários usuários de uma vez. |
| **Permissões** | Lista das permissões do sistema, usadas pelos grupos. Normalmente não precisa ser alterada. |
| **Cargos** | Cargos dos funcionários (Professor, Coordenador, Secretária…). Cadastre antes dos funcionários. |
| **Funcionários** | Cadastro completo dos funcionários: dados pessoais, contato, endereço e cargo. |

## Configuração de Matrículas

Cadastros de base que precisam existir **antes** de matricular alunos.
Normalmente são revistos uma vez por ano. Detalhes em
[configuracao-matriculas.md](configuracao-matriculas.md).

| Item | Para que serve |
|---|---|
| **Ano escolar** | Datas de início e fim do ano letivo e de cada um dos 4 bimestres. O vencimento das mensalidades segue o ano escolar. |
| **Cursos oferecidos** | Cursos da escola (ex.: Ensino Médio, Pré UNB, Pré ENEM). |
| **Tipos de contratos** | O "preço" de cada curso, série e ano: valor total do contrato e desconto de pontualidade do boleto. Toda matrícula usa um tipo de contrato. |
| **Tipos de descontos** | Descontos que podem ser dados na matrícula (ex.: "Irmãos – 10%"), em percentual. |
| **Documentos Necessários** | Documentos que o aluno deve entregar. Cada matrícula ganha uma lista de conferência com eles. |

## Financeiro

Tudo o que a escola tem a receber e a pagar, os pagamentos e os boletos.
Detalhes em [financeiro.md](financeiro.md) e
[cobranca-bancaria.md](cobranca-bancaria.md).

| Item | Para que serve |
|---|---|
| **Categorias financeiras** | Classificação das contas (Mensalidade, Material, Aluguel, Energia…), cada uma marcada como "A receber" ou "A pagar". |
| **Fornecedores** | Empresas e pessoas a quem a escola paga, com CPF/CNPJ e contato. |
| **Contratos a receber** | Contas que a escola tem a receber. As das matrículas são criadas automaticamente; outras (ex.: venda de material) podem ser lançadas à mão e divididas em parcelas. |
| **Contratos a pagar** | Contas que a escola tem a pagar a fornecedores, divididas em parcelas. |
| **Baixa de matrícula** | Registrar o recebimento de uma parcela a receber (mensalidade paga em PIX, dinheiro, cartão…), com multa, juros e desconto. |
| **Pagamento de contas** | Registrar o pagamento de uma parcela a pagar (conta de fornecedor). |
| **Balanço** | Todas as parcelas, a receber e a pagar, com filtros por situação e vencimento e os totais de valor, recebido/pago e faltante. Daqui também se dá baixa em uma parcela. |
| **Remessas** | Gerar o arquivo de remessa (.REM) com os boletos novos e os pedidos de baixa para enviar ao Bradesco. Também dá acesso à configuração bancária. |
| **Retornos** | Importar o arquivo de retorno (.RET) do banco, que registra automaticamente os boletos pagos, rejeitados e baixados. |
| **Boletos** | Acompanhar todos os boletos emitidos e a situação de cada um no banco. |

> O histórico de baixas e pagamentos já registrados fica na tela **Baixas**
> (`/accounts/payments/list/`), que é aberta depois de salvar uma baixa ou um
> pagamento. Ela ainda não tem item próprio no menu.

## Acadêmico

O dia a dia da secretaria. Detalhes em [academico.md](academico.md).

O submenu **Edição** reúne os cadastros da parte pedagógica. Clique nele para
abrir ou fechar seus itens.

| Item | Para que serve |
|---|---|
| **Edição → Turmas** | Turmas de cada curso e ano, com série, nome, turno e número de vagas. |
| **Edição → Matérias** | Matérias (disciplinas) ensinadas na escola, como Português e Matemática. |
| **Edição → Notas** | Ainda não implementado. |
| **Matrículas** | Matricular um aluno em um tipo de contrato e turma. Ao salvar, o sistema cria sozinho a conta a receber, as mensalidades e a lista de documentos. Também imprime o contrato em PDF. |
| **Alunos** | Cadastro do aluno (dados pessoais, foto, contato, endereço) e seus responsáveis. O número de matrícula é gerado automaticamente. |
| **Responsáveis** | Cadastro de pais e responsáveis. Um responsável pode estar ligado a vários alunos (irmãos). |

> A tela **Gerenciamento de turmas** (`/classes/detail/`), que mostra os alunos
> de uma turma, ainda não tem item próprio no menu. Veja
> [academico.md](academico.md#alunos-da-turma).

## Ordem recomendada de cadastro

Para começar a usar o sistema do zero (ou um novo ano), siga esta ordem:

1. **Ano escolar** → **Cursos oferecidos** → **Turmas** (e **Matérias**, se
   faltar alguma)
2. **Tipos de contratos**, **Tipos de descontos**, **Documentos Necessários**
3. **Categorias financeiras** (a categoria "Mensalidade" é criada sozinha na
   primeira matrícula, se não existir)
4. **Responsáveis** e **Alunos** (com pelo menos um responsável financeiro)
5. **Matrículas**

O passo a passo de cada rotina está em [fluxos.md](fluxos.md).
