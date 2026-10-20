# Recursos Humanos

Seção do menu com o acesso ao sistema (usuários, grupos e permissões) e o
cadastro de funcionários.

[← Voltar ao menu](sidebar.md)

## Usuários

Contas de quem entra no sistema pela tela de login.

**Pesquisa:** usuário, nome, sobrenome ou e-mail.

| Campo | Descrição |
|---|---|
| Primeiro nome / Sobrenome | Nome exibido no rodapé do menu. |
| Usuário | Nome usado para entrar no sistema. Deve ser único. |
| E-mail | E-mail de contato da pessoa. |
| Membro da equipe | Permite acessar a área administrativa do Django (`/admin/`). |
| Ativo | Desmarque para bloquear o acesso sem apagar a conta. É melhor que excluir. |
| Superusuário | Tem todas as permissões. Use com cuidado. |

## Grupos

Um grupo reúne permissões (ex.: "Secretaria", "Financeiro") para que não seja
preciso marcar uma a uma em cada usuário.

**Pesquisa:** nome do grupo.

| Campo | Descrição |
|---|---|
| Nome | Nome do grupo. |
| Permissões | Lista de permissões; segure Ctrl (ou ⌘ no Mac) para selecionar várias. |

## Permissões

Lista das permissões do sistema, criadas automaticamente para cada tipo de
registro (ver, adicionar, alterar, excluir). Em geral só é preciso consultá-la;
cadastrar ou alterar permissões é tarefa técnica.

**Pesquisa:** nome, código, aplicativo ou modelo.

> **Atenção:** hoje as permissões e grupos ainda não bloqueiam o acesso às
> telas. Eles já podem ser organizados para quando esse controle for ativado.

## Cargos

Cargos dos funcionários (ex.: Professor, Coordenador, Secretária). Precisa
existir antes de cadastrar o funcionário.

**Pesquisa:** nome do cargo.

Um cargo que já tem funcionários não pode ser excluído.

## Funcionários

Cadastro dos funcionários da escola. O formulário é dividido em abas; se algum
campo tiver erro, o sistema abre a aba onde ele está.

**Pesquisa:** nome, CPF ou cargo.

| Aba | Campos |
|---|---|
| Dados pessoais | Nome, sexo, cargo, CPF, RG, órgão emissor, data de nascimento, nacionalidade, naturalidade |
| Contato | Telefone, celular, e-mail |
| Endereço | Endereço, bairro, cidade, UF, CEP |

- CPF e RG não podem se repetir entre funcionários.
- CPF e CEP são guardados só com números; pode digitar com ou sem pontuação.
