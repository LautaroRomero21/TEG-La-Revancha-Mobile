"""Regresiones v11: dados, bloqueos, tarjetas continentales y fronteras.

Ejecutar: python -m unittest -v test_correcciones_v11
"""
import random
import unittest
from collections import deque
from unittest.mock import patch

from data import PAISES_DATA, CONTINENTES
from logic import JuegoTEG, FASE_INCORPORAR, FASE_ATACAR


class ReglasV11(unittest.TestCase):
    def setUp(self):
        random.seed(1111)
        self.j=JuegoTEG(4,orden_inicial=[0,1,2,3])

    def combate(self,atacante=8,defensor=4):
        j=self.j
        j.etapa='hostilidades';j.ronda=3;j.fase=FASE_ATACAR
        j.situacion='Clásico';j.turno_idx=0
        j.tablero['Alaska']['propietario']=0
        j.tablero['Alaska']['ejercitos']=atacante
        j.tablero['Canada']['propietario']=1
        j.tablero['Canada']['ejercitos']=defensor
        return j

    def controlar(self,continente,dueno=0):
        j=self.j
        for pais,datos in j.tablero.items():
            if datos['continente']==continente:
                datos['propietario']=dueno
                datos['ejercitos']=3
        return j.jugadores[dueno]

    def test_tres_cuatro_tres_dados_sucesivos_sin_viento(self):
        j=self.combate(9,5)
        # Ataque 1: 9 vs 5, dos bajas del defensor y una del atacante.
        # Ataque 2: 8 vs 3, ya puede tirar 4 dados por ventaja doble.
        # Ataque 3: 6 vs 2, deja de aplicar (mínimo 3 defensores).
        resultados=[]
        con_dados=[[6,6,2,5,4,3], [6,2,2,1,5,4,3], [4,3,2,5,5]]
        for dados in con_dados:
            with patch('logic.random.randint', side_effect=dados):
                r=j.atacar('Alaska','Canada')
            self.assertTrue(r['ok'])
            resultados.append(len(r['dados_atk']))
        self.assertEqual(resultados,[3,4,3])
        self.assertEqual(j.tablero['Canada']['ejercitos'],2)
        self.assertIsNone(r['razon_4_dados'])
        self.assertIn('4 DADOS: DOBLE FUERZA', ' '.join(j.historial))

    def test_ventaja_doble_requiere_tres_defensores_sin_contar_misiles(self):
        j=self.combate(20,2)
        j.tablero['Canada']['misiles']=10
        with patch('logic.random.randint',return_value=1):
            r=j.atacar('Alaska','Canada')
        self.assertEqual(len(r['dados_atk']),3)
        self.assertIsNone(r['razon_4_dados'])
        j=self.combate(6,3)
        with patch('logic.random.randint',return_value=1):
            r=j.atacar('Alaska','Canada')
        self.assertEqual(len(r['dados_atk']),4)
        self.assertIn('DOBLE FUERZA',r['razon_4_dados'])

    def test_viento_a_favor_sigue_permitiendo_cuarto_dado(self):
        j=self.combate(4,3)
        j.situacion='Viento a favor'
        with patch('logic.random.randint',return_value=1):
            r=j.atacar('Alaska','Canada')
        self.assertEqual(len(r['dados_atk']),4)
        self.assertEqual(r['razon_4_dados'],'VIENTO A FAVOR')

    def preparar_bloqueo_brasil(self):
        j=self.j
        p='Brasil'
        j.tablero[p]['propietario']=0
        j.tablero[p]['ejercitos']=8
        j.tablero['Alaska']['propietario']=0
        for n in j.tablero[p]['fronteras']:
            j.tablero[n]['propietario']=1
            j.tablero[n]['ejercitos']=2
        return p,list(j.tablero[p]['fronteras'])

    def test_bloqueo_tres_vecinos_mismo_color_dos_fichas_y_no_puede_incorporar(self):
        j=self.j
        p,vecinos=self.preparar_bloqueo_brasil()
        self.assertGreaterEqual(len(vecinos),3)
        self.assertTrue(j._pais_bloqueado(p))
        j.etapa='hostilidades';j.fase=FASE_INCORPORAR
        j.turno_idx=0;j.ejercitos_a_colocar=5
        self.assertFalse(j.incorporar(p,1))
        self.assertEqual(j.ejercitos_a_colocar,5)

    def test_bloqueo_no_vale_con_un_vecino_de_un_ejercito(self):
        p,vecinos=self.preparar_bloqueo_brasil()
        self.j.tablero[vecinos[0]]['ejercitos']=1
        self.assertFalse(self.j._pais_bloqueado(p))

    def test_bloqueo_no_vale_con_colores_distintos(self):
        p,vecinos=self.preparar_bloqueo_brasil()
        self.j.tablero[vecinos[0]]['propietario']=2
        self.assertFalse(self.j._pais_bloqueado(p))

    def test_bloqueo_no_vale_con_menos_de_tres_limites(self):
        self.assertEqual(len(self.j.tablero['Venezuela']['fronteras']),2)
        for n in self.j.tablero['Venezuela']['fronteras']:
            self.j.tablero[n]['propietario']=1
            self.j.tablero[n]['ejercitos']=2
        self.j.tablero['Venezuela']['propietario']=0
        self.assertFalse(self.j._pais_bloqueado('Venezuela'))

    def test_bloqueo_se_anula_si_pais_unico(self):
        p,vecinos=self.preparar_bloqueo_brasil()
        for t in self.j.tablero:
            if t!=p and self.j.tablero[t]['propietario']==0:
                self.j.tablero[t]['propietario']=2
        self.assertEqual(self.j.paises_de(0),[p])
        self.assertFalse(self.j._pais_bloqueado(p))

    def test_pais_bloqueado_si_puede_atacar(self):
        p,vecinos=self.preparar_bloqueo_brasil()
        j=self.j
        j.etapa='hostilidades';j.fase=FASE_ATACAR;j.turno_idx=0;j.situacion='Clásico'
        self.assertTrue(j._pais_bloqueado(p))
        self.assertTrue(j.puede_atacar_desde(p))
        with patch('logic.random.randint',return_value=1):
            resultado=j.atacar(p,vecinos[0])
        self.assertTrue(resultado['ok'])

    def test_condominio_no_cuenta_como_un_unico_color_bloqueador(self):
        p,vecinos=self.preparar_bloqueo_brasil()
        self.j.condominios[vecinos[0]]={1:2,2:2}
        self.j._sincronizar_condominio(vecinos[0])
        self.assertFalse(self.j._pais_bloqueado(p))

    def test_carta_continental_se_retira_en_conquista_durante_turno_ajeno(self):
        j=self.j;pl=self.controlar('Europa',dueno=0)
        j._actualizar_tarjetas_continente(pl)
        self.assertIn('Europa',pl.cartas_continente)
        j.tablero['Egipto']['propietario']=1
        j.tablero['Egipto']['ejercitos']=10
        j.tablero['Polonia']['ejercitos']=1
        j.turno_idx=1;j.etapa='hostilidades';j.fase=FASE_ATACAR;j.ronda=3
        j.situacion='Clásico'
        self.assertTrue(j.son_adyacentes('Egipto','Polonia'))
        with patch('logic.random.randint',side_effect=[6,6,6,1]):
            r=j.atacar('Egipto','Polonia')
        self.assertTrue(r['conquisto'])
        self.assertNotIn('Europa',pl.cartas_continente)
        self.assertNotIn('Europa',pl.continentes_usados)
        self.assertTrue(any('pierde tarjeta de continente: Europa' in l for l in j.historial))
        j.turno_idx=0;j.fase=FASE_INCORPORAR
        self.assertIsNone(j.opcion_canje(pl))
        self.assertFalse(j.canje_valido(continentes=['Europa']))
        self.assertEqual(j.canjear_tarjetas(continente='Europa'),0)

    def test_pais_recuperado_permte_recuperar_carta_no_usada(self):
        j=self.j;pl=self.controlar('Europa',dueno=0)
        j._actualizar_tarjetas_continente(pl)
        j.tablero['Polonia']['propietario']=1
        j._revocar_tarjetas_continente_por_perdida('Europa')
        self.assertNotIn('Europa',pl.cartas_continente)
        j.tablero['Polonia']['propietario']=0
        j._actualizar_tarjetas_continente(pl)
        self.assertIn('Europa',pl.cartas_continente)
        j.turno_idx=0;j.etapa='hostilidades';j.fase=FASE_INCORPORAR;j.ronda=3
        self.assertEqual(j.canjear_tarjetas(continente='Europa'),6)
        self.assertIn('Europa',pl.continentes_usados)
        self.assertNotIn('Europa',pl.cartas_continente)
        j.tablero['Polonia']['propietario']=1
        j._revocar_tarjetas_continente_por_perdida('Europa')
        j.tablero['Polonia']['propietario']=0
        j._actualizar_tarjetas_continente(pl)
        self.assertNotIn('Europa',pl.cartas_continente)
        self.assertEqual(j.canjear_tarjetas(continente='Europa'),0)

    def test_no_puede_canjear_carta_continental_almacenada_si_pierde_continente(self):
        j=self.j;pl=self.controlar('Asia',dueno=0)
        pl.cartas_continente.add('Asia')
        j.tablero['China']['propietario']=1  # simula un estado previo sin sincronización
        j.turno_idx=0;j.etapa='hostilidades';j.fase=FASE_INCORPORAR;j.ronda=3
        self.assertIsNone(j.opcion_canje(pl))
        self.assertFalse(j.canje_valido(continentes=['Asia']))
        self.assertEqual(j.canjear_tarjetas(continente='Asia'),0)

    def test_tarjeta_de_continente_perdida_por_condominio(self):
        j=self.j;pl=self.controlar('Africa',dueno=0)
        j._actualizar_tarjetas_continente(pl)
        self.assertIn('Africa',pl.cartas_continente)
        j.condominios['Egipto']={0:2,1:2}
        j._sincronizar_condominio('Egipto')
        self.assertNotIn('Africa',pl.cartas_continente)

    def test_conexiones_eliminadas_y_mapa_conexo(self):
        for x,y in (('Nueva York','Terranova'),('Noruega','Bielorrusia')):
            with self.subTest(a=x,b=y):
                self.assertNotIn(y,PAISES_DATA[x]['fronteras'])
                self.assertNotIn(x,PAISES_DATA[y]['fronteras'])
        for p,d in PAISES_DATA.items():
            for vecino in d['fronteras']:
                self.assertIn(p,PAISES_DATA[vecino]['fronteras'])
        inicio=next(iter(PAISES_DATA));vistos={inicio};cola=deque([inicio])
        while cola:
            p=cola.popleft()
            for q in PAISES_DATA[p]['fronteras']:
                if q not in vistos:vistos.add(q);cola.append(q)
        self.assertEqual(len(vistos),72)


if __name__=='__main__':unittest.main()
