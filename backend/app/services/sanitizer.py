import re
from typing import Dict, Tuple

class Sanitizer:
    # Regex pour les emails
    EMAIL_REGEX = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    
    # Regex pour les numéros de téléphone (NA et International simple)
    # Nécessite au moins la structure XXX-XXX-XXXX
    PHONE_REGEX = r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'

    @staticmethod
    def sanitize(text: str) -> Tuple[str, Dict[str, str]]:
        """
        Remplace les PII par des placeholders et retourne le texte + le mapping.
        """
        if not text:
            return text, {}
            
        mapping = {}
        sanitized_text = text
        
        # 1. Emails
        emails = re.findall(Sanitizer.EMAIL_REGEX, sanitized_text)
        for i, email in enumerate(list(set(emails))):
            placeholder = f"[EMAIL_{i+1}]"
            mapping[placeholder] = email
            sanitized_text = sanitized_text.replace(email, placeholder)
            
        # 2. Téléphones
        phones = re.findall(Sanitizer.PHONE_REGEX, sanitized_text)
        # Trier par longueur décroissante pour éviter de remplacer des sous-parties
        phones = sorted(list(set(p.strip() for p in phones)), key=len, reverse=True)
        for i, phone in enumerate(phones):
            placeholder = f"[PHONE_{i+1}]"
            mapping[placeholder] = phone
            sanitized_text = sanitized_text.replace(phone, placeholder)
            
        return sanitized_text, mapping

    @staticmethod
    def desanitize(text: str, mapping: Dict[str, str]) -> str:
        """
        Restaure les données originales à partir des placeholders.
        """
        if not text or not mapping:
            return text
            
        restored_text = text
        for placeholder, original in mapping.items():
            restored_text = restored_text.replace(placeholder, original)
            
        return restored_text

# Fonctions utilitaires pour export simple
def sanitize(text: str) -> Tuple[str, Dict[str, str]]:
    return Sanitizer.sanitize(text)

def desanitize(text: str, mapping: Dict[str, str]) -> str:
    return Sanitizer.desanitize(text, mapping)

class SanitizationMap(dict):
    """Alias pour type hint plus clair"""
    pass
