# Documentação de Dados: Tabela de Situação Logística

## 1. Visão Geral
**Tabela:** `dw.tab_situacao_nota_logi`  
**Objetivo:** Centralizar o status e o rastreamento de operações logísticas, consolidando informações de Pedidos (solicitações de serviço) e Notas Fiscais. Esta tabela atua como a espinha dorsal para o Business Intelligence (BI) logístico, permitindo o acompanhamento de ponta a ponta (recebimento até expedição).

---

## 2. Estrutura Técnica (DDL)

```sql
CREATE TABLE dw.tab_situacao_nota_logi (
    "IDENTIFICADOR" varchar(35) NULL,
    "FILIAL" varchar(2) NULL,
    "NOME_FILIAL" varchar(10) NULL,
    "COD_FORNECEDOR" varchar(15) NULL,
    "RAZ_SOCIAL_REDUZ" varchar(10) NULL,
    "REFERENCIA" int4 NOT NULL,
    "PEDIDO" varchar(20) NULL,
    "NOTA_FISCAL" numeric(20) NULL,
    "SERIE" varchar(3) NULL,
    "VALOR" numeric(17, 2) NULL,
    "VALOR_PEDIDO" numeric(15, 2) NULL,
    "QTDE_ITEM" int4 NULL,
    "SOMA_ITEM" numeric(38, 3) NULL,
    "VOLUME_M3" numeric(15, 6) NULL,
    "QTDE_VOLUME" int4 NULL,
    "QTD_PALETE" int4 NULL,
    "PESO_BRUTO" numeric(17, 6) NULL,
    "PESO_LIQUIDO" numeric(17, 6) NULL,
    "CNPJ_CPF_DES" varchar(8000) NULL,
    "DESTINATARIO" varchar(36) NULL,
    "EMISSAO" timestamp NULL,
    "REC_PEDIDO" timestamp NULL,
    "REC_XML" timestamp NULL,
    "INCONSISTENTE" timestamp NULL,
    "ACOLHIDO" timestamp NULL,
    "PLANO_GERADO" timestamp NULL,
    "ONDA_GERADA" timestamp NULL,
    "INI_SEPARACAO" timestamp NULL,
    "FIM_SEPARACAO" timestamp NULL,
    "INI_CONFERENCIA" timestamp NULL,
    "FIM_CONFERENCIA" timestamp NULL,
    "PER_CONF" numeric(38, 2) NULL,
    "INI_CHECKOUT" timestamp NULL,
    "FIM_CHECKOUT" timestamp NULL,
    "USU_CHECKOUT" varchar(8) NULL,
    "CON_SEPARACAO" timestamp NULL,
    "EMB_FINALIZADO" timestamp NULL,
    "EXPEDIDO" timestamp NULL,
    "STA_NOTA" varchar(24) NULL,
    "SIT_SOL" varchar(1) NULL,
    "LISTA" int4 NULL,
    "CESV" varchar(10) NULL,
    "CHAVE_NFE" varchar(255) NULL,
    "TRANPORTADORA" varchar(36) NULL,
    "USUARIO_CONF" varchar(8) NULL,
    "NOME_CONFERENTE" varchar(30) NULL,
    "USUARIO_SEP" varchar NULL,
    "NOME_SEPARADOR" varchar NULL,
    "DAT_INCLUSAO" timestamp NULL,
    id serial4 NOT NULL,
    last_updated timestamp DEFAULT CURRENT_TIMESTAMP NULL,
    CONSTRAINT pk_tab_situacao_nota_logi PRIMARY KEY (id)
)
WITH (
    autovacuum_enabled=false
);
```

---

## 3. Dicionário de Dados

