"""Pruebas del motor sin dependencias gráficas: python -m unittest -v."""
import random
import unittest
from collections import Counter
from pathlib import Path
from struct import unpack
from unittest.mock import patch
from data import PAISES_DATA, CONTINENTES, FIGURAS_POR_PAIS, ejercitos_por_paises, COLORES_OFICIALES
from logic import (JuegoTEG, FASE_ATACAR, FASE_INCORPORAR, FASE_REAGRUPAR, FASE_TARJETA,
                   _objetivos_oficiales, _tres_figuras_validas)


class Reglas(unittest.TestCase):
    def setUp(self):
        random.seed(19)
        self.j=JuegoTEG(4)

    def preparar_ataque(self, origen='Alaska', destino='Canada', atk=10, defensor=2):
        j=self.j
        j.etapa='hostilidades';j.ronda=2;j.fase=FASE_ATACAR
        j.situacion='Clásico';j.turno_idx=0
        j.tablero[origen]['propietario']=0;j.tablero[origen]['ejercitos']=atk
        j.tablero[destino]['propietario']=1;j.tablero[destino]['ejercitos']=defensor
        return j

    def test_72_y_fronteras(self):
        self.assertEqual(len(PAISES_DATA),72)
        for pais,data in PAISES_DATA.items():
            for vecino in data['fronteras']:
                self.assertIn(vecino, PAISES_DATA)
                self.assertIn(pais, PAISES_DATA[vecino]['fronteras'])

    def test_fronteras_corregidas_por_usuario(self):
        """Conexiones v3 que siguen vigentes después de las correcciones de v8."""
        agregadas = [
            ('Turquia','China'), ('Irak','Israel'),
            ('India','Vietnam'), ('Corea','Malasia'), ('Corea','Vietnam'),
            ('Vietnam','Filipinas'), ('Bielorrusia','Polonia'),
            ('Polonia','Croacia'), ('Polonia','Albania'),
            ('Alemania','Italia'), ('Gran Bretana','Portugal'),
            ('Egipto','Madagascar'),
        ]
        eliminadas = [
            ('Alaska','Oregon'), ('Isla Victoria','Labrador'),
            ('Labrador','Nueva York'), ('Nueva York','Florida'),
            ('Florida','Mexico'), ('Las Vegas','Mexico'),
            ('Honduras','Nicaragua'),
            ('Gran Bretana','Islandia'), ('Gran Bretana','Francia'),
            ('Gran Bretana','Espana'), ('Finlandia','Rusia'),
            ('Croacia','Albania'), ('Albania','Serbia'),
            ('Ucrania','Serbia'), ('Irak','India'),
            ('Arabia','India'), ('China','Vietnam'),
            ('Malasia','Filipinas'), ('Malasia','Sumatra'),
            ('Sumatra','Filipinas'), ('Australia','Nueva Zelanda'),
        ]
        self.assertEqual(len(agregadas),12)
        self.assertEqual(len(eliminadas),21)
        for a,b in agregadas:
            with self.subTest(alta=f'{a}-{b}'):
                self.assertIn(b,PAISES_DATA[a]['fronteras'])
                self.assertIn(a,PAISES_DATA[b]['fronteras'])
        for a,b in eliminadas:
            with self.subTest(baja=f'{a}-{b}'):
                self.assertNotIn(b,PAISES_DATA[a]['fronteras'])
                self.assertNotIn(a,PAISES_DATA[b]['fronteras'])

    def test_mazo_situaciones_cincuenta_cartas_exactas(self):
        """El mazo es finito y contiene las frecuencias del juego de mesa."""
        esperadas={
            'Clásico':20,'Nieve':4,'Crisis':4,'Viento a favor':4,
            'Refuerzos extras':4,'Fronteras abiertas':4,'Fronteras cerradas':4,
        }
        esperadas.update({f'Descanso {color}':1 for color in COLORES_OFICIALES})
        self.assertEqual(len(self.j.mazo_situacion),50)
        self.assertEqual(Counter(self.j.mazo_situacion),esperadas)
        self.assertEqual(self.j.descarte_situacion,[])

    def test_descanso_ausente_consumido_y_convertido_en_clasico(self):
        j=JuegoTEG(2,color_humano=0)
        self.assertTrue(all(jugador.color_nombre!='Verde' for jugador in j.jugadores))
        j.mazo_situacion=['Nieve','Descanso Verde']
        j.descarte_situacion=[]
        j._siguiente_situacion()
        self.assertEqual(j.situacion,'Clásico')
        self.assertEqual(j.mazo_situacion,['Nieve'])
        self.assertEqual(j.descarte_situacion,['Descanso Verde'])
        j._siguiente_situacion()
        self.assertEqual(j.situacion,'Nieve')
        self.assertEqual(len(j.descarte_situacion),2)

    def test_descanso_presente_aplica_y_carta_se_descarta(self):
        j=JuegoTEG(3,color_humano=0)
        j.mazo_situacion=['Descanso Rojo']
        j.descarte_situacion=[]
        j._siguiente_situacion()
        self.assertEqual(j.situacion,'Descanso Rojo')
        self.assertEqual(j.descarte_situacion,['Descanso Rojo'])

    def test_desglose_refuerzos_y_restriccion_continental_en_vivo(self):
        j=self.j
        j.fase=FASE_INCORPORAR
        j.etapa='preparacion'  # no considerar bloqueos en un montaje sintético
        j.turno_idx=0
        j.tablero['China']['propietario']=0
        j.tablero['Alaska']['propietario']=0
        j.ejercitos_a_colocar=7
        j.refuerzos_continente={'Asia':3}
        self.assertEqual(j.desglose_incorporacion(),{
            'libres':4,'continentes':{'Asia':3},'total':7})
        self.assertTrue(j.incorporar('China',2))
        self.assertEqual(j.desglose_incorporacion(),{
            'libres':4,'continentes':{'Asia':1},'total':5})
        self.assertTrue(j.incorporar('Alaska',3))
        self.assertEqual(j.desglose_incorporacion(),{
            'libres':1,'continentes':{'Asia':1},'total':2})
        self.assertFalse(j.incorporar('Alaska',2))
        self.assertEqual(j.desglose_incorporacion()['total'],2)
        self.assertTrue(j.incorporar('China',1))
        self.assertEqual(j.desglose_incorporacion(),{
            'libres':1,'continentes':{},'total':1})

    def test_misil_conquistado_permanece_y_se_puede_usar(self):
        j=self.preparar_ataque(atk=10,defensor=1)
        j.tablero['Canada']['misiles']=2
        j.tablero['Oregon']['propietario']=2
        j.tablero['Oregon']['ejercitos']=7
        with patch('logic.random.randint',side_effect=[6,6,6,1]):
            resultado=j.atacar('Alaska','Canada',3)
        self.assertTrue(resultado['conquisto'])
        self.assertEqual(j.tablero['Canada']['propietario'],0)
        self.assertEqual(j.tablero['Canada']['misiles'],2)
        self.assertTrue(any('MISILES CAPTURADOS' in item for item in j.historial))
        self.assertTrue(j.resolver_conquista(2))
        self.assertTrue(j.lanzar_misil('Oregon',desde='Canada'))
        self.assertEqual(j.tablero['Canada']['misiles'],1)
        self.assertEqual(j.tablero['Oregon']['ejercitos'],4)

    def test_graficos_rotados_y_sprite_misil_png(self):
        carpeta=Path(__file__).parent
        tamaños={
            'Granada':(57,76),'Tanque':(68,76),'Avion':(76,67),
            'Soldado':(57,76),'Barco':(66,76),
        }
        for nombre,(ancho,alto) in tamaños.items():
            archivo=carpeta/'iconos_cartas'/f'{nombre}.png'
            with open(archivo,'rb') as f:
                cabecera=f.read(24)
            self.assertEqual(cabecera[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(unpack('>II',cabecera[16:24]),(ancho,alto))
        icono=carpeta/'iconos_ui'/'misil.png'
        self.assertTrue(icono.is_file())
        with open(icono,'rb') as f:
            cabecera=f.read(26)
        self.assertEqual(cabecera[:8],b'\x89PNG\r\n\x1a\n')
        self.assertEqual(cabecera[25],6)  # PNG RGBA con transparencia

    def test_refuerzos_minimos_y_adicionales(self):
        """Con 0-7 países hay mínimo de cuatro; crece cada dos a partir de 10."""
        for n in range(0,72):
            self.assertEqual(ejercitos_por_paises(n),max(4,n//2))
        for n in (6,7):
            for d in self.j.tablero.values():
                d['propietario']=1
            for pais in list(self.j.tablero)[:n]:
                self.j.tablero[pais]['propietario']=0
            self.j.situacion='Clásico'
            self.assertEqual(self.j._calcular_incorporacion(self.j.jugadores[0]),4)

    def test_bonos_reglamento(self):
        self.assertEqual({c:d['bonus'] for c,d in CONTINENTES.items()},
                         {'America del Norte':6,'America Central':3,'America del Sur':4,
                          'Europa':8,'Asia':8,'Africa':4,'Oceania':3})
        self.assertEqual(ejercitos_por_paises(1),4)
        self.assertEqual(ejercitos_por_paises(5),4)
        self.assertEqual(ejercitos_por_paises(6),4)
        self.assertEqual(ejercitos_por_paises(7),4)
        self.assertEqual(ejercitos_por_paises(8),4)
        self.assertEqual(ejercitos_por_paises(9),4)
        self.assertEqual(ejercitos_por_paises(10),5)
        self.assertEqual(ejercitos_por_paises(19),9)


    def test_refuerzos_en_bloque_antes_de_ataques(self):
        """En ronda 2+ todos incorporan antes de la primera fase de ataque."""
        for n in (2,3,4,6):
            with self.subTest(jugadores=n):
                j=JuegoTEG(n,orden_inicial=list(range(n)))
                for vuelta in range(1 if n==2 else 2):
                    for jugador in range(n):
                        self.assertEqual(j.turno_idx,jugador)
                        self.assertTrue(j.incorporar(j.paises_de(jugador)[0],j.ejercitos_a_colocar))
                self.assertEqual((j.ronda,j.fase,j.etapa_ronda),(1,FASE_ATACAR,'ATAQUE'))
                for jugador in range(n):
                    self.assertEqual(j.turno_idx,jugador)
                    for _ in range(3):self.assertTrue(j.avanzar_fase())
                self.assertEqual(j.ronda,2)
                self.assertEqual(j.etapa_ronda,'INCORPORACION')
                orden=j.orden_ronda.copy()
                self.assertEqual(orden,list(range(1,n))+[0])
                for pos,jugador in enumerate(orden):
                    self.assertEqual(j.turno_idx,jugador)
                    self.assertEqual(j.fase,FASE_INCORPORAR)
                    # Resolver primero refuerzos obligatorios por continente.
                    while any(j.refuerzos_continente.values()):
                        c=next(c for c,v in j.refuerzos_continente.items() if v>0)
                        p=next(p for p in j.paises_de(jugador)
                               if j.tablero[p]['continente']==c and not j._pais_bloqueado(p))
                        self.assertTrue(j.incorporar(p,j.refuerzos_continente[c]))
                    if j.fase==FASE_INCORPORAR:
                        p=next(p for p in j.paises_de(jugador) if not j._pais_bloqueado(p))
                        self.assertTrue(j.incorporar(p,j.ejercitos_a_colocar))
                    if pos<n-1:
                        self.assertEqual(j.fase,FASE_INCORPORAR)
                        self.assertEqual(j.turno_idx,orden[pos+1])
                        self.assertEqual(j.etapa_ronda,'INCORPORACION')
                self.assertEqual(j.etapa_ronda,'ATAQUE')
                self.assertEqual(j.fase,FASE_ATACAR)
                self.assertEqual(j.turno_idx,orden[0])
                self.assertEqual(j.ejercitos_a_colocar,0)
                for jugador in orden:
                    self.assertEqual(j.turno_idx,jugador)
                    self.assertEqual(j.fase,FASE_ATACAR)
                    for _ in range(3):self.assertTrue(j.avanzar_fase())
                self.assertEqual(j.ronda,3)
                self.assertEqual(j.fase,FASE_INCORPORAR)
                self.assertEqual(j.etapa_ronda,'INCORPORACION')

    def test_objetivos_de_destruccion_opcionales(self):
        for n in (4,5,6):
            j=JuegoTEG(n,objetivos_eliminacion=False)
            self.assertFalse(j.objetivos_eliminacion)
            for jugador in j.jugadores:
                self.assertTrue(jugador.objetivos)
                self.assertTrue(all(o['tipo']=='ocupacion' for o in jugador.objetivos))
        # Con 2 o 3 no aparecen objetivos destructivos, incluso con opción activa.
        for n in (2,3):
            j=JuegoTEG(n,objetivos_eliminacion=True)
            self.assertTrue(all(o['tipo']=='ocupacion' for pl in j.jugadores for o in pl.objetivos))

    def test_tarjetas_objetivo_tienen_imagen_por_identificador(self):
        from pathlib import Path
        carpeta=Path(__file__).with_name('objetivos_imagenes')
        misiones=_objetivos_oficiales()
        self.assertEqual([o['tarjeta_id'] for o in misiones],list(range(19)))
        for mision in misiones:
            archivo=carpeta / f"obj_{mision['tarjeta_id']:02d}.png"
            self.assertTrue(archivo.is_file(),archivo.name)
            self.assertGreater(archivo.stat().st_size,1000)

    def test_bots_con_perfiles_variados_y_tacticas_validas(self):
        for n in (3,6):
            j=JuegoTEG(n)
            perfiles=[p.estilo_bot for p in j.jugadores[1:]]
            self.assertEqual(len(perfiles),len(set(perfiles)))
            self.assertTrue(set(perfiles) <= {'Agresivo','Defensivo','Objetivo','Oportunista','Equilibrado'})
            self.assertIsNone(j.jugadores[0].estilo_bot)
            # Cada IA elige países propios, sin inventar refuerzos ni mover fuera del turno.
            j.turno_idx=1
            for _ in range(1):
                antes=j.ejercitos_a_colocar
                actual=j.turno_idx
                estado=j.paso_bot()
                self.assertIsNotNone(estado)
                self.assertEqual(j.turno_idx,actual)
                self.assertLess(j.ejercitos_a_colocar,antes)
                self.assertEqual(sum(d['ejercitos'] for d in j.tablero.values()),
                                 72+(18 if n==2 else 8)-j.ejercitos_a_colocar)

    def test_preparacion_por_cantidad(self):
        for n in range(2,7):
            j=JuegoTEG(n)
            self.assertEqual([len(j.paises_de(i)) for i in range(n)].count(0),0)
            self.assertEqual(sum(len(j.paises_de(i)) for i in range(n)),72)
            self.assertEqual(j.ejercitos_a_colocar,18 if n==2 else 8)
            self.assertEqual(len(j.jugadores[0].objetivos),2 if n==2 else 1)
            for _ in range(1 if n==2 else 2):
                for jugador in j.orden_base:
                    self.assertEqual(j.turno_idx,jugador)
                    cantidad=j.ejercitos_a_colocar
                    self.assertTrue(j.incorporar(j.paises_de(jugador)[0],cantidad))
            self.assertEqual(j.etapa,'hostilidades')
            self.assertEqual(j.fase,FASE_ATACAR)
            self.assertEqual(j.ejercitos_a_colocar,0)
            self.assertEqual(j.ronda,1)

    def test_objetivos_secretos(self):
        self.assertEqual(len(_objetivos_oficiales()),19)
        for n in (2,3,4,5,6):
            j=JuegoTEG(n)
            for pl in j.jugadores:
                for obj in pl.objetivos:
                    self.assertIn(obj['tipo'],('ocupacion','eliminacion'))
                    if n<=3:self.assertEqual(obj['tipo'],'ocupacion')

    def test_victoria_comun(self):
        j=self.preparar_ataque()
        for i,p in enumerate(j.tablero):
            j.tablero[p]['propietario']=0 if i<45 else 1
        self.assertTrue(j._verificar_victoria(j.jugadores[0]))
        self.assertEqual(j.ganador_idx,0)

    def test_victoria_ocupacion_tipos(self):
        j=self.preparar_ataque()
        mision=next(o for o in _objetivos_oficiales() if 'Europa y América del Sur' in o['descripcion'])
        j.jugadores[0].objetivos=[mision]
        j.jugadores[0].objetivo=mision
        for p in j.tablero:
            j.tablero[p]['propietario']=1
        self.assertFalse(j._verificar_victoria(j.jugadores[0]))
        for p in j.tablero:
            if j.tablero[p]['continente'] in ('Europa','America del Sur'):
                j.tablero[p]['propietario']=0
        self.assertTrue(j._verificar_victoria(j.jugadores[0]))

    def test_premio_continentes_y_restriccion_colocacion(self):
        j=self.j
        j.etapa='hostilidades';j.ronda=2;j.fase=FASE_INCORPORAR
        for p,d in j.tablero.items():
            d['propietario']=0 if d['continente']=='Oceania' else 1
        ref=j._calcular_incorporacion(j.jugadores[0])
        self.assertEqual(ref,4+3)
        j.ejercitos_a_colocar=ref
        self.assertFalse(j.incorporar('Alaska',1))
        self.assertTrue(j.incorporar('Australia',3))
        self.assertEqual(j.refuerzos_continente['Oceania'],0)

    def test_combates_empate_defensor(self):
        j=self.preparar_ataque(atk=4,defensor=3)
        with patch('logic.random.randint',return_value=6):
            r=j.atacar('Alaska','Canada',3)
        self.assertTrue(r['ok'])
        self.assertEqual(r['bajas_atk'],3)
        self.assertEqual(r['bajas_def'],0)
        self.assertEqual(j.tablero['Alaska']['ejercitos'],1)

    def test_combate_4_dados_y_nieve(self):
        j=self.preparar_ataque(atk=10,defensor=4)
        with patch('logic.random.randint',return_value=1):
            r=j.atacar('Alaska','Canada',4)
        self.assertEqual(len(r['dados_atk']),4)
        self.assertEqual(len(r['dados_def']),3)
        j.situacion='Nieve';j.tablero['Alaska']['ejercitos']=10
        with patch('logic.random.randint',return_value=1):
            r=j.atacar('Alaska','Canada',4)
        self.assertEqual(len(r['dados_def']),4)

    def test_ocupacion_humana_min_y_max(self):
        j=self.preparar_ataque(atk=9,defensor=1)
        with patch('logic.random.randint',side_effect=[6,6,6,1]):
            r=j.atacar('Alaska','Canada',3)
        self.assertTrue(r['conquisto'])
        self.assertEqual(j.tablero['Canada']['ejercitos'],0)
        self.assertFalse(j.pasar_fase())
        self.assertFalse(j.resolver_conquista(4))
        self.assertTrue(j.resolver_conquista(2))
        self.assertEqual(j.tablero['Canada']['ejercitos'],2)
        self.assertEqual(j.tablero['Alaska']['ejercitos'],7)

    def test_misiles_alcance_y_escudo(self):
        j=self.preparar_ataque(atk=7,defensor=7)
        self.assertTrue(j.incorporar_misil('Alaska',reemplazar=True) is False) # solo en INCORPORAR
        j.fase=FASE_INCORPORAR
        self.assertTrue(j.incorporar_misil('Alaska',reemplazar=True))
        j.fase=FASE_ATACAR
        self.assertEqual(j.tablero['Alaska']['misiles'],1)
        self.assertEqual(j.tablero['Alaska']['ejercitos'],1)
        self.assertTrue(j.lanzar_misil('Canada',desde='Alaska'))
        self.assertEqual(j.tablero['Canada']['ejercitos'],4)
        self.assertEqual(j.tablero['Alaska']['misiles'],0)
        j.tablero['Alaska']['misiles']=1
        j.tablero['Canada']['misiles']=1
        self.assertFalse(j.lanzar_misil('Canada',desde='Alaska'))
        j.tablero['Canada']['misiles']=0
        j.tablero['Canada']['ejercitos']=3
        self.assertFalse(j.lanzar_misil('Canada',desde='Alaska'))

    def test_canjes(self):
        j=self.j
        self.assertEqual([j.valor_canje() for _ in [1]], [6])
        valores=[]
        for n in range(7):
            j.jugador_actual().canjes_realizados=n
            valores.append(j.valor_canje())
        self.assertEqual(valores,[6,10,15,20,25,30,35])
        self.assertTrue(_tres_figuras_validas(['Avion','Soldado','Barco']))
        self.assertFalse(_tres_figuras_validas(['Avion','Avion','Barco']))

    def test_reagrupe_no_doble_movimiento(self):
        j=self.preparar_ataque()
        j.fase=FASE_REAGRUPAR
        for p in ('Alaska','Canada','Oregon'):
            j.tablero[p]['propietario']=0
        j.tablero['Alaska']['ejercitos']=10
        j.tablero['Canada']['ejercitos']=1
        j.tablero['Oregon']['ejercitos']=1
        self.assertTrue(j.reagrupar('Alaska','Canada',6))
        self.assertFalse(j.reagrupar('Canada','Oregon',6))

    def test_eliminacion_tarjetas(self):
        j=self.preparar_ataque()
        for p in j.tablero:j.tablero[p]['propietario']=0
        j.tablero['Canada']['propietario']=1
        j.jugadores[1].tarjetas=['Alaska','Brasil']
        j.tablero['Canada']['propietario']=0
        j._ultimo_atacante=0
        j._verificar_eliminacion(1,0)
        self.assertTrue(j.jugadores[1].eliminado)
        self.assertIn('Brasil',j.jugadores[0].tarjetas)
        self.assertEqual(j.jugadores[1].tarjetas,[])

    def test_smoke_bots_y_invariantes(self):
        for n in range(2,7):
            random.seed(n+100)
            j=JuegoTEG(n)
            for _ in range(100):
                if j.fase=='VICTORIA':break
                if j.jugador_actual().es_bot:
                    j.turno_bot()
                elif j.fase==FASE_INCORPORAR:
                    if j.refuerzos_continente:
                        con=next((c for c,x in j.refuerzos_continente.items() if x>0),None)
                        if con:
                            p=next(p for p in j.paises_de(0) if j.tablero[p]['continente']==con and not j._pais_bloqueado(p))
                            self.assertTrue(j.incorporar(p,1))
                            continue
                    p=next(p for p in j.paises_de(0) if not j._pais_bloqueado(p) or j.etapa=='preparacion')
                    self.assertTrue(j.incorporar(p,j.ejercitos_a_colocar))
                else:
                    self.assertTrue(j.pasar_fase())
                self.assertEqual(sum(len(j.paises_de(i)) for i in range(n)),72)
                self.assertTrue(all(d['ejercitos']>=1 for d in j.tablero.values()))
            self.assertGreaterEqual(j.ronda,1)

    def test_primera_ronda_hostilidades_sin_refuerzos(self):
        j=JuegoTEG(3)
        for _ in range(2):
            for k in range(3):
                self.assertTrue(j.incorporar(j.paises_de(k)[0],j.ejercitos_a_colocar))
        self.assertEqual(j.fase,FASE_ATACAR)
        self.assertTrue(j.pasar_fase())
        self.assertTrue(j.pasar_fase())
        self.assertEqual(j.fase,FASE_TARJETA)
        self.assertTrue(j.pasar_fase())
        self.assertEqual(j.turno_idx,j.orden_base[1])
        self.assertEqual(j.fase,FASE_ATACAR)
        self.assertEqual(j.ejercitos_a_colocar,0)

    def test_distancia_misiles_dos_y_tres(self):
        j=self.preparar_ataque('Alaska','Canada',7,8)
        j.tablero['Alaska']['misiles']=3
        self.assertEqual(j.distancia('Alaska','Terranova'),2)
        self.assertEqual(j.distancia('Alaska','Chicago'),3)
        for objetivo,daño in [('Terranova',2),('Chicago',1)]:
            j.tablero[objetivo]['propietario']=1
            j.tablero[objetivo]['ejercitos']=8
            self.assertTrue(j.lanzar_misil(objetivo,desde='Alaska'))
            self.assertEqual(j.tablero[objetivo]['ejercitos'],8-daño)

    def test_canje_supertarjeta_y_continentes(self):
        j=self.j
        j.fase=FASE_INCORPORAR;j.etapa='hostilidades';j.ronda=5
        pl=j.jugador_actual()
        # El segundo PDF no contiene supertarjetas de país: canje con 3 cartas válidas.
        pl.tarjetas=['Angola','Alemania','Albania']
        self.assertEqual(j.opcion_canje(pl),([0,1,2],[]))
        self.assertEqual(j.canjear_tarjetas(),6)
        self.assertEqual(pl.tarjetas,[])
        self.assertEqual(j.canjear_tarjetas(),0) # máximo 1 canje
        j.ronda+=1
        # La carta solo puede canjearse si todavía controla TODO el continente.
        for pais, datos in j.tablero.items():
            if datos['continente']=='Europa': datos['propietario']=j.turno_idx
        pl.cartas_continente.add('Europa')
        self.assertEqual(j.canjear_tarjetas(),10)
        self.assertIn('Europa',pl.continentes_usados)
        j.ronda+=1
        pl.tarjetas=[next(p for p,f in j.figuras_cartas.items() if f=='Barco')]
        for pais, datos in j.tablero.items():
            if datos['continente']=='Africa': datos['propietario']=j.turno_idx
        pl.cartas_continente.add('Africa')
        # África = avión+barco, se necesitan las 3 variables: barco+barco+avión no vale
        self.assertIsNone(j.opcion_canje(pl))
        pl.tarjetas=[next(p for p,f in j.figuras_cartas.items() if f=='Tanque')]
        self.assertEqual(j.canjear_tarjetas(),15) # África + Tanque, tres distintos

    def test_descanso_viento_y_fronteras(self):
        j=self.preparar_ataque('Alaska','Canada',6,1)
        j.situacion='Descanso Blanco'
        self.assertFalse(j.atacar('Alaska','Canada',3)['ok'])
        j.situacion='Viento a favor'
        with patch('logic.random.randint',return_value=1):
            r=j.atacar('Alaska','Canada',4)
        self.assertEqual(len(r['dados_atk']),4)
        j=self.preparar_ataque('Alaska','Chukchi',6,1)
        j.situacion='Fronteras cerradas'
        self.assertFalse(j.atacar('Alaska','Chukchi',3)['ok'])
        j.situacion='Fronteras abiertas'
        self.assertTrue(j.atacar('Alaska','Chukchi',3)['ok'])

    def test_figuras_pdf_72_reales(self):
        from collections import Counter
        self.assertEqual(len(FIGURAS_POR_PAIS),72)
        self.assertEqual(set(FIGURAS_POR_PAIS),set(PAISES_DATA))
        self.assertEqual(Counter(FIGURAS_POR_PAIS.values()),
                         {'Soldado':4,'Granada':5,'Tanque':21,'Avion':21,'Barco':21})
        self.assertEqual(FIGURAS_POR_PAIS['Alaska'],'Soldado')
        self.assertEqual(FIGURAS_POR_PAIS['Polonia'],'Tanque')
        self.assertEqual(FIGURAS_POR_PAIS['Brasil'],'Avion')
        self.assertEqual(FIGURAS_POR_PAIS['Francia'],'Barco')
        self.assertEqual(FIGURAS_POR_PAIS['Argentina'],'Granada')

    def test_colores_elegibles_y_descanso_verdadero(self):
        for color in range(6):
            j=JuegoTEG(4,color_humano=color,orden_inicial=[1,3,0,2])
            self.assertEqual(j.jugadores[0].color_nombre,COLORES_OFICIALES[color])
            self.assertEqual(len({x.color_nombre for x in j.jugadores}),4)
            self.assertEqual(j.orden_ronda,[1,3,0,2])
        with self.assertRaises(ValueError):JuegoTEG(3,color_humano=6)

    def test_rotacion_exacta_con_turnos_aleatorios(self):
        j=JuegoTEG(4,orden_inicial=[2,0,3,1])
        self.assertEqual(j.turno_idx,2)
        for i in [2,0,3,1,2,0,3,1]:
            self.assertEqual(j.turno_idx,i)
            self.assertTrue(j.incorporar(j.paises_de(i)[0],j.ejercitos_a_colocar))
        self.assertEqual(j.fase,FASE_ATACAR)
        self.assertEqual(j.orden_ronda,[2,0,3,1])
        self.assertEqual(j.orden_visual_jugadores(),[2,0,3,1])
        for i in [2,0,3,1]:
            self.assertEqual(j.turno_idx,i)
            self.assertTrue(j.pasar_fase())  # reagrupar
            self.assertTrue(j.pasar_fase())  # tarjetas
            self.assertTrue(j.pasar_fase())  # siguiente
        self.assertEqual(j.orden_ronda,[0,3,1,2])
        self.assertEqual(j.orden_visual_jugadores(),[0,3,1,2])
        self.assertEqual(j.turno_idx,0)
        self.assertEqual(j.ronda,2)
        self.assertEqual(j.fase,FASE_INCORPORAR)

    def test_orden_visual_eliminados_al_final(self):
        j=JuegoTEG(4,orden_inicial=[2,0,3,1])
        j.jugadores[0].eliminado=True
        self.assertEqual(j.orden_visual_jugadores(),[2,3,1,0])
        # Los índices/color originales permanecen intactos.
        self.assertEqual(j.turno_idx,2)
        self.assertEqual(len(j.jugadores),4)

    def test_ataque_siempre_dados_maximos(self):
        j=self.preparar_ataque(atk=9,defensor=4)
        with patch('logic.random.randint',return_value=6):
            res=j.atacar('Alaska','Canada',1)
        self.assertEqual(len(res['dados_atk']),4)  # 4 permitidos por ventaja
        self.assertEqual(res['bajas_atk'],3)

    def test_solicitud_tarjeta_explicita_una_por_turno(self):
        j=self.j
        j.etapa='hostilidades';j.fase=FASE_REAGRUPAR;j.ronda=4
        jugador=j.jugador_actual()
        j.conquistas_turno=1
        inicio=len(jugador.tarjetas)
        self.assertFalse(j.puede_solicitar_tarjeta())
        self.assertTrue(j.avanzar_fase())
        self.assertEqual(j.fase,FASE_TARJETA)
        self.assertEqual(len(jugador.tarjetas),inicio)
        carta=j.solicitar_tarjeta()
        self.assertIn(carta,FIGURAS_POR_PAIS)
        self.assertFalse(j.puede_solicitar_tarjeta())
        self.assertIsNone(j.solicitar_tarjeta())
        self.assertEqual(len(jugador.tarjetas),inicio+1)
        self.assertTrue(j.avanzar_fase())
        self.assertNotEqual(j.turno_idx,jugador.idx)

    def test_umbral_dos_paises_despues_tercer_canje(self):
        j=self.j
        j.etapa='hostilidades';j.fase=FASE_TARJETA;j.ronda=5
        pl=j.jugador_actual();pl.canjes_realizados=3
        j.conquistas_turno=1
        self.assertFalse(j.puede_solicitar_tarjeta())
        j.conquistas_turno=2
        self.assertTrue(j.puede_solicitar_tarjeta())
        pl.tarjetas=['Alaska','Brasil','Italia','Nigeria','Siberia']
        self.assertFalse(j.puede_solicitar_tarjeta())

    def test_canje_manual_valido_igual_distinto_con_comodin(self):
        j=self.j
        j.etapa='hostilidades';j.fase=FASE_INCORPORAR;j.ronda=3
        j.jugador_actual().tarjetas=['Angola','Alemania','Albania','Brasil','Polonia']
        self.assertTrue(j.canje_valido([0,1,2],[]))
        self.assertTrue(j.canje_valido([0,3,4],[]))
        self.assertFalse(j.canje_valido([3,4],[]))
        self.assertEqual(j.canjear_tarjetas(indices=[0,3,4]),6)
        self.assertEqual(j.jugador_actual().tarjetas,['Alemania','Albania'])

    def test_tres_jugadores_requiere_diez_extras(self):
        j=JuegoTEG(3)
        j.etapa='hostilidades';j.fase=FASE_ATACAR
        mision=next(o for o in _objetivos_oficiales() if o.get('completos')==['Europa','America del Sur'])
        j.jugadores[0].objetivos=[mision]
        for p in j.tablero:
            j.tablero[p]['propietario']=1
        mis=[p for p in j.tablero if j.tablero[p]['continente'] in ('Europa','America del Sur')]
        for p in mis:j.tablero[p]['propietario']=0
        self.assertEqual(len(j.paises_de(0)),24)
        self.assertFalse(j._verificar_victoria(j.jugadores[0]))
        for p in list(j.paises_de(1))[:10]:j.tablero[p]['propietario']=0
        self.assertTrue(j._verificar_victoria(j.jugadores[0]))

    def test_bloqueo_rechaza_refuerzos(self):
        j=self.j;j.etapa='hostilidades';j.fase=FASE_INCORPORAR
        p='Brasil'
        j.tablero[p]['propietario']=0
        for vecino in j.tablero[p]['fronteras']:
            j.tablero[vecino]['propietario']=1
            j.tablero[vecino]['ejercitos']=2
        self.assertTrue(j._pais_bloqueado(p))
        j.ejercitos_a_colocar=5
        self.assertFalse(j.incorporar(p,1))


if __name__=='__main__':unittest.main()
