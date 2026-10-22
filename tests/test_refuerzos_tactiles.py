"""Regresiones del gesto de refuerzo y limites del panel Android."""
import unittest
from unittest.mock import patch
from controller import ControlMovil, FASE_INCORPORAR, FASE_ATACAR


class PruebasIncorporacionTactil(unittest.TestCase):
    def setUp(self):
        self.c = ControlMovil(n_jugadores=2, orden_inicial=[0, 1], animaciones=False)
        self.j = self.c.juego
        self.j.turno_idx = 0
        self.j.fase = FASE_INCORPORAR
        self.j.ejercitos_a_colocar = 8
        self.pais = self.j.paises_de(0)[0]

    def test_doble_toque_suma_una_unidad(self):
        antes = self.j.tablero[self.pais]["ejercitos"]
        self.assertTrue(self.c.incorporar_uno_por_doble_toque(self.pais))
        self.assertEqual(self.j.tablero[self.pais]["ejercitos"], antes + 1)
        self.assertEqual(self.j.ejercitos_a_colocar, 7)

    def test_doble_toque_invalido_durante_bot_dialogo_y_ataque(self):
        antes = self.j.tablero[self.pais]["ejercitos"]
        self.c.dialogo = {"kind": "info", "obligatorio": False}
        self.assertFalse(self.c.incorporar_uno_por_doble_toque(self.pais))
        self.c.dialogo = None
        self.j.turno_idx = 1
        self.assertFalse(self.c.incorporar_uno_por_doble_toque(self.pais))
        self.j.turno_idx = 0
        self.j.fase = FASE_ATACAR
        self.assertFalse(self.c.incorporar_uno_por_doble_toque(self.pais))
        self.assertEqual(self.j.tablero[self.pais]["ejercitos"], antes)

    def test_cantidad_superior_al_disponible_se_ajusta(self):
        self.j.ejercitos_a_colocar = 2
        self.c.origen = self.pais
        antes = self.j.tablero[self.pais]["ejercitos"]
        self.assertTrue(self.c.accion("incorporar", 20))
        self.assertEqual(self.j.tablero[self.pais]["ejercitos"], antes + 2)
        self.assertEqual(self.j.ejercitos_a_colocar, 0)

    def test_cantidad_respeta_limite_continental(self):
        continente = self.j.tablero[self.pais]["continente"]
        self.j.ejercitos_a_colocar = 8
        self.j.refuerzos_continente = {"otro_continente": 6}
        # El motor no debe aceptar refuerzos reservados para otra región.
        # Probamos el límite de refuerzos libres sin depender de un continente real.
        with patch.object(self.j, "desglose_incorporacion", return_value={
            "libres": 2, "continentes": {"otro_continente": 6}, "total": 8
        }):
            with patch.object(self.j, "incorporar", return_value=True) as incorporar:
                self.c.origen = self.pais
                self.assertTrue(self.c.accion("incorporar", 20))
                incorporar.assert_called_once_with(self.pais, 2)


if __name__ == "__main__":
    unittest.main()
