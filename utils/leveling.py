# KimiXP - Discord Bot
# Copyright (C) 2026 BrunoDevPe
#
# This file is part of KimiXP.
#
# KimiXP is free software licensed under the GNU General Public License v3.0.
# See the LICENSE file in the root directory for more information.

import re
import math
from typing import Tuple, Dict, Any

class LevelCalculator:
    """
    Calculadora del sistema de XP y progresion de niveles.
    Utiliza los parametros del config.json para definir la curva de experiencia.
    """

    def __init__(self, base_multiplier: float = 50.0, linear_increment: float = 100.0):
        self.base_multiplier = base_multiplier
        self.linear_increment = linear_increment

    def get_xp_for_level(self, level: int) -> int:
        """
        Retorna la XP total necesaria para alcanzar el nivel indicado.
        Formula progresiva: 50 * (level - 1)^2 + 100 * (level - 1)
        Level 1: 0 XP
        Level 2: 150 XP
        Level 3: 400 XP
        Level 4: 750 XP
        Level 5: 1200 XP
        """
        if level <= 1:
            return 0
        lvl_index = level - 1
        return int(self.base_multiplier * (lvl_index ** 2) + self.linear_increment * lvl_index)

    def get_level_from_xp(self, total_xp: int) -> int:
        """Calcula el nivel correspondiente a una cantidad dada de XP total."""
        if total_xp <= 0:
            return 1
        
        level = 1
        while self.get_xp_for_level(level + 1) <= total_xp:
            level += 1
        return level

    def get_progress_details(self, total_xp: int) -> Dict[str, Any]:
        """Calcula detalles de progreso del usuario (nivel actual, XP en nivel, XP necesaria, porcentaje)."""
        current_level = self.get_level_from_xp(total_xp)
        current_level_base_xp = self.get_xp_for_level(current_level)
        next_level_xp = self.get_xp_for_level(current_level + 1)

        xp_in_level = total_xp - current_level_base_xp
        xp_needed_for_next = next_level_xp - current_level_base_xp
        percentage = min(100.0, max(0.0, (xp_in_level / xp_needed_for_next) * 100.0 if xp_needed_for_next > 0 else 100.0))

        return {
            "level": current_level,
            "total_xp": total_xp,
            "xp_in_level": xp_in_level,
            "xp_needed_for_next": xp_needed_for_next,
            "percentage": round(percentage, 1),
            "next_level_total_xp": next_level_xp
        }

    @staticmethod
    def render_progress_bar(percentage: float, length: int = 12) -> str:
        """Genera una barra de progreso visual con caracteres ASCII/Unicode."""
        filled_length = int(round(length * (percentage / 100.0)))
        filled_length = max(0, min(length, filled_length))
        empty_length = length - filled_length
        return "█" * filled_length + "░" * empty_length


class AntiSpamFilter:
    """Filtro básico anti-farming para ignorar spam evidente sin castigar conversaciones breves."""

    @staticmethod
    def is_spam(content: str) -> bool:
        clean = content.strip()
        
        # Ignorar mensajes totalmente vacíos
        if not clean:
            return True

        # Permitir palabras cortas legítimas como "ok", "hola", "xd", "si"
        if len(clean) <= 3:
            return False

        # Detectar repetición excesiva del mismo caracter (ej: "aaaaaaaaaaaaa")
        if len(clean) >= 6:
            most_common_char_count = max(clean.count(c) for c in set(clean))
            if (most_common_char_count / len(clean)) > 0.8:
                return True

        # Detectar repetición de palabras idénticas muchas veces (ej: "hola hola hola hola hola")
        words = clean.lower().split()
        if len(words) >= 5 and len(set(words)) == 1:
            return True

        return False