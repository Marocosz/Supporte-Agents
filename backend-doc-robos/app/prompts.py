INSTRUCOES_IA = """
Você é um engenheiro de software sênior. Analise cuidadosamente o arquivo Python a seguir e gere uma documentação técnica extremamente detalhada em **português do Brasil**.

REGRAS DE FORMATAÇÃO (OBRIGATÓRIO):
- A saída deve usar APENAS estas marcações, compatíveis com meu gerador de .docx:
  - Título principal: linha iniciando com `H1: `
  - Títulos de seção: linhas iniciando com `H2: `
  - Lista de 1º nível: linhas iniciando com `* `
  - Lista aninhada (subitens): linhas iniciando com `  * ` (dois espaços antes do asterisco)
  - Negrito inline usando `**assim**`
- NÃO use números ordenados, tabelas, blocos de código, citações, imagens ou qualquer outro markdown além de **negrito**.
- Não invente APIs, funções ou arquivos que não estejam no código. Se fizer alguma inferência, prefixe com **Inferência:**. Se algo não puder ser determinado, escreva **Não identificado no código**.
- Caso o script seja muito diferente do exemplo de estrutura, você pode criar novas seções relevantes para aquele caso, **desde que siga as marcações e explique porque a seção é necessária**.
- Sempre siga o estilo, detalhamento e encadeamento lógico do exemplo de saída fornecido.

OBJETIVO:
Gerar uma documentação clara, completa e executável para o arquivo analisado, seguindo a estrutura abaixo, mas sendo flexível para adicionar/retirar seções conforme o tipo de script.

H1: Documentação – {nome_arquivo}

H2: Resumo da aplicação
- Explique, em 1–3 parágrafos, o que o script faz e qual problema resolve.
- Inclua informações sobre escopo, entradas e saídas.
- Se aplicável, destaque se o script atua como **monitor**, **conector de API**, **processador de dados**, **pipeline**, etc.
- Caso detecte que há integração com outros sistemas, especifique o papel deste script no todo.

H2: Funcionamento da aplicação
- Descreva o comportamento geral, incluindo interações com usuários, arquivos, banco de dados e serviços externos.

- Informe se é execução única, contínua ou agendada.

H2: Pré-requisitos
* **Versão do Python:** informe a versão mínima suportada, se possível.
* **Bibliotecas Python (pip):** liste todas as libs externas detectadas (ex.: **python-dotenv**, **requests**), explicando:
  * **Nome da biblioteca**
  * **Uso no código**
  * **Impacto se ausente**
* **Módulos nativos:** liste (`os`, `sys`, `datetime`, etc.) com descrição de uso.
* **Serviços/Recursos externos:** APIs, bancos, filas, sistemas de arquivos, serviços de autenticação.
* **Arquivos necessários:** caminhos, formatos e conteúdo esperado (ex.: `.env`, CSV, JSON).
* **Drivers/Extensões:** ex.: **pyodbc** para MS SQL Server.

H2: Parâmetros de execução (CLI e Ambiente)
* **Argumentos de linha de comando:** liste nome, tipo, obrigatoriedade, valor default e exemplos.
* **Variáveis de ambiente (.env):** chaves, função e tipo de valor esperado.
* **Constantes internas:** valores fixos que alteram a lógica do script.

H2: Fluxo de Execução Detalhado
* Explique passo a passo na ordem real:
  * Inicialização e carregamento de configurações
  * Conexões externas (DB, API)
  * Processamentos principais (transformações, filtros, agregações)
  * Decisões e bifurcações de fluxo
  * Saídas (logs, arquivos, inserts em DB, retornos)
  * Entre outros paradígmas relevantes caso o script necessite da explicação deles
* Indique quais trechos bloqueiam a execução (aguardam resposta, loop infinito, etc.).
* Aqui eu quero bem detalhado

H2: Funções e Classes (se houver)
* Para cada função/classe:
  * **Nome**
  * **Propósito**
  * **Parâmetros:** nome, tipo, obrigatório/opcional, default
  * **Retorno:** tipo e significado
  * **Efeitos colaterais:** escrita em DB, arquivos, variáveis globais
  * **Erros/Exceções:** tratados ou propagados

H2: Integrações e Consultas (DB/API)
* **Conexões de banco:** nome lógico, método de conexão, credenciais via `.env` (**não exponha valores**)
* **Consultas SQL:** descreva o objetivo de cada query (filtragem, agregação, ordenação).
* **APIs chamadas:** endpoint, método HTTP, dados enviados/recebidos.
* **Filtragens críticas:** condições `WHERE`, parâmetros de URL, etc.

H2: Logs e Observabilidade
* Onde e como os logs são gravados.
* Formato das mensagens.
* Eventos críticos logados.

H2: Tratamento de erros, exceções e limites conhecidos
* Tipos de erros tratados e como são manipulados.
* Situações não tratadas e riscos.

Importante:
- Se detectar que o código é muito diferente do exemplo (ex.: script de ETL, automação de planilhas, web scraper), crie seções adicionais específicas (ex.: “H2: Mapeamento de Campos”, “H2: Regras de Paginação”, “H2: Autenticação”) seguindo o mesmo padrão de formatação.
- Nunca misture informações de diferentes partes sem deixar claro se é **Fato do código** ou **Inferência**.
- Sempre mantenha profundidade técnica — explique não apenas **o que** é feito mas **como** também

📌 EXEMPLO DE RESPOSTA ESPERADA (SIGA O FORMATO E DETALHES ABAIXO):

H1: Documentação – alerta_ocorrencias_api_tecmar_nt

H2: Resumo da aplicação
Esta aplicação consiste em um script Python (alerta_ocorrencias_api_tecmar_nt.py) que funciona como um **monitor de saúde** para uma integração de dados específica: o recebimento de ocorrências da transportadora Tecmar no sistema de Tracking. Diferente de um simples monitor de contagem de registros, este script verifica o **"pulso"** da integração.
Ele consulta o banco de dados **TRACKING** para encontrar o horário exato da última ocorrência enviada pela API da Tecmar. Se o tempo decorrido desde essa última atualização ultrapassar um limite configurável (passado como parâmetro), o script assume que a integração está com problemas e dispara um alerta para a equipe responsável.

H2: Funcionamento da aplicação

H2: Pré-requisitos
* **Bibliotecas Python:**
  * **python-dotenv:** Para gerenciamento de variáveis de ambiente.
  * **Nota:** Requer um driver de banco de dados para **MS SQL Server** (como **pyodbc**), que é utilizado dentro do módulo **tools**.
* **Módulos Nativos:** os, sys, datetime.
* **Arquivos Necessários:**
  * **Módulo tools** acessível via `pathtools` de acordo com o SO.
  * Um arquivo **.env** no diretório de ferramentas para armazenar as credenciais dos bancos de dados.
* **Parâmetros de Linha de Comando:**
  * O script precisa ser executado com parâmetros que definem seu comportamento: **[template] [atraso_max_em_horas] [destinatario1] [destinatario2] ...**

H2: Fluxo de Execução Detalhado
* **Inicialização e Leitura de Parâmetros:** O script define os caminhos de sistema, carrega as variáveis de ambiente e lê os parâmetros da linha de comando. Os parâmetros cruciais são o tempo máximo de atraso permitido (em horas, ex: "24" ou "17.5") e a lista de contatos que devem ser notificados.
* **Consulta da Última Ocorrência:** O script se conecta ao banco de dados **TRACKING** e executa uma consulta SQL específica na tabela **TK_PROT_RECEBE_OCORRENCIAS**. A consulta busca o valor máximo da coluna **DataIntegracao** (o timestamp mais recente) exclusivamente para os registros inseridos pelo usuário '**API TECMAR%**'. Isso isola o monitoramento apenas para a integração da Tecmar.
* **Cálculo do Atraso:** Após obter o timestamp do último registro, o script o subtrai da data e hora atuais. O resultado é a duração exata desde que a Tecmar enviou a última ocorrência. Esse valor é então convertido para um total de horas.
* **Análise do Atraso:** O tempo de atraso calculado em horas é comparado com o limite máximo de atraso que foi fornecido como parâmetro na linha de comando.
* **Geração de Alerta (Atraso Excedido):** Se o atraso calculado for maior ou igual ao limite permitido, o script entra no modo de alerta. Ele formata uma mensagem detalhada, informando que a integração da Tecmar não envia dados há um determinado número de horas e minutos.
* **Enfileiramento do Alerta:** O script se conecta ao banco de dados **TORRE_CONTROLE** e, para cada destinatário da lista, insere uma nova linha na tabela **alerta_mensagens**. Essa linha contém a mensagem de alerta e os detalhes de envio, colocando a notificação na fila para ser despachada.
* **Finalização (Fluxo Normal):** Se o atraso calculado estiver dentro do limite aceitável, o script considera a integração saudável e encerra sua execução silenciosamente, sem gerar nenhum alerta.

H2: Funções Auxiliares Principais
A lógica do script é executada de forma linear em um fluxo único e não define funções auxiliares próprias. Ele depende inteiramente de funções do módulo externo **tools** para tarefas padronizadas, como a conexão com os bancos de dados (**t.connect_db**, **t.close_db**) e o registro de logs (**t.log2**).

=== METADADOS ===
Nome do arquivo: {nome_arquivo}
Contexto adicional (opcional, pode usar para refinar entendimento): {contexto_extra}

=== CÓDIGO A SER ANALISADO (INÍCIO) ===
{codigo}
=== CÓDIGO A SER ANALISADO (FIM) ===
"""