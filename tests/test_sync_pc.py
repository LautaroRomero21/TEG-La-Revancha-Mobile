"""Regresiones de sincronización con TEG PC: IA, mapa, pactos y objetivos."""
import unittest
from unittest.mock import patch

from controller import ControlMovil
from logic import JuegoTEG, FASE_ATACAR
from data import PAISES_DATA
from ia_dificil import probabilidad_conquista


class SincronizacionPC(unittest.TestCase):
    def test_niveles_de_dificultad(self):
        for dificultad in ("Normal", "Dificil"):
            with self.subTest(dificultad=dificultad):
                c = ControlMovil(3, orden_inicial=[0, 1, 2],
                                 dificultad=dificultad)
                self.assertEqual(c.juego.dificultad, dificultad)
                self.assertIsNotNone(c.juego.ia_dificil)
        with self.assertRaises(ValueError):
            JuegoTEG(2, dificultad="Experto")

    def test_dificil_delega_estrategia(self):
        j = JuegoTEG(3, orden_inicial=[0, 1, 2], dificultad="Dificil")
        j.turno_idx = 1
        esperado = {"accion": "incorporar", "pais": "Alaska", "cantidad": 1}
        with patch.object(j.ia_dificil, "paso", return_value=esperado) as paso:
            self.assertEqual(j.paso_bot(), esperado)
            paso.assert_called_once_with(j.jugadores[1])

    def test_probabilidades_de_dados(self):
        probabilidad, bajas = probabilidad_conquista(8, 2)
        self.assertGreater(probabilidad, 0)
        self.assertLessEqual(probabilidad, 1)
        self.assertGreaterEqual(bajas, 0)

    def test_frontera_chechenia_kamchatka_eliminada(self):
        self.assertNotIn("Kamchatka", PAISES_DATA["Chechenia"]["fronteras"])
        self.assertNotIn("Chechenia", PAISES_DATA["Kamchatka"]["fronteras"])
        for nombre, pais in PAISES_DATA.items():
            for vecino in pais["fronteras"]:
                self.assertIn(nombre, PAISES_DATA[vecino]["fronteras"])

    def test_agresion_verifica_los_dos_origenes_antes_de_negociar(self):
        j = JuegoTEG(3, orden_inicial=[0, 1, 2])
        j.etapa = "hostilidades"
        j.etapa_ronda = "ATAQUE"
        j.ronda = 2
        j.fase = FASE_ATACAR
        j.turno_idx = 0
        j.situacion = "Clásico"
        for pais, propietario in (("Alaska", 0), ("Oregon", 1), ("Canada", 2)):
            j.tablero[pais]["propietario"] = propietario
            j.tablero[pais]["ejercitos"] = 10
        with patch.object(j, "_ataque_permitido", side_effect=[True, False]) as validar:
            self.assertFalse(j.puede_proponer_agresion_conjunta(
                0, 1, "Alaska", "Oregon", "Canada"
            ))
            self.assertEqual(validar.call_count, 2)
        with patch.object(j, "_ataque_permitido", return_value=False):
            antes = len(j.agresiones_pendientes)
            self.assertIsNone(j.proponer_agresion_conjunta(
                0, 1, "Alaska", "Oregon", "Canada"
            ))
            self.assertEqual(len(j.agresiones_pendientes), antes)

    def test_victoria_indica_objetivo(self):
        c = ControlMovil(2, orden_inicial=[0, 1])
        j = c.juego
        j.fase = "VICTORIA"
        j.ganador_idx = 1
        j.detalle_victoria = {
            "tipo": "personal",
            "objetivos": ["Conquistar Europa", "Controlar Oceanía"],
            "paises": 22,
        }
        c.tick()
        self.assertEqual(c.dialogo["kind"], "victoria")
        self.assertIn("Conquistar Europa", c.dialogo["texto"])
        self.assertIn("Controlar Oceanía", c.dialogo["texto"])


if __name__ == "__main__":
    unittest.main()
