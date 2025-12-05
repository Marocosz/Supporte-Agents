"""
MÓDULO: app/services/security.py
Responsável por mascarar dados sensíveis (PII e Segredos Comerciais) antes de enviar para a IA.
"""
import logging
from presidio_analyzer import AnalyzerEngine, PatternRecognizer
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger("security")

class DataSanitizer:
    def __init__(self):
        # Inicializa o motor de análise (Score 0.4 significa que ele é bem rigoroso)
        self.analyzer = AnalyzerEngine(default_score_threshold=0.4)
        self.anonymizer = AnonymizerEngine()
        
        # --- 1. LISTA DE EMPRESAS E PARCEIROS (DENY LIST) ---
        # Adicione aqui todos os nomes que não podem vazar
        empresas_proibidas = [
            "Supporte Logística", 
            "Supporte", 
            "Cliente X", 
            "Fornecedor Y",
            "Coca-Cola", 
            "Samsung"
        ]
        
        # Cria o reconhecedor para Empresas
        empresa_recognizer = PatternRecognizer(
            supported_entity="EMPRESA_CONFIDENCIAL",
            deny_list=empresas_proibidas
        )
        self.analyzer.registry.add_recognizer(empresa_recognizer)

        # --- 2. LISTA DE SEGREDOS DE PROJETO ---
        segredos_projeto = [
            "Projeto Zeus", 
            "Operação Fênix", 
            "Margem Líquida", 
            "Budget 2025"
        ]
        
        # Cria o reconhecedor para Segredos
        segredo_recognizer = PatternRecognizer(
            supported_entity="SEGREDO_NEGOCIO",
            deny_list=segredos_projeto
        )
        self.analyzer.registry.add_recognizer(segredo_recognizer)

    def sanitize(self, text: str) -> str:
        """
        Recebe um texto com dados reais e retorna o texto mascarado.
        """
        if not text:
            return ""

        try:
            # Analisa o texto procurando entidades padrões e as nossas customizadas
            results = self.analyzer.analyze(
                text=text,
                language='pt',
                entities=[
                    # Padrão (Detectado via IA/Spacy)
                    "CPF", "EMAIL_ADDRESS", "PHONE_NUMBER", "PERSON", "CREDIT_CARD",
                    # Customizados (Detectados via Lista Exata)
                    "EMPRESA_CONFIDENCIAL", "SEGREDO_NEGOCIO"
                ]
            )

            # Substitui pelo nome genérico
            anonymized_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=results,
                operators={
                    "DEFAULT": OperatorConfig("replace", {"new_value": "<DADO_SENSIVEL>"}),
                    "CPF": OperatorConfig("replace", {"new_value": "<CPF>"}),
                    "PERSON": OperatorConfig("replace", {"new_value": "<NOME_PESSOA>"}),
                    "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "<EMAIL>"}),
                    # Nossas regras novas:
                    "EMPRESA_CONFIDENCIAL": OperatorConfig("replace", {"new_value": "<EMPRESA>"}),
                    "SEGREDO_NEGOCIO": OperatorConfig("replace", {"new_value": "<ESTRATEGIA>"}),
                }
            )

            return anonymized_result.text

        except Exception as e:
            logger.error(f"Erro ao sanitizar dados: {e}")
            # Em caso de erro, por segurança, retornamos o texto original 
            # (ou poderia retornar string vazia se for crítico)
            return text

# Instância Singleton
sanitizer = DataSanitizer()