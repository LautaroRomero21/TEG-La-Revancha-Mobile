"""Regresiones v9: compra de misiles sin bono del continente del país."""
import unittest
from data import CONTINENTES, PAISES_DATA, MISIL_COSTO_EJERCITOS
from logic import JuegoTEG, FASE_INCORPORAR


class MisilesIncorporacionV9(unittest.TestCase):
    def crear_partida(self, pais, pendientes, bonos=None):
        juego = JuegoTEG(2, orden_inicial=[0, 1])
        juego.etapa = 'hostilidades'
        juego.ronda = 2
        juego.etapa_ronda = 'INCORPORACION'
        juego.turno_idx = 0
        juego.fase = FASE_INCORPORAR
        for datos in juego.tablero.values():
            datos['propietario'] = 1
            datos['ejercitos'] = 1
        juego.tablero[pais]['propietario'] = 0
        juego.tablero[pais]['ejercitos'] = 1
        juego.ejercitos_a_colocar = pendientes
        juego.refuerzos_continente = dict(bonos or {})
        return juego

    def test_misil_con_solo_refuerzos_libres_en_oceania(self):
        # Reproduce exactamente el KeyError: 'Oceania' informado en ronda 2.
        j = self.crear_partida('Australia', 10)
        self.assertTrue(j.incorporar_misil('Australia'))
        self.assertEqual(j.tablero['Australia']['misiles'], 1)
        self.assertEqual(j.ejercitos_a_colocar, 4)
        self.assertEqual(j.refuerzos_continente, {})
        self.assertEqual(j.desglose_incorporacion()['libres'], 4)

    def test_misil_con_refuerzos_libres_en_todos_los_continentes(self):
        for continente in CONTINENTES:
            pais = next(p for p,d in PAISES_DATA.items() if d['continente']==continente)
            with self.subTest(continente=continente, pais=pais):
                j = self.crear_partida(pais, 9)
                self.assertTrue(j.incorporar_misil(pais))
                self.assertEqual(j.tablero[pais]['misiles'], 1)
                self.assertEqual(j.ejercitos_a_colocar, 3)
                self.assertEqual(j.refuerzos_continente, {})

    def test_no_consumir_bono_de_otro_continente(self):
        j = self.crear_partida('Australia', 10, {'Asia': 3})  # 7 libres, 3 asiáticos
        self.assertTrue(j.incorporar_misil('Australia'))
        self.assertEqual(j.refuerzos_continente, {'Asia': 3})
        self.assertEqual(j.ejercitos_a_colocar, 4)
        self.assertEqual(j.desglose_incorporacion(), {
            'libres': 1, 'continentes': {'Asia': 3}, 'total': 4
        })

    def test_rechazar_si_solo_hay_cinco_libres_y_bonos_de_otro_continente(self):
        j = self.crear_partida('Australia', 8, {'Asia': 3})
        self.assertFalse(j.incorporar_misil('Australia'))
        self.assertEqual(j.tablero['Australia']['misiles'], 0)
        self.assertEqual(j.ejercitos_a_colocar, 8)
        self.assertEqual(j.refuerzos_continente, {'Asia': 3})

    def test_misil_consume_primero_refuerzos_de_su_continente(self):
        j = self.crear_partida('Australia', 11, {'Oceania': 3})
        self.assertTrue(j.incorporar_misil('Australia'))
        self.assertEqual(j.refuerzos_continente['Oceania'], 0)
        self.assertEqual(j.ejercitos_a_colocar, 5)
        self.assertEqual(j.desglose_incorporacion()['libres'], 5)
        self.assertEqual(j.tablero['Australia']['misiles'], 1)

    def test_misil_con_bono_del_continente_ya_agotado(self):
        j = self.crear_partida('Australia', 8, {'Oceania': 0})
        self.assertTrue(j.incorporar_misil('Australia'))
        self.assertEqual(j.refuerzos_continente['Oceania'], 0)
        self.assertEqual(j.ejercitos_a_colocar, 2)

    def test_conversion_de_seis_ejercitos_no_modifica_refuerzos(self):
        j = self.crear_partida('Australia', 7, {'Asia': 3})
        j.tablero['Australia']['ejercitos'] = 7
        self.assertTrue(j.incorporar_misil('Australia', reemplazar=True))
        self.assertEqual(j.tablero['Australia']['ejercitos'], 1)
        self.assertEqual(j.tablero['Australia']['misiles'], 1)
        self.assertEqual(j.ejercitos_a_colocar, 7)
        self.assertEqual(j.refuerzos_continente, {'Asia': 3})

    def test_compra_en_partida_real_al_comenzar_ronda_dos(self):
        # Recorre preparación 18, ronda inicial completa y compra en ronda 2,
        # exactamente como en el reporte del jugador.
        j = JuegoTEG(2, orden_inicial=[0, 1])
        for idx in range(2):
            self.assertEqual(j.turno_idx, idx)
            pais = next(p for p in j.paises_de(idx) if not j._pais_bloqueado(p))
            self.assertTrue(j.incorporar(pais, j.ejercitos_a_colocar))
        for idx in range(2):
            self.assertEqual(j.turno_idx, idx)
            for _ in range(3):
                self.assertTrue(j.avanzar_fase())
        self.assertEqual(j.ronda, 2)
        self.assertEqual(j.fase, FASE_INCORPORAR)
        self.assertEqual(j.refuerzos_continente, {})
        pais = next(p for p in j.paises_de(j.turno_idx) if not j._pais_bloqueado(p))
        saldo_previo = j.ejercitos_a_colocar
        self.assertGreaterEqual(saldo_previo, MISIL_COSTO_EJERCITOS)
        misiles_previos = j.tablero[pais]['misiles']
        self.assertTrue(j.incorporar_misil(pais))
        self.assertEqual(j.tablero[pais]['misiles'], misiles_previos+1)
        self.assertEqual(j.ejercitos_a_colocar, saldo_previo-MISIL_COSTO_EJERCITOS)

    def test_compra_rechazada_no_muta_tablero_ni_refuerzos(self):
        j = self.crear_partida('Australia', MISIL_COSTO_EJERCITOS - 1)
        previo = (j.ejercitos_a_colocar, j.tablero['Australia']['misiles'], dict(j.refuerzos_continente))
        self.assertFalse(j.incorporar_misil('Australia'))
        self.assertEqual((j.ejercitos_a_colocar, j.tablero['Australia']['misiles'], j.refuerzos_continente), previo)


if __name__ == '__main__':
    unittest.main()
