"""
VEKTRA Translation Service
==========================
Handles multi-language support for reports and UI elements.
Supports English, Kiswahili, Spanish, French, German, Chinese.
"""

from typing import Dict, Optional

# Translation dictionary for key UI elements and report sections
TRANSLATIONS = {
    'en': {
        'vektra_report': 'VEKTRA Report',
        'weekly_report': 'Weekly Report',
        'monthly_report': 'Monthly Report',
        'quarterly_report': 'Quarterly Report',
        'annual_report': 'Annual Report',
        'trajectory_status': 'Trajectory Status',
        'your_wins': 'Your Wins This Week',
        'silent_killers': 'Silent Killers',
        'numbers_dont_lie': 'The Numbers Don\'t Lie',
        'next_week_directive': 'Next Week Directive',
        'key_metrics': 'Key Metrics',
        'financial_summary': 'Financial Summary',
        'total_income': 'Total Income',
        'total_expenses': 'Total Expenses',
        'net_cash_flow': 'Net Cash Flow',
        'total_saved': 'Total Saved/Invested',
        'vektra_score': 'VEKTRA Score',
        'average_mood': 'Average Mood',
        'average_energy': 'Average Energy',
        'average_focus': 'Average Focus',
        'average_sleep': 'Average Sleep',
        'days_logged': 'Days Logged',
        'goal_hit_rate': 'Goal Hit Rate',
        'survival_runway': 'Survival Runway',
        'happy_birthday': 'Happy Birthday',
        'vector_magnitude_direction': 'Vector = Magnitude × Direction',
        'rising': 'RISING',
        'flat': 'FLAT',
        'declining': 'DECLINING',
    },
    'sw': {
        'vektra_report': 'Ripoti ya VEKTRA',
        'weekly_report': 'Ripoti ya Wiki',
        'monthly_report': 'Ripoti ya Mwezi',
        'quarterly_report': 'Ripoti ya Robo',
        'annual_report': 'Ripoti ya Mwaka',
        'trajectory_status': 'Hali ya Mwelekeo',
        'your_wins': 'Shinda Zako Wiki Hii',
        'silent_killers': 'Wauaji Wasioonekana',
        'numbers_dont_lie': 'Namba Hazidanganyi',
        'next_week_directive': 'Maelekezo ya Wiki Inayofuata',
        'key_metrics': 'Vipimo Vikuu',
        'financial_summary': 'Muhtasari wa Kifedha',
        'total_income': 'Jumla ya Mapato',
        'total_expenses': 'Jumla ya Matumizi',
        'net_cash_flow': 'Mtiririko wa Pesa',
        'total_saved': 'Jumla Iliyohifadhiwa',
        'vektra_score': 'Alama ya VEKTRA',
        'average_mood': 'Mood ya Wastani',
        'average_energy': 'Nishati ya Wastani',
        'average_focus': 'Kuzingatia kwa Wastani',
        'average_sleep': 'Usingizi wa Wastani',
        'days_logged': 'Siku Zilizorekodiwa',
        'goal_hit_rate': 'Kiwango cha Kufikia Lengo',
        'survival_runway': 'Njia ya Kuishi',
        'happy_birthday': 'Siku ya Kuzaliwa Njema',
        'vector_magnitude_direction': 'Kielelezo = Kiasi + Mwelekeo',
        'rising': 'INAPOKUA',
        'flat': 'SAWA',
        'declining': 'INASHUKA',
    },
    'es': {
        'vektra_report': 'Informe VEKTRA',
        'weekly_report': 'Informe Semanal',
        'monthly_report': 'Informe Mensual',
        'quarterly_report': 'Informe Trimestral',
        'annual_report': 'Informe Anual',
        'trajectory_status': 'Estado de Trayectoria',
        'your_wins': 'Tus Victorias Esta Semana',
        'silent_killers': 'Asesinos Silenciosos',
        'numbers_dont_lie': 'Los Números No Mienten',
        'next_week_directive': 'Directiva de la Próxima Semana',
        'key_metrics': 'Métricas Clave',
        'financial_summary': 'Resumen Financiero',
        'total_income': 'Ingresos Totales',
        'total_expenses': 'Gastos Totales',
        'net_cash_flow': 'Flujo de Efectivo Neto',
        'total_saved': 'Total Ahorrado/Invertido',
        'vektra_score': 'Puntuación VEKTRA',
        'average_mood': 'Ánimo Promedio',
        'average_energy': 'Energía Promedio',
        'average_focus': 'Enfoque Promedio',
        'average_sleep': 'Sueño Promedio',
        'days_logged': 'Días Registrados',
        'goal_hit_rate': 'Tasa de Logro de Metas',
        'survival_runway': 'Pista de Supervivencia',
        'happy_birthday': 'Feliz Cumpleaños',
        'vector_magnitude_direction': 'Vector = Magnitud × Dirección',
        'rising': 'EN AUMENTO',
        'flat': 'ESTABLE',
        'declining': 'EN DISMINUCIÓN',
    },
    'fr': {
        'vektra_report': 'Rapport VEKTRA',
        'weekly_report': 'Rapport Hebdomadaire',
        'monthly_report': 'Rapport Mensuel',
        'quarterly_report': 'Rapport Trimestriel',
        'annual_report': 'Rapport Annuel',
        'trajectory_status': 'État de la Trajectoire',
        'your_wins': 'Vos Victoires Cette Semaine',
        'silent_killers': 'Tueurs Silencieux',
        'numbers_dont_lie': 'Les Chiffres Ne Mentent Pas',
        'next_week_directive': 'Directive de la Semaine Prochaine',
        'key_metrics': 'Métriques Clés',
        'financial_summary': 'Résumé Financier',
        'total_income': 'Revenus Totaux',
        'total_expenses': 'Dépenses Totales',
        'net_cash_flow': 'Flux de Trésorerie Net',
        'total_saved': 'Total Économisé/Investi',
        'vektra_score': 'Score VEKTRA',
        'average_mood': 'Humeur Moyenne',
        'average_energy': 'Énergie Moyenne',
        'average_focus': 'Concentration Moyenne',
        'average_sleep': 'Sommeil Moyen',
        'days_logged': 'Jours Enregistrés',
        'goal_hit_rate': 'Taux de Réalisation des Objectifs',
        'survival_runway': 'Piste de Survie',
        'happy_birthday': 'Joyeux Anniversaire',
        'vector_magnitude_direction': 'Vecteur = Magnitude × Direction',
        'rising': 'EN HAUSSE',
        'flat': 'STABLE',
        'declining': 'EN BAISSE',
    },
    'de': {
        'vektra_report': 'VEKTRA Bericht',
        'weekly_report': 'Wochenbericht',
        'monthly_report': 'Monatsbericht',
        'quarterly_report': 'Quartalsbericht',
        'annual_report': 'Jahresbericht',
        'trajectory_status': 'Trajektorienstatus',
        'your_wins': 'Ihre Erfolge Diese Woche',
        'silent_killers': 'Stille Killer',
        'numbers_dont_lie': 'Zahlen Lügen Nicht',
        'next_week_directive': 'Direktive für Nächste Woche',
        'key_metrics': 'Schlüsselkennzahlen',
        'financial_summary': 'Finanzielle Zusammenfassung',
        'total_income': 'Gesamteinkommen',
        'total_expenses': 'Gesamtausgaben',
        'net_cash_flow': 'Netto-Cashflow',
        'total_saved': 'Insgesamt Gespart/Investiert',
        'vektra_score': 'VEKTRA-Score',
        'average_mood': 'Durchschnittliche Stimmung',
        'average_energy': 'Durchschnittliche Energie',
        'average_focus': 'Durchschnittlicher Fokus',
        'average_sleep': 'Durchschnittlicher Schlaf',
        'days_logged': 'Protokollierte Tage',
        'goal_hit_rate': 'Ziel-Erfolgsrate',
        'survival_runway': 'Überlebenslaufbahn',
        'happy_birthday': 'Alles Gute zum Geburtstag',
        'vector_magnitude_direction': 'Vektor = Betrag × Richtung',
        'rising': 'STEIGEND',
        'flat': 'STABIL',
        'declining': 'FALLEND',
    },
    'zh': {
        'vektra_report': 'VEKTRA 报告',
        'weekly_report': '周报',
        'monthly_report': '月报',
        'quarterly_report': '季报',
        'annual_report': '年报',
        'trajectory_status': '轨迹状态',
        'your_wins': '本周成就',
        'silent_killers': '隐形杀手',
        'numbers_dont_lie': '数字不会说谎',
        'next_week_directive': '下周指令',
        'key_metrics': '关键指标',
        'financial_summary': '财务摘要',
        'total_income': '总收入',
        'total_expenses': '总支出',
        'net_cash_flow': '净现金流',
        'total_saved': '总储蓄/投资',
        'vektra_score': 'VEKTRA 分数',
        'average_mood': '平均情绪',
        'average_energy': '平均能量',
        'average_focus': '平均专注度',
        'average_sleep': '平均睡眠',
        'days_logged': '记录天数',
        'goal_hit_rate': '目标达成率',
        'survival_runway': '生存跑道',
        'happy_birthday': '生日快乐',
        'vector_magnitude_direction': '向量 = 大小 × 方向',
        'rising': '上升',
        'flat': '平稳',
        'declining': '下降',
    },
}

