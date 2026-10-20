from unittest import mock

from django.db import OperationalError
from django.test import SimpleTestCase

from obstetric_care.dbrouters import LegacyRouter

from .models import ControlesPrevios
from .services import obtener_controles_previos


class ObtenerControlesPreviosTests(SimpleTestCase):
    """No requiere BD: se simula el queryset de ControlesPrevios."""

    def _mock_queryset(self, resultado=None, error=None):
        qs = mock.MagicMock()
        qs.order_by.return_value.__getitem__.return_value = resultado or []
        if error:
            qs.order_by.return_value.__getitem__.side_effect = error
        return qs

    @mock.patch.object(ControlesPrevios, 'objects')
    def test_devuelve_lista_y_disponible(self, objects):
        control = ControlesPrevios(paciente_rut='16293109-1')
        objects.filter.return_value = self._mock_queryset([control])

        controles, disponible = obtener_controles_previos('16293109-1')

        self.assertTrue(disponible)
        self.assertEqual(controles, [control])
        objects.filter.assert_called_once_with(paciente_rut='16293109-1')
        objects.filter.return_value.order_by.assert_called_once_with('-fecha_control')

    @mock.patch.object(ControlesPrevios, 'objects')
    def test_bd_legacy_caida_no_revienta(self, objects):
        objects.filter.return_value = self._mock_queryset(
            error=OperationalError(2003, "Can't connect to MySQL server")
        )

        with self.assertLogs('legacyApp.services', level='ERROR'):
            controles, disponible = obtener_controles_previos('16293109-1')

        self.assertFalse(disponible)
        self.assertEqual(controles, [])

    @mock.patch.object(ControlesPrevios, 'objects')
    def test_rut_vacio_no_consulta(self, objects):
        controles, disponible = obtener_controles_previos('')

        self.assertTrue(disponible)
        self.assertEqual(controles, [])
        objects.filter.assert_not_called()


class LegacyRouterTests(SimpleTestCase):
    def setUp(self):
        self.router = LegacyRouter()

    def test_lectura_va_a_legacy(self):
        self.assertEqual(self.router.db_for_read(ControlesPrevios), 'legacy')

    def test_no_migra_legacy(self):
        self.assertFalse(self.router.allow_migrate('legacy', 'legacyApp'))
        self.assertFalse(self.router.allow_migrate('default', 'legacyApp'))
