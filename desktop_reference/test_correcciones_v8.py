"""Regresiones v8: conexiones, misiones, ronda clásica y pactos de cinco clases."""
import random
import unittest
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from data import PAISES_DATA, FIGURAS_POR_PAIS
from logic import JuegoTEG, FASE_ATACAR
from test_correcciones_v7 import PactoDeBot


AGREGAR = (
    ('India','Malasia'), ('Chile','Brasil'), ('Oregon','Terranova'),
    ('Nigeria','Sudafrica'), ('Egipto','Polonia'), ('Turquia','Rusia'),
    ('Turquia','Irak'), ('Turquia','Iran'), ('Albania','Iran'),
    ('China','Chukchi'), ('China','Siberia'),
)
QUITAR = (
    ('Turquia','Malasia'), ('Bielorrusia','Rusia'), ('Angola','Sudafrica'),
    ('Egipto','Arabia'), ('Egipto','Croacia'), ('China','Iran'),
)


class FronterasV8(unittest.TestCase):
    def test_las_11_altas_bidireccionales(self):
        self.assertEqual(len(AGREGAR),11)
        for a,b in AGREGAR:
            with self.subTest(paises=(a,b)):
                self.assertIn(b,PAISES_DATA[a]['fronteras'])
                self.assertIn(a,PAISES_DATA[b]['fronteras'])

    def test_las_6_bajas_bidireccionales(self):
        self.assertEqual(len(QUITAR),6)
        for a,b in QUITAR:
            with self.subTest(paises=(a,b)):
                self.assertNotIn(b,PAISES_DATA[a]['fronteras'])
                self.assertNotIn(a,PAISES_DATA[b]['fronteras'])

    def test_grafo_sin_vecinos_falsos_ni_asimetrias(self):
        self.assertEqual(len(PAISES_DATA),72)
        for nombre,datos in PAISES_DATA.items():
            self.assertEqual(len(datos['fronteras']),len(set(datos['fronteras'])))
            self.assertNotIn(nombre,datos['fronteras'])
            for vecino in datos['fronteras']:
                self.assertIn(vecino,PAISES_DATA)
                self.assertIn(nombre,PAISES_DATA[vecino]['fronteras'])
        pendientes={'Alaska'}
        recorridos=set()
        while pendientes:
            p=pendientes.pop()
            if p not in recorridos:
                recorridos.add(p)
                pendientes.update(PAISES_DATA[p]['fronteras'])
        self.assertEqual(len(recorridos),72)

    def test_renombrado_chukchi_en_tablero_y_cartas(self):
        self.assertIn('Chukchi', PAISES_DATA)
        self.assertNotIn('Chokchi',PAISES_DATA)
        self.assertIn('Chukchi', FIGURAS_POR_PAIS)
        self.assertEqual(FIGURAS_POR_PAIS['Chukchi'],'Avion')
        self.assertNotIn('Chokchi',FIGURAS_POR_PAIS)
        j=JuegoTEG(4)
        self.assertIn('Chukchi',j.tablero)
        self.assertIn('Chukchi',j.mazo_cartas_pais)
        self.assertNotIn('Chokchi',j.mazo_cartas_pais)
        self.assertTrue(j.son_adyacentes('China','Chukchi'))
        self.assertEqual(j.distancia('China','Chukchi'),1)