| Coluna | Tipo | Descrição | Exemplo |
| :--- | :--- | :--- | :--- |
| **IDENTIFICADOR** | varchar(35) | Chave composta única (Junção de `FILIAL` + `REFERENCIA`). | `02_519855` |
| **FILIAL** | varchar(2) | Código identificador da filial. | `02` |
| **NOME_FILIAL** | varchar(10) | Nome da filial (Ex: MAO = Manaus). | `SUP MAO I` |
| **COD_FORNECEDOR** | varchar(15) | Código único do fornecedor no sistema. | `007703111000103` |
| **RAZ_SOCIAL_REDUZ** | varchar(10) | Razão social abreviada do fornecedor. | `HARMAN` |
| **REFERENCIA** | int4 | Identificador numérico da referência do pedido/nota. | `519855` |
| **PEDIDO** | varchar(20) | Identificador do pedido (Pode ser nulo se for entrada direta por nota). | `2401202303` |
| **NOTA_FISCAL** | numeric(20) | Número da nota fiscal (Numérico). Se existir, `PEDIDO` pode não existir. | `17727` |
| **SERIE** | varchar(3) | Série da nota fiscal. Depende da coluna `NOTA_FISCAL`. | `16` |
| **VALOR** | numeric(17,2) | Valor total da nota fiscal (Monetário). | `50562.65` |
| **VALOR_PEDIDO** | numeric(15,2) | Valor do pedido informado pelo cliente. | `7135.59` |
| **QTDE_ITEM** | int4 | Contagem de SKUs (itens distintos) na carga. | `12` |
| **SOMA_ITEM** | numeric(38,3) | Quantidade total de unidades de itens na carga. | `300.000` |
| **VOLUME_M3** | numeric(15,6) | Cubagem da carga em metros cúbicos. | `33.233000` |
| **QTDE_VOLUME** | int4 | Quantidade de volumes físicos (caixas). | `27` |
| **QTD_PALETE** | int4 | Quantidade de paletes ocupados. | `23` |
| **PESO_BRUTO** | numeric(17,6) | Peso total (carga + embalagem + paletes) em Kg. | `7828.556000` |
| **PESO_LIQUIDO** | numeric(17,6) | Peso apenas da mercadoria em Kg. | `6254.945000` |
| **CNPJ_CPF_DES** | varchar(8000) | Documento do destinatário (Cliente final). | `004.402.223/0001-01` |
| **DESTINATARIO** | varchar(36) | Nome/Razão Social do destinatário. | `BIC AMAZONIA S/A` |
| **EMISSAO** | timestamp | Data de emissão do documento (saída do cliente). | `2023-02-09 17:57:00` |
| **REC_PEDIDO** | timestamp | Data em que o sistema recebeu a carga/pedido do cliente. | `2023-02-09 17:57:00` |
| **REC_XML** | timestamp | Data de recebimento do XML da Nota Fiscal. | `2023-02-10 15:07:00` |
| **INCONSISTENTE** | timestamp | Data de registro de avaria, acidente ou erro de processo. | `2023-05-10 16:54:00` |
| **ACOLHIDO** | timestamp | Data de entrada/acolhimento no sistema Logix. | `2023-05-10 16:58:00` |
| **PLANO_GERADO** | timestamp | Data de geração do plano de separação pelo sistema. | `2023-03-08 16:53:00` |
| **ONDA_GERADA** | timestamp | Data de geração da onda de separação. | `2023-03-08 17:04:00` |
| **INI_SEPARACAO** | timestamp | Data de início da operação física de separação. | `2023-03-09 09:54:00` |
| **FIM_SEPARACAO** | timestamp | Data de término da operação física de separação. | `2023-03-09 09:55:00` |
| **INI_CONFERENCIA** | timestamp | Data de início da conferência da carga. | `2023-03-09 09:56:27` |
| **FIM_CONFERENCIA** | timestamp | Data de término da conferência da carga. | `2023-01-31 19:12:41` |
| **PER_CONF** | numeric(38,2) | Percentual de progresso da conferência (0 a 100). | `100.00` |
| **INI_CHECKOUT** | timestamp | Data de início do empacotamento (frações menores). | `2023-03-06 15:24:09` |
| **FIM_CHECKOUT** | timestamp | Data de término do empacotamento. | `2023-03-06 15:24:10` |
| **USU_CHECKOUT** | varchar(8) | Usuário Logix que realizou o checkout. | `002562` ou `RAIN` |
| **CON_SEPARACAO** | timestamp | Confirmação de separação (Aguarda NF no fluxo de pedido). | `2025-02-03 16:28:00` |
| **EMB_FINALIZADO** | timestamp | Data de finalização do embarque (carga pronta para sair). | `2025-02-05 11:45:00` |
| **EXPEDIDO** | timestamp | Data de saída do caminhão pela portaria. | `2023-09-20 17:14:00` |
| **STA_NOTA** | varchar(24) | Descrição textual da situação atual da nota. | `EXPEDIDO` |
| **SIT_SOL** | varchar(1) | Código da situação da solicitação. **'E' = Expedido**. | `E` |
| **LISTA** | int4 | ID da lista de separação gerada. | `243456` |
| **CESV** | varchar(10) | ID do Controle de Entrada e Saída de Veículos. | `2025001957` |
| **CHAVE_NFE** | varchar(255) | Chave de acesso da Nota Fiscal Eletrônica. | `312502...` |
| **TRANPORTADORA** | varchar(36) | Nome da transportadora responsável. (Obs: Typo no DB). | `SUPPLOG ARMAZENS` |
| **USUARIO_CONF** | varchar(8) | ID do usuário que fez a conferência. | `000609` |
| **NOME_CONFERENTE** | varchar(30) | Nome legível do conferente. | `ALEXANDER SILVA` |
| **USUARIO_SEP** | varchar | ID do usuário que fez a separação. | `BIANCA` |
| **NOME_SEPARADOR** | varchar | Nome legível do separador. | `BIANCA RODRIGUES` |
| **DAT_INCLUSAO** | timestamp | Data de inclusão do registro no Logix. | `2023-09-30 10:21:13` |

---

## 4. Mapeamentos Oficiais (De/Para)

Esta seção documenta os valores exatos (Enums) presentes no banco de dados para garantir a precisão nas consultas e filtros.

### 4.1. Unidades e Filiais
Mapeamento entre o código numérico (`FILIAL`) e o nome comercial (`NOME_FILIAL`).

| Código (FILIAL) | Nome (NOME_FILIAL) | Descrição / Localização |
| :--- | :--- | :--- |
| `01` | **SUP IPO** | Ipojuca (PE) |
| `02` | **SUP MAO I** | Manaus I (AM) |
| `03` | **SUP BAR** | Barueri (SP) |
| `04` | **SUP UDI** | Uberlândia (MG) |
| `05` | **SUP MAO II** | Manaus II (AM) |
| `06` | **MAO ENTREP** | Manaus Entreposto (AM) |

### 4.2. Status da Operação (Workflow)
A coluna `STA_NOTA` é a descrição legível, enquanto `SIT_SOL` é o código de sistema. A tabela abaixo ordena o fluxo lógico e mostra a correspondência exata.

| Código (SIT_SOL) | Descrição (STA_NOTA) | Fase do Processo |
| :--- | :--- | :--- |
| **A** | **ACOLHIDO** | **1. Entrada** (Recebimento da demanda) |
| **N** | **AG. NOTA FISCAL** | **1. Entrada** (Aguardando faturamento) |
| **L** | **PLANO GERADO** | **2. Planejamento** (Otimização de carga) |
| **O** | **ONDA GERADA** | **2. Planejamento** (Envio para operação) |
| **S** | **EM SEPARAÇÃO** | **3. Operação** (Picking) |
| **3** | **AG. BAIXA ESTOQUE** | **3. Operação** (Movimentação sistêmica) |
| **4** | **BAIXADO ESTOQUE** | **3. Operação** (Conclusão de baixa) |
| **F** | **CONFERÊNCIA** | **3. Operação** (Checking/Auditoria) |
| **R** | **RECONF. EMBARQUE** | **3. Operação** (Revisão pontual) |
| **Z** | **EMBARQUE FINALIZADO** | **4. Saída** (Carga pronta para doca) |
| **V** | **AG. VEÍCULO NA DOCA** | **4. Saída** (Aguardando transporte) |
| **Q** | **EMBARQUE INICIADO** | **4. Saída** (Carregamento físico) |
| **X** | **AG. EXPEDIÇÃO** | **4. Saída** (Documentação final) |
| **E** | **EXPEDIDO** | **5. Conclusão** (Caminhão saiu - Status Final Sucesso) |
| **U** | **AG. DESEMBARQUE** | **Exceção** (Processo reverso) |
| **B** | **BLOQUEADO** | **Exceção** (Parado por pendência) |
| **I** | **INCONSISTENTE** | **Exceção** (Erro de estoque/dados) |
| **C** | **CANCELADO** | **Fim** (Processo abortado) |

