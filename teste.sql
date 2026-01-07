ALTER VIEW [dbo].[VW_API_CONTA_ORDEM]
AS

/***************************************************************************
View para recuperar o XML da conta e ordem.
Objetivo: Ler um campo de texto livre (Observação), extrair números de notas
          e cruzar com tabelas oficiais do sistema.

Autor: TIAGO LUCIO     
Criação: 08/10/2024 

Editor: Marcos Rodrigues
Edição: 07/01/2026
***************************************************************************/

SELECT 
    SF2.F2_DOC AS NUM_CONTA_E_ORDEM,
    SF2.F2_SERIE AS SERIE_CONTA_E_ORDEM,
    SA1.A1_CGC AS CGC_CLIENTE,
    SA1.A1_NOME AS NOME_CLIENTE,
    
    /* ---------------------------------------------------------------------------------
       PARTE 4: FORMATAÇÃO FINAL (ZERO PADDING - TÉCNICA RIGHT)
       Transforma o número extraído (ex: "123") no padrão do sistema (ex: "000000123").
       
       Lógica da Função RIGHT:
       1. Concatenamos uma string de zeros com o número limpo:
          '000000000' + '123' = '000000000123'
       2. A função RIGHT pega apenas os últimos N caracteres da direita.
          RIGHT('000000000123', 9) = '000000123'
    --------------------------------------------------------------------------------- */
    CAST(RIGHT('000000000' + RTRIM(Calculos.NumRaw), 9) AS VARCHAR(9)) AS NUM_NOTA_CLIENTE,
    CAST(RIGHT('000' + RTRIM(Calculos.SerieRaw), 3) AS VARCHAR(3)) AS SERIE_NOTA_CLIENTE,

    DTC.DTC_NFEID AS CHV_NF_CLIENTE,
    SF2.F2_CHVNFE AS CHV_CONTA_E_ORDEM,
    TSS.XML_ERP AS XML_CONTA_E_ORDEM

FROM SF2010 SF2 WITH (NOLOCK)

/* ---------------------------------------------------------------------------------
   ETAPA 1: LIMPEZA INICIAL (Var1)
   Objetivo: Padronizar o texto para facilitar a contagem de posições.
   
   Exemplo de Entrada (F2_MENNOTA): "REF. NF: 12345 SERIE: 1 EMISSAO: 01/01"
   Ação: Remove todos os dois pontos (:).
   Exemplo de Saída (TxtLimpo):     "REF. NF  12345 SERIE  1 EMISSAO  01/01"
--------------------------------------------------------------------------------- */
CROSS APPLY (
    SELECT REPLACE(SF2.F2_MENNOTA, ':', '') AS TxtLimpo
) AS Var1

/* ---------------------------------------------------------------------------------
   ETAPA 2: MAPEAMENTO DE POSIÇÕES (Var2)
   Objetivo: Descobrir em qual número de caractere cada palavra-chave começa.
   Função CHARINDEX: Retorna o índice inicial da palavra.
   
   Usando o TxtLimpo: "REF. NF  12345 SERIE  1..."
                       12345678...
   
   PosNF: Encontra onde começa o "NF". (No exemplo acima, índice 6)
   PosSerie: Encontra onde começa "SERIE". (Digamos, índice 16)
   PosEmissao: Encontra onde começa "EMISSAO".
--------------------------------------------------------------------------------- */
CROSS APPLY (
    SELECT 
        CHARINDEX('NF', Var1.TxtLimpo) AS PosNF,
        CHARINDEX('SERIE', Var1.TxtLimpo) AS PosSerie,
        CHARINDEX('EMISSAO', Var1.TxtLimpo) AS PosEmissao
) AS Var2

