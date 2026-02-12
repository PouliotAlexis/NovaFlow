"""
Tests pour le module de Sanitization Réversible.

Ces tests vérifient que :
1. Les entités sensibles sont correctement détectées et remplacées.
2. La desanitization restaure parfaitement les valeurs originales.
3. Le mapping est cohérent et bidirectionnel.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.sanitizer import sanitize, desanitize


def test_email_sanitization():
    """Les emails doivent être remplacés par des tokens."""
    text = "Contacte jean.dupont@gmail.com pour le projet."
    sanitized, san_map = sanitize(text)

    assert "jean.dupont@gmail.com" not in sanitized
    assert "[EMAIL_1]" in sanitized

    # Vérifier que la desanitization restaure l'original
    restored = desanitize(sanitized, san_map)
    assert restored == text


def test_phone_sanitization():
    """Les numéros de téléphone doivent être remplacés."""
    text = "Appelle-moi au 514-555-1234."
    sanitized, san_map = sanitize(text)

    assert "514-555-1234" not in sanitized
    assert "[PHONE_1]" in sanitized

    restored = desanitize(sanitized, san_map)
    assert restored == text


def test_money_sanitization():
    """Les montants d'argent doivent être remplacés."""
    text = "Le loyer est de $1500 par mois."
    sanitized, san_map = sanitize(text)

    assert "$1500" not in sanitized
    assert "[MONEY_1]" in sanitized

    restored = desanitize(sanitized, san_map)
    assert restored == text


def test_url_sanitization():
    """Les URLs doivent être remplacées."""
    text = "Consulte le site https://moodle.univ.ca/cours/123."
    sanitized, san_map = sanitize(text)

    assert "https://moodle.univ.ca/cours/123" not in sanitized
    assert "[URL_1]" in sanitized

    restored = desanitize(sanitized, san_map)
    assert restored == text


def test_date_sanitization():
    """Les dates doivent être remplacées."""
    text = "La remise est le 12/03/2026."
    sanitized, san_map = sanitize(text)

    assert "12/03/2026" not in sanitized
    assert "[DATE_1]" in sanitized

    restored = desanitize(sanitized, san_map)
    assert restored == text


def test_custom_entities():
    """Les entités fournies manuellement doivent être remplacées."""
    text = "Envoie un mail à Jean Dupont pour le projet Aurora."
    custom = ["Jean Dupont", "Aurora"]
    sanitized, san_map = sanitize(text, extra_entities=custom)

    assert "Jean Dupont" not in sanitized
    assert "Aurora" not in sanitized
    assert "[CUSTOM_1]" in sanitized
    assert "[CUSTOM_2]" in sanitized

    restored = desanitize(sanitized, san_map)
    assert restored == text


def test_multiple_entities():
    """Plusieurs entités du même type doivent avoir des tokens différents."""
    text = "Mail de alice@test.com et bob@test.com."
    sanitized, san_map = sanitize(text)

    assert "alice@test.com" not in sanitized
    assert "bob@test.com" not in sanitized
    assert "[EMAIL_1]" in sanitized
    assert "[EMAIL_2]" in sanitized

    restored = desanitize(sanitized, san_map)
    assert restored == text


def test_complex_scenario():
    """Scénario complet : plusieurs types d'entités mélangées."""
    text = (
        "Bonjour Prof. Martin, l'examen est le 15/04/2026. "
        "Envoyez les résultats à martin@universite.ca. "
        "Le coût est de $250 CAD. "
        "Plus d'infos sur https://portail.universite.ca."
    )
    custom = ["Prof. Martin"]
    sanitized, san_map = sanitize(text, extra_entities=custom)

    # Aucune donnée sensible ne doit rester
    assert "Prof. Martin" not in sanitized
    assert "martin@universite.ca" not in sanitized
    assert "$250" not in sanitized
    assert "https://portail.universite.ca" not in sanitized
    assert "15/04/2026" not in sanitized

    # La restauration doit être parfaite
    restored = desanitize(sanitized, san_map)
    assert restored == text


def test_no_entities():
    """Un texte sans entités sensibles ne doit pas être modifié."""
    text = "Ceci est un texte sans données sensibles."
    sanitized, san_map = sanitize(text)

    assert sanitized == text
    assert len(san_map.token_map) == 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
