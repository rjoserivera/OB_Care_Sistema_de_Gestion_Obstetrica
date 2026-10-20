# legacyApp/services.py
"""
Acceso de solo lectura a la base histórica (legacy).

La BD legacy es opcional para la atención: si no está disponible,
las vistas deben seguir funcionando y solo mostrar un aviso.
"""
import logging

from django.db import DatabaseError

from .models import ControlesPrevios

logger = logging.getLogger(__name__)


def obtener_controles_previos(rut, limite=20):
    """
    Retorna (controles, disponible).

    - controles: lista (ya evaluada) con los últimos `limite` controles del RUT.
    - disponible: False si la BD legacy no respondió; en ese caso controles = [].
    """
    if not rut:
        return [], True

    try:
        controles = list(
            ControlesPrevios.objects.filter(paciente_rut=rut)
            .order_by('-fecha_control')[:limite]
        )
    except DatabaseError:
        logger.exception("No se pudo consultar la BD legacy (rut=%s)", rut)
        return [], False

    return controles, True