/* ---------------------------------------------------------------------------------
   ETAPA 3: MATEMÁTICA DE EXTRAÇÃO DE TEXTO (Calculos)
   Objetivo: Recortar o texto que está ENTRE as palavras chaves.
   Função SUBSTRING(Texto, Inicio, Tamanho)
   
   Cálculo do Número da Nota (NumRaw):
   1. Inicio: Onde achou 'NF' + 3 caracteres (tamanho de 'NF' + 1 espaço).
   2. Tamanho: (Onde começa 'SERIE') - (Onde começa 'NF') - 3.
      Isso calcula a distância exata entre as duas palavras.
   
   Exemplo Prático:
   Se 'NF' está na posição 6 e 'SERIE' na posição 16.
   Inicio do corte = 6 + 3 = 9.
   Tamanho do corte = 16 - 6 - 3 = 7 caracteres.
   Resultado: Pega o que estiver nesses 7 espaços (o número da nota).
--------------------------------------------------------------------------------- */
CROSS APPLY (
    SELECT
        -- Pega o texto entre "NF" e "SERIE"
        SUBSTRING(Var1.TxtLimpo, Var2.PosNF + 3, Var2.PosSerie - Var2.PosNF - 3) AS NumRaw,
        
        -- Pega o texto entre "SERIE" e "EMISSAO"
        -- Mesma lógica: Posição final - Posição inicial - Compensação de caracteres
        SUBSTRING(Var1.TxtLimpo, Var2.PosSerie + 6, Var2.PosEmissao - Var2.PosSerie - 6) AS SerieRaw
) AS Calculos

INNER JOIN SD2010 SD2 WITH (NOLOCK) 
    ON SF2.F2_FILIAL = SD2.D2_FILIAL
    AND SF2.F2_DOC = SD2.D2_DOC
    AND SF2.F2_SERIE = SD2.D2_SERIE
    AND SF2.F2_CLIENTE = SD2.D2_CLIENTE
    AND SF2.F2_LOJA = SD2.D2_LOJA
    AND SF2.D_E_L_E_T_ = SD2.D_E_L_E_T_

INNER JOIN SA1010 SA1 WITH (NOLOCK) 
    ON SF2.F2_CLIENTE = SA1.A1_COD
    AND SF2.F2_LOJA = SA1.A1_LOJA
    AND SF2.D_E_L_E_T_ = SA1.D_E_L_E_T_

/* ---------------------------------------------------------------------------------
   JOIN COM DOCUMENTO DE TRANSPORTE (DTC)
   Aqui cruzamos a nota extraída do texto com a tabela real de transporte.
   
   Importante: Aplicamos a mesma formatação RIGHT nos dois lados da igualdade.
   Isso garante que "000123" seja igual a "123   " após a padronização.
--------------------------------------------------------------------------------- */
INNER JOIN DTC010 DTC WITH (NOLOCK) 
    ON SF2.F2_FILIAL = DTC.DTC_FILDOC
    AND SF2.F2_CLIENTE = DTC.DTC_CLIDES
    AND SF2.F2_LOJA = DTC.DTC_LOJDES
    AND SF2.D_E_L_E_T_ = DTC.D_E_L_E_T_
    
    -- Comparação do Número da Nota (Padronizado para 9 dígitos com Zeros à Esquerda)
    AND RIGHT('000000000' + RTRIM(Calculos.NumRaw), 9) = RIGHT('000000000' + RTRIM(DTC.DTC_NUMNFC), 9)
    
    -- Comparação da Série (Padronizado para 3 dígitos com Zeros à Esquerda)
    AND RIGHT('000' + RTRIM(Calculos.SerieRaw), 3) = RIGHT('000' + RTRIM(DTC.DTC_SERNFC), 3)

INNER JOIN TSSPRD30..SPED050 TSS WITH (NOLOCK) 
    ON SF2.F2_CHVNFE COLLATE Latin1_General_100_BIN = TSS.DOC_CHV
    AND SF2.D_E_L_E_T_ COLLATE Latin1_General_100_BIN = TSS.D_E_L_E_T_

WHERE SF2.D_E_L_E_T_ = ''
    AND SF2.F2_MENNOTA LIKE '%CONTA E ORDEM%'
    AND SD2.D2_CF IN ('5923', '6923', '7923')
    AND SF2.F2_EMISSAO >= FORMAT(DATEADD(month, -3, GETDATE()), 'yyyyMMdd', 'en-US');