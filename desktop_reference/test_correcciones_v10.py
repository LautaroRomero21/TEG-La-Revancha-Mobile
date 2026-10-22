"""Regresiones v10: canjes por jugador y premios de tarjeta de país.

Ejecutar: python -m unittest -v test_correcciones_v10
"""
import random
import unittest

from logic import (
    JuegoTEG, FASE_INCORPORAR, FASE_ATACAR, FASE_REAGRUPAR, FASE_TARJETA,
)


class PremiosYCanjesV10(unittest.TestCase):
    def setUp(self):
        random.seed(1010)
        self.j = JuegoTEG(4)

    def test_cada_jugador_empieza_con_seis_aunque_otros_hayan_canjeado(self):
        j = self.j
        j.canje_numero = 8  # Partida con canjes anteriores ajenos.
        j.jugadores[1].canjes_realizados = 3
        j.jugadores[2].canjes_realizados = 1
        j.turno_idx = 0
        self.assertEqual(j.valor_canje(), 6)
        j.turno_idx = 1
        self.assertEqual(j.valor_canje(), 20)
        j.turno_idx = 2
        self.assertEqual(j.valor_canje(), 10)
        j.turno_idx = 3
        self.assertEqual(j.valor_canje(), 6)

    def test_secuencia_seis_diez_quince_veinte_y_cinco_mas_por_jugador(self):
        j = self.j
        for indice in (0, 1, 2, 3):
            for anteriores, esperado in enumerate((6,10,15,20,25,30,35,40)):
                j.jugadores[indice].canjes_realizados = anteriores
                self.assertEqual(j.valor_canje(j.jugadores[indice]), esperado)

    def test_canjes_reales_con_bots_no_aumentan_primer_canje_humano(self):
        j = self.j
        j.etapa = 'hostilidades'
        j.fase = FASE_INCORPORAR
        j.ronda = 2
        j.ejercitos_a_colocar = 5
        j.turno_idx = 1
        j.jugadores[1].tarjetas = ['Angola','Alemania','Albania']
        self.assertEqual(j.canjear_tarjetas(indices=[0,1,2]), 6)
        self.assertEqual(j.jugadores[1].canjes_realizados, 1)
        self.assertEqual(j.canje_numero, 1)
        self.assertEqual(j.ejercitos_a_colocar, 11)

        j.turno_idx = 0
        j.jugadores[0].tarjetas = ['Angola','Alemania','Albania']
        self.assertEqual(j.valor_canje(), 6)
        self.assertEqual(j.canjear_tarjetas(indices=[0,1,2]), 6)
        self.assertEqual(j.canje_numero, 2)
        self.assertEqual(j.jugadores[0].canjes_realizados, 1)
        self.assertEqual(j.ejercitos_a_colocar, 17)

        j.ronda = 3
        j.turno_idx = 0
        j.jugadores[0].tarjetas = ['Angola','Alemania','Albania']
        self.assertEqual(j.canjear_tarjetas(indices=[0,1,2]), 10)
        self.assertEqual(j.jugadores[0].canjes_realizados, 2)
        j.turno_idx = 1
        self.assertEqual(j.valor_canje(), 10)
        j.turno_idx = 2
        self.assertEqual(j.valor_canje(), 6)

    def test_tarjeta_recibida_del_pais_que_tengo_da_tres_de_inmediato(self):
        j = self.j
        j.tablero['Alaska']['propietario'] = 0
        j.tablero['Alaska']['ejercitos'] = 2
        j.mazo_cartas_pais = ['Alaska']
        self.assertEqual(j.robar_tarjeta(j.jugadores[0]), 'Alaska')
        self.assertEqual(j.tablero['Alaska']['ejercitos'], 5)
        self.assertIn('Alaska', j.jugadores[0].tarjetas)
        self.assertIn('Alaska', j.jugadores[0].tarjetas_premiadas)
        j._premios_tarjetas(j.jugadores[0])
        self.assertEqual(j.tablero['Alaska']['ejercitos'], 5)

    def test_tarjeta_del_pais_ajeno_se_premia_al_cierre_de_turno_si_conquisto(self):
        j = self.j
        j.tablero['Canada']['propietario'] = 1
        j.tablero['Canada']['ejercitos'] = 1
        j.mazo_cartas_pais = ['Canada']
        self.assertEqual(j.robar_tarjeta(j.jugadores[0]), 'Canada')
        self.assertEqual(j.tablero['Canada']['ejercitos'], 1)
        self.assertNotIn('Canada', j.jugadores[0].tarjetas_premiadas)

        # La conquista ocurre posteriormente; premio en la etapa de tarjetas.
        j.tablero['Canada']['propietario'] = 0
        j.tablero['Canada']['ejercitos'] = 2
        j.turno_idx = 0
        j.etapa = 'hostilidades'
        j.fase = FASE_REAGRUPAR
        self.assertTrue(j.avanzar_fase())
        self.assertEqual(j.fase, FASE_TARJETA)
        self.assertEqual(j.tablero['Canada']['ejercitos'], 5)
        self.assertIn('Canada', j.jugadores[0].tarjetas_premiadas)
        j._premios_tarjetas(j.jugadores[0])
        self.assertEqual(j.tablero['Canada']['ejercitos'], 5)

    def test_no_se_premia_tarjeta_sin_controlar_pais(self):
        j = self.j
        j.tablero['Canada']['propietario'] = 1
        j.mazo_cartas_pais = ['Canada']
        valor = j.tablero['Canada']['ejercitos']
        j.robar_tarjeta(j.jugadores[0])
        j._premios_tarjetas(j.jugadores[0])
        self.assertEqual(j.tablero['Canada']['ejercitos'], valor)
        self.assertNotIn('Canada', j.jugadores[0].tarjetas_premiadas)

    def test_premio_bloqueado_se_pospone_hasta_levantar_bloqueo(self):
        j = self.j
        p = 'Brasil'
        j.tablero[p]['propietario'] = 0
        j.tablero[p]['ejercitos'] = 3
        for vecino in j.tablero[p]['fronteras']:
            j.tablero[vecino]['propietario'] = 1
            j.tablero[vecino]['ejercitos'] = 2
        # Al menos otro país para que corresponda el bloqueo.
        j.tablero['Alaska']['propietario'] = 0
        self.assertTrue(j._pais_bloqueado(p))
        j.mazo_cartas_pais = [p]
        j.robar_tarjeta(j.jugadores[0])
        self.assertEqual(j.tablero[p]['ejercitos'], 3)
        j.tablero[j.tablero[p]['fronteras'][0]]['ejercitos'] = 1
        self.assertFalse(j._pais_bloqueado(p))
        j._premios_tarjetas(j.jugadores[0])
        self.assertEqual(j.tablero[p]['ejercitos'], 6)

    def test_tarjetas_heredadas_tambien_pueden_recibir_premio_en_nuevo_dueno(self):
        j = self.j
        for pais in j.tablero:
            j.tablero[pais]['propietario'] = 0
        j.tablero['Canada']['propietario'] = 1
        j.tablero['Brasil']['ejercitos'] = 2
        j.jugadores[1].tarjetas = ['Brasil']
        j.jugadores[1].tarjetas_premiadas = {'Brasil'}
        j.tablero['Canada']['propietario'] = 0
        j._verificar_eliminacion(1, 0)
        self.assertIn('Brasil', j.jugadores[0].tarjetas)
        self.assertNotIn('Brasil', j.jugadores[0].tarjetas_premiadas)
        j._premios_tarjetas(j.jugadores[0])
        self.assertEqual(j.tablero['Brasil']['ejercitos'], 5)
        j._premios_tarjetas(j.jugadores[0])
        self.assertEqual(j.tablero['Brasil']['ejercitos'], 5)


if __name__ == '__main__':
    unittest.main()