class SituacionesV8(unittest.TestCase):
    def setUp(self):
        random.seed(876)
        self.j=JuegoTEG(4,orden_inicial=[0,1,2,3])

    def test_primera_ronda_no_roba_ni_descarta_y_siempre_es_clasica(self):
        j=self.j
        mazo=list(j.mazo_situacion)
        j.mazo_situacion[-1]='Nieve'  # hubiera salido en la v7
        mazo=list(j.mazo_situacion)
        j._comenzar_hostilidades()
        self.assertEqual(j.ronda,1)
        self.assertEqual(j.situacion,'Clásico')
        self.assertEqual(j.etapa_ronda,'ATAQUE')
        self.assertEqual(j.fase,FASE_ATACAR)
        self.assertEqual(j.mazo_situacion,mazo)
        self.assertEqual(j.descarte_situacion,[])
        self.assertFalse(any('TARJETA DE SITUACIÓN' in t for t in j.historial))

    def test_la_segunda_ronda_roba_una_sola_tarjeta(self):
        j=self.j
        j._comenzar_hostilidades()
        mazo=list(j.mazo_situacion)
        j.turno_idx=j.orden_ronda[-1]
        j._siguiente_jugador()  # termina la primera ronda
        self.assertEqual(j.ronda,2)
        self.assertEqual(j.situacion,mazo[-1])
        self.assertEqual(j.descarte_situacion,[mazo[-1]])
        self.assertEqual(j.mazo_situacion,mazo[:-1])

    def test_ventana_situacion_solo_a_partir_de_segunda_ronda(self):
        modulo=PactoDeBot._importar_interfaz(solo_renderer=False)
        vista=SimpleNamespace(popup=None,vista_tarjetas=None)
        j=self.j
        j._comenzar_hostilidades()
        self.assertFalse(modulo.debe_mostrar_situacion(j,0,vista))
        j.ronda=2
        self.assertTrue(modulo.debe_mostrar_situacion(j,0,vista))
        self.assertFalse(modulo.debe_mostrar_situacion(j,2,vista))
        vista.popup={'tipo':'pacto'}
        self.assertFalse(modulo.debe_mostrar_situacion(j,0,vista))


class PantallaPactosV8(unittest.TestCase):
    def test_firmar_mundial_y_abrir_pactos_sin_keyerror(self):
        j=JuegoTEG(4)
        p=j.proponer_no_agresion(0,1,'mundial')
        self.assertIsNotNone(p)
        self.assertNotIn('paises',p)
        renderer_mod=PactoDeBot._importar_interfaz(solo_renderer=True)
        renderer=renderer_mod.Renderer.__new__(renderer_mod.Renderer)
        renderer.pais_seleccionado=None
        renderer.pais_objetivo=None
        popup=[]
        renderer.mostrar_popup=lambda *args:popup.append(args)
        renderer.mostrar_pactos(j)
        self.assertEqual(popup[0][0],'DIPLOMACIA Y PACTOS')
        self.assertIn('MUNDIAL',popup[0][1])
        self.assertIn('Todo el mundo',popup[0][1])

    def test_descripcion_todas_las_modalidades_y_rupturas(self):
        j=JuegoTEG(4)
        p=[]
        j.tablero['Alaska']['propietario']=0
        j.tablero['Canada']['propietario']=1
        j.tablero['Chicago']['propietario']=1
        j.tablero['Polonia']['propietario']=0
        j.tablero['Egipto']['propietario']=1
        p.append(j.proponer_no_agresion(0,1,'pais',paises=('Alaska','Canada')))
        p.append(j.proponer_no_agresion(0,1,'continente',continente='America del Norte'))
        p.append(j.proponer_no_agresion(0,1,'frontera',continentes=('Europa','Africa')))
        p.append(j.proponer_no_agresion(0,1,'mundial'))
        p.append(j._nuevo_pacto('condominio',0,1,pais='Chile'))
        self.assertTrue(all(p))
        for pacto,contenido in zip(p,('Alaska','America del Norte','Europa','Todo el mundo','Chile')):
            with self.subTest(tipo=pacto['tipo']):
                self.assertIn(contenido,j.descripcion_pacto(pacto))
        self.assertTrue(j.romper_pacto(p[3]['id'],0))
        self.assertIn('RUPTURA PENDIENTE',j.descripcion_pacto(p[3]))

    def test_texto_auxiliar_de_mision_quitado(self):
        fuente=Path(__file__).with_name('renderer.py').read_text(encoding='utf-8')
        self.assertNotIn('Las imágenes corresponden a tus tarjetas de misión.',fuente)


if __name__=='__main__':
    unittest.main()