# Language code mapping
LANGUAGE_CODES = {
    'english': 'en',
    'kiswahili': 'sw',
    'spanish': 'es',
    'french': 'fr',
    'german': 'de',
    'chinese': 'zh',
}


class TranslationService:
    """Handles translation of UI elements and report content."""
    
    def normalize_language_code(self, language: Optional[str]) -> str:
        """
        Normalize language name to code.
        Defaults to 'en' if not found.
        """
        if not language:
            return 'en'
        
        language_lower = language.lower()
        
        # Direct code match
        if language_lower in TRANSLATIONS:
            return language_lower
        
        # Name match
        if language_lower in LANGUAGE_CODES:
            return LANGUAGE_CODES[language_lower]
        
        # Partial match
        for name, code in LANGUAGE_CODES.items():
            if language_lower in name or name in language_lower:
                return code
        
        return 'en'
    
    def translate(self, key: str, language: Optional[str] = None) -> str:
        """
        Translate a key to the specified language.
        Returns original key if translation not found.
        """
        lang_code = self.normalize_language_code(language)
        
        if lang_code in TRANSLATIONS and key in TRANSLATIONS[lang_code]:
            return TRANSLATIONS[lang_code][key]
        
        # Fallback to English
        if key in TRANSLATIONS.get('en', {}):
            return TRANSLATIONS['en'][key]
        
        # Return key if no translation found
        return key
    
    def translate_dict(self, data: Dict[str, str], language: Optional[str] = None) -> Dict[str, str]:
        """
        Translate all values in a dictionary.
        Useful for translating report content.
        """
        translated = {}
        for key, value in data.items():
            if isinstance(value, str):
                translated[key] = self.translate(value, language)
            else:
                translated[key] = value
        return translated
    
    def get_supported_languages(self) -> list:
        """Return list of supported language codes."""
        return list(TRANSLATIONS.keys())
    
    def get_language_name(self, code: str) -> str:
        """Get human-readable language name from code."""
        names = {
            'en': 'English',
            'sw': 'Kiswahili',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'zh': 'Chinese',
        }
        return names.get(code, code)


translation_service = TranslationService()