---

## 5. Regras de Negócio e Fluxos Operacionais

Existem dois fluxos principais que alimentam esta tabela. A coluna `SIT_SOL` (Situação da Solicitação) é atualizada conforme o avanço das etapas.

### Fluxo A: Pedido (Solicitação de Serviço)
*Ocorre quando o cliente solicita uma separação para que a Supporte verifique a carga antes de gerar a Nota Fiscal.*

1.  **Entrada:** Cliente faz o pedido.
    * Campos preenchidos: `ACOLHIDO`, `REC_PEDIDO`, `DAT_INCLUSAO`, `EMISSAO` (do pedido).
2.  **Planejamento:**
    * Geração de Onda: `ONDA_GERADA`.
    * Geração de Plano: `PLANO_GERADO`, `LISTA`.
3.  **Operação (Armazém):**
    * Separação: `INI_SEPARACAO` -> `FIM_SEPARACAO`. Usuários: `USUARIO_SEP`, `NOME_SEPARADOR`.
    * Conferência: `INI_CONFERENCIA` -> `FIM_CONFERENCIA`. Usuários: `USUARIO_CONF`.
    * Progresso: A coluna `PER_CONF` varia durante este processo.
4.  **Confirmação:**
    * Confirmação da Separação: `CON_SEPARACAO`.
    * *Ação Externa:* Supporte avisa o cliente -> Cliente emite a NF -> Cliente retorna NF.
    * Atualização de Dados Fiscais: `REC_XML`, `NOTA_FISCAL`, `SERIE`, `CHAVE_NFE`.
5.  **Saída:**
    * Embarque: `EMB_FINALIZADO`.
    * Expedição (Baixa): `EXPEDIDO`.
    * **Encerramento:** Coluna `SIT_SOL` recebe valor **'E'**.

### Fluxo B: Nota Fiscal (Entrada Direta)
*Ocorre quando a mercadoria já chega com a Nota Fiscal emitida.*

1.  **Entrada:** Acolhimento da carga com NF.
    * Campos preenchidos: `EMISSAO`, `REC_XML`, `NOTA_FISCAL`, `SERIE`, `CHAVE_NFE`.
2.  **Planejamento:**
    * Geração de Onda: `ONDA_GERADA`.
    * Geração de Plano: `PLANO_GERADO`, `LISTA`.
3.  **Operação (Armazém):**
    * Separação: `INI_SEPARACAO` -> `FIM_SEPARACAO`.
    * Conferência: `INI_CONFERENCIA` -> `FIM_CONFERENCIA`.
    * *Nota:* Não há etapa de `CON_SEPARACAO` (Confirmação) pois a NF já existe.
4.  **Saída:**
    * Embarque: `EMB_FINALIZADO`.
    * Expedição (Baixa): `EXPEDIDO`.
    * **Encerramento:** Coluna `SIT_SOL` recebe valor **'E'**.

---

## 6. Relacionamentos e Insights

### Relacionamentos com Outras Tabelas
Para análises mais profundas (ex: detalhe de produtos), esta tabela deve ser cruzada com tabelas auxiliares:

* **Tabelas de Itens:** `pec_roteirização_logi` ou `item_logi`.
* **Chave de Junção (Join Key):**
    * Na tabela atual: Coluna `IDENTIFICADOR` (Composta por Filial + Referência).
    * Nas tabelas destino: Geralmente colunas como `filial_sc` e `solic_carg` (referência).

### Potencial Analítico (Perguntas Respondíveis)
Com os dados estruturados desta forma, o Agente de IA é capaz de responder:

1.  **Rastreabilidade:** "Qual a situação atual do pedido X ou da nota Y?"
2.  **Previsão:** "Qual a previsão de expedição baseada na média histórica deste cliente?"
3.  **Histórico de Vendas:** "Qual foi a última vez que o cliente X comprou o produto Y?" (Necessário Join).
4.  **Gargalos Operacionais:** "Qual o tempo médio entre o Fim da Separação e o Início da Conferência?"
5.  **Performance:** "Qual separador processou mais volumes hoje?"