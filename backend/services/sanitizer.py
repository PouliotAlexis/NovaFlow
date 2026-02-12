"""
NovaFlow - Module de Sanitization Réversible (Reversible Redaction)

Ce module est le cœur de la sécurité de NovaFlow en mode Cloud.
Il remplace les entités sensibles (noms, emails, téléphones) par des tokens
AVANT l'envoi à l'IA, puis restaure les vraies valeurs APRÈS la réponse.

Flux :
1. Input: "Envoie un mail à Jean Dupont à jean@email.com"
2. Sanitize: "Envoie un mail à [PERSON_1] à [EMAIL_1]"
   -> Map: {"[PERSON_1]": "Jean Dupont", "[EMAIL_1]": "jean@email.com"}
3. AI répond avec les tokens
4. Desanitize: Les tokens sont remplacés par les vraies valeurs
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class SanitizationMap:
    """Stocke le mapping bidirectionnel entre tokens et valeurs réelles."""
    _token_to_value: Dict[str, str] = field(default_factory=dict)
    _value_to_token: Dict[str, str] = field(default_factory=dict)
    _counters: Dict[str, int] = field(default_factory=dict)

    def add(self, entity_type: str, value: str) -> str:
        """Ajoute une entité et retourne le token correspondant.
        
        Si la valeur existe déjà, retourne le token existant.
        """
        if value in self._value_to_token:
            return self._value_to_token[value]

        # Incrémenter le compteur pour ce type d'entité
        count = self._counters.get(entity_type, 0) + 1
        self._counters[entity_type] = count

        token = f"[{entity_type}_{count}]"
        self._token_to_value[token] = value
        self._value_to_token[value] = token
        return token

    def get_value(self, token: str) -> str | None:
        """Récupère la valeur réelle à partir d'un token."""
        return self._token_to_value.get(token)

    def get_token(self, value: str) -> str | None:
        """Récupère le token à partir d'une valeur réelle."""
        return self._value_to_token.get(value)

    @property
    def token_map(self) -> Dict[str, str]:
        """Retourne le dictionnaire token -> valeur (lecture seule)."""
        return dict(self._token_to_value)

    def clear(self) -> None:
        """Réinitialise le mapping."""
        self._token_to_value.clear()
        self._value_to_token.clear()
        self._counters.clear()


# === Patterns de détection (Regex - PAS d'IA) ===

# Emails
EMAIL_PATTERN = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
)

# Numéros de téléphone (formats nord-américains et internationaux)
PHONE_PATTERN = re.compile(
    r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b'
)

# Dates (formats courants)
DATE_PATTERN = re.compile(
    r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
    r'|\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
)

# URLs
URL_PATTERN = re.compile(
    r'https?://[^\s<>\"\']+|www\.[^\s<>\"\']+' 
)

# Montants d'argent
MONEY_PATTERN = re.compile(
    r'[$]\s?\d+(?:\s?\d{3})*(?:[.,]\d{1,2})?(?:\s?(?:CAD|USD|EUR))?'
    r'|\d+(?:\s?\d{3})*(?:[.,]\d{1,2})?\s?(?:CAD|USD|EUR|€)'
)


# === Fonctions principales ===

def sanitize(text: str, extra_entities: List[str] | None = None) -> Tuple[str, SanitizationMap]:
    """
    Nettoie un texte en remplaçant les entités sensibles par des tokens.
    
    Args:
        text: Le texte à nettoyer.
        extra_entities: Liste optionnelle de mots/noms supplémentaires à censurer
                       (fournis manuellement par l'utilisateur, ex: noms de profs).
    
    Returns:
        Tuple (texte_nettoyé, mapping_de_restauration)
    """
    sanitization_map = SanitizationMap()
    sanitized_text = text

    # 1. Remplacer les entités fournies manuellement (les plus fiables)
    if extra_entities:
        # Trier par longueur décroissante pour éviter les remplacements partiels
        sorted_entities = sorted(extra_entities, key=len, reverse=True)
        for entity in sorted_entities:
            if entity in sanitized_text:
                token = sanitization_map.add("CUSTOM", entity)
                sanitized_text = sanitized_text.replace(entity, token)

    # 2. Remplacer les URLs (avant les emails pour éviter les conflits)
    for match in URL_PATTERN.finditer(sanitized_text):
        value = match.group()
        token = sanitization_map.add("URL", value)
        sanitized_text = sanitized_text.replace(value, token)

    # 3. Remplacer les emails
    for match in EMAIL_PATTERN.finditer(sanitized_text):
        value = match.group()
        token = sanitization_map.add("EMAIL", value)
        sanitized_text = sanitized_text.replace(value, token)

    # 4. Remplacer les montants d'argent (AVANT les téléphones pour éviter collision)
    for match in MONEY_PATTERN.finditer(sanitized_text):
        value = match.group()
        token = sanitization_map.add("MONEY", value)
        sanitized_text = sanitized_text.replace(value, token)

    # 5. Remplacer les dates
    for match in DATE_PATTERN.finditer(sanitized_text):
        value = match.group()
        token = sanitization_map.add("DATE", value)
        sanitized_text = sanitized_text.replace(value, token)

    # 6. Remplacer les numéros de téléphone (APRÈS montants et dates)
    for match in PHONE_PATTERN.finditer(sanitized_text):
        value = match.group()
        token = sanitization_map.add("PHONE", value)
        sanitized_text = sanitized_text.replace(value, token)

    return sanitized_text, sanitization_map


def desanitize(text: str, sanitization_map: SanitizationMap) -> str:
    """
    Restaure les vraies valeurs dans un texte en remplaçant les tokens.
    
    Args:
        text: Le texte contenant des tokens (ex: [PERSON_1]).
        sanitization_map: Le mapping créé lors de la sanitization.
    
    Returns:
        Le texte avec les vraies valeurs restaurées.
    """
    result = text
    # Trier par longueur de token décroissante pour éviter les remplacements partiels
    for token, value in sorted(
        sanitization_map.token_map.items(), 
        key=lambda x: len(x[0]), 
        reverse=True
    ):
        result = result.replace(token, value)
    return result
