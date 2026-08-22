# -*- coding: utf-8 -*-
"""
Package locales - Traductions multilingues

Ce package contient toutes les traductions pour le bot.
"""

from . import fr
from . import en

AVAILABLE_LANGUAGES = {
    'fr': fr,
    'en': en
}

def get_locale(lang_code: str):
    """
    Récupère le module de traduction pour une langue
    
    Args:
        lang_code (str): Code de langue ('fr', 'en')
    
    Returns:
        module: Module de traduction
    """
    return AVAILABLE_LANGUAGES.get(lang_code, fr)

def get_text(lang_code: str, key: str, **kwargs) -> str:
    """
    Récupère une traduction avec variables
    
    Args:
        lang_code (str): Code de langue
        key (str): Clé de traduction
        **kwargs: Variables à remplacer
    
    Returns:
        str: Texte traduit
    """
    locale = get_locale(lang_code)
    return locale.get_text(key, **kwargs)

__all__ = [
    'fr',
    'en',
    'AVAILABLE_LANGUAGES',
    'get_locale',
    'get_text'
]

__version__ = '1.0.0'
__supported_languages__ = ['fr', 'en']
