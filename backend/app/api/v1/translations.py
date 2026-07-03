from fastapi import APIRouter, Query
from typing import Optional
from app.services.translation_service import translation_service

router = APIRouter()


@router.get("/translations/supported")
async def get_supported_languages():
    """
    Get list of supported languages.
    Returns language codes and names.
    """
    languages = []
    for code in translation_service.get_supported_languages():
        languages.append({
            'code': code,
            'name': translation_service.get_language_name(code)
        })
    return {'languages': languages}


@router.get("/translations/translate")
async def translate_text(
    text: str = Query(..., description="Text to translate"),
    language: Optional[str] = Query(None, description="Target language (english, kiswahili, spanish, french, german, chinese)")
):
    """
    Translate a text key to the specified language.
    Uses predefined translation keys for UI elements.
    """
    translated = translation_service.translate(text, language)
    return {
        'original': text,
        'translated': translated,
        'language': translation_service.normalize_language_code(language)
    }


@router.post("/translations/translate-dict")
async def translate_dict(
    data: dict,
    language: Optional[str] = Query(None, description="Target language")
):
    """
    Translate all string values in a dictionary.
    Useful for translating report content.
    """
    translated = translation_service.translate_dict(data, language)
    return {
        'original': data,
        'translated': translated,
        'language': translation_service.normalize_language_code(language)
    }
