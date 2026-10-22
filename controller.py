"""Interacción portable Android/PC para el motor original v16, sin pygame ni Kivy.

La interfaz llama a las acciones públicas; solo este controlador coordina turnos,
popups y eventos visuales. Los módulos de engine no se modifican.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ENGINE = str(BASE / 'engine')
if ENGINE not in sys.path:
    sys.path.insert(0, ENGINE)

from logic import (JuegoTEG, FASE_INCORPORAR, FASE_ATACAR,
                   FASE_REAGRUPAR, FASE_TARJETA)
from data import PAISES_DATA, CONTINENTES, COLORES_OFICIALES
from respuestas_pactos import respuesta_propuesta_bot


class ControlMovil:
    """Adaptador de las APIs v16: mantiene el motor original y los diálogos."""

    VELOCIDADES = [None, 1.1, .55, .25, .09]

    def __init__(self, n_jugadores=4, color_humano=0,
                 objetivos_eliminacion=True, animaciones=True, orden_inicial=None):
        self.juego = JuegoTEG(n_jugadores=n_jugadores, color_humano=color_humano,
                              objetivos_eliminacion=objetivos_eliminacion,
                              orden_inicial=orden_inicial)
        self.animaciones = animaciones
        self.velocidad = 1
        self.origen = None
        self.destino = None
        self.inspeccion = None
        self.dialogo = None
        self.aviso = 'Preparación: incorporá los ejércitos iniciales.'
        self.ultimo_evento = None
        self.fx = None
        self.situacion_anunciada = 0
        self.victoria_mostrada = False
        self.seleccion_cartas = set()
        self.seleccion_continentes = set()
        self._reagrupe_origen = None
        self._agresion_socio = None
        self._agresion_origen = None

    def _dialogo(self, kind, titulo, texto, opciones=(), obligatorio=False):
        self.dialogo = dict(kind=kind, titulo=titulo, texto=texto,
                            opciones=list(opciones), obligatorio=obligatorio)
        return self.dialogo

    def _error(self, texto):
        self.aviso = texto
        self._dialogo('info', 'Acción no permitida', texto, [('Entendido', 'cerrar')])
        return False

    def cerrar_dialogo(self):
        if self.dialogo and self.dialogo['obligatorio']:
            return False
        self.dialogo = None
        return True

    def _evento(self, tipo, origen=None, destino=None, texto='', resultado=None):
        self.fx = dict(tipo=tipo, origen=origen, destino=destino, resultado=resultado)
        if texto:
            self.aviso = texto
        self.ultimo_evento = self.fx

    def tocar_pais(self, pais):
        """Toque corto; durante una negociación solamente permite inspección."""
        if pais not in self.juego.tablero:
            return False
        self.inspeccion = pais
        j = self.juego
        if self.dialogo and self.dialogo['kind'] not in ('pactos', 'info'):
            return True
        if j.fase == 'VICTORIA' or j.jugador_actual().es_bot or j.conquista_pendiente:
            return True
        propio = j.es_propietario(pais, 0)
        if j.fase == FASE_INCORPORAR:
            if propio:
                self.origen, self.destino = pais, None
            else:
                self.aviso = f'{pais}: elegí un territorio de tu color.'
            return True
        if self.origen is None:
            if propio:
                self.origen = pais
                self.destino = None
            else:
                self.aviso = 'Primero elegí un territorio propio como origen.'
        elif pais == self.origen:
            self.origen = self.destino = None
        elif j.fase == FASE_ATACAR and propio:
            self.origen, self.destino = pais, None
        else:
            self.destino = pais
        return True

    def seleccionar_origen(self, pais):
        if pais in self.juego.tablero and self.juego.es_propietario(pais, 0):
            self.origen, self.destino = pais, None
            return True
        return False

    def cancelar_seleccion(self):
        self.origen = self.destino = None

    def acciones_disponibles(self):
        j = self.juego
        human = not j.jugador_actual().es_bot and j.fase != 'VICTORIA'
        if not human or j.conquista_pendiente or (self.dialogo and self.dialogo['obligatorio']):
            return []
        if j.fase == FASE_INCORPORAR:
            a = ['incorporar'] if self.origen and j.es_propietario(self.origen, 0) else []
            if a:
                a += ['misil_nuevo', 'misil_convertir']
            if j.etapa == 'hostilidades': a += ['canje']
            return a + ['pasar']
        if j.fase == FASE_ATACAR:
            return ['atacar', 'lanzar_misil', 'pactos', 'pasar']
        if j.fase == FASE_REAGRUPAR:
            return ['reagrupar', 'reagrupar_misil', 'pactos', 'pasar']
        if j.fase == FASE_TARJETA:
            return (['solicitar_tarjeta'] if j.puede_solicitar_tarjeta() else []) + ['pasar']
        return []

    def accion(self, nombre, cantidad=None):
        j = self.juego
        if nombre == 'cerrar':
            return self.cerrar_dialogo()
        if nombre == 'historial':
            return self._dialogo('historial', 'Historial de la partida',
                                 '\n'.join(j.historial[-50:]) or 'Sin eventos.', [('Cerrar', 'cerrar')])
        if nombre == 'objetivos':
            o = j.jugadores[0].objetivos
            texto = '\n'.join(f'Objetivo {i+1}: {ob["descripcion"]}' for i, ob in enumerate(o))
            return self._dialogo('objetivos', 'Objetivos secretos',
                                 texto + '\nAlternativa: controlar 45 países.', [('Cerrar', 'cerrar')])
        if nombre == 'tarjetas':
            return self.ver_tarjetas()
        if nombre == 'pactos':
            return self.ver_pactos()
        if nombre == 'velocidad':
            self.velocidad = (self.velocidad + 1) % len(self.VELOCIDADES)
            return True
        if nombre == 'animaciones':
            self.animaciones = not self.animaciones
            return True
        if nombre == 'cancelar':
            self.cancelar_seleccion()
            return True
        if self.dialogo and self.dialogo['obligatorio']:
            return False
        if j.jugador_actual().es_bot or j.fase == 'VICTORIA':
            return False
        if nombre == 'pasar':
            if not j.avanzar_fase():
                return self._error('Primero terminá los refuerzos o resolvé la conquista pendiente.')
            self.cancelar_seleccion()
            return True
        if nombre == 'incorporar':
            if j.fase != FASE_INCORPORAR or not self.origen:
                return self._error('Seleccioná un territorio propio para incorporar.')
            if cantidad is None:
                return self._dialogo('refuerzos', 'Incorporar ejércitos',
                                    f'{self.origen}: hay {j.ejercitos_a_colocar} refuerzos pendientes.\n'
                                    f'Libres: {j.desglose_incorporacion()["libres"]}; '
                                    f'continentales: {j.desglose_incorporacion()["continentes"]}',
                                    [(f'+{n}', f'incorporar:{n}') for n in (1, 3, 5, 10, 20)] +
                                    [('Todos posibles', 'incorporar:max'), ('Cerrar','cerrar')])
            if cantidad == 'max':
                cantidad = min(j.ejercitos_a_colocar,
                              j.desglose_incorporacion()['libres'] +
                              j.refuerzos_continente.get(j.tablero[self.origen]['continente'], 0))
            if cantidad and j.incorporar(self.origen, int(cantidad)):
                self._evento('incorporar', self.origen, texto=f'+{cantidad} ejércitos en {self.origen}')
                self.dialogo = None
                return True
            return self._error('No hay suficientes refuerzos utilizables en ese continente, o está bloqueado.')
        if nombre in ('misil_nuevo', 'misil_convertir'):
            if not self.origen or not j.incorporar_misil(self.origen, reemplazar=nombre=='misil_convertir'):
                return self._error('Se requieren 6 refuerzos o 7 ejércitos en un país propio habilitado.')
            self._evento('incorporar_misil', self.origen, texto=f'Misil incorporado en {self.origen}')
            return True
        if nombre == 'atacar':
            if not self.origen or not self.destino: return self._error('Seleccioná origen propio y destino enemigo.')
            if self.destino in j.condominios:
                defensores = [i for i in j.condominios[self.destino] if i != 0]
                if len(defensores)>1:
                    return self._dialogo('elegir_guarnicion', 'Atacar condominio',
                                        f'Elegí qué guarnición atacar en {self.destino}.',
                                        [(j.jugadores[i].color_nombre, f'atacar_guarnicion:{i}') for i in defensores])
            return self._atacar()
        if nombre == 'lanzar_misil':
            if not self.origen or not self.destino or not j.lanzar_misil(self.destino, desde=self.origen):
                return self._error('Misil inválido. Verificá alcance, situación, guarniciones y pactos.')
            self._evento('misil', self.origen, self.destino,
                         f'Misil desde {self.origen} hacia {self.destino}')
            self.destino = None
            return True
        if nombre == 'reagrupar':
            if not self.origen or not self.destino:
                return self._error('Seleccioná origen y destino propios, limítrofes.')
            maximo = j.ejercitos_de(self.origen, 0) - 1
            recibido = j.reagrupados_recibidos.get((self.origen,0),0) if self.origen in j.condominios else j.reagrupados_recibidos.get(self.origen,0)
            maximo -= recibido
            if maximo <= 0:return self._error('No quedan ejércitos disponibles para reagrupar.')
            return self._dialogo('reagrupe', 'Reagrupar ejércitos',
                                f'{self.origen} → {self.destino}. Máximo {maximo}.',
                                [(str(n), f'reagrupar:{n}') for n in sorted(set([1, min(3,maximo),maximo]))] +
                                [('Cerrar','cerrar')])
        if nombre == 'reagrupar_misil':
            if self.origen and self.destino and j.reagrupar_misil(self.origen, self.destino):
                self._evento('reagrupar_misil', self.origen, self.destino, 'Misil reagrupado.')
                self.cancelar_seleccion()
                return True
            return self._error('No se puede mover el misil entre esos países.')
        if nombre == 'solicitar_tarjeta':
            carta = j.solicitar_tarjeta()
            if not carta:return self._error('No reunís las conquistas requeridas o alcanzaste el límite de 5 cartas.')
            self.aviso = f'Tarjeta: {carta} ({j.figuras_cartas[carta]})'
            return self.ver_tarjetas()
        if nombre == 'canje':
            return self.ver_tarjetas()
        return False

    def _atacar(self, defensor_idx=None):
        j = self.juego
        res = (j.atacar_condominio(self.origen, self.destino, defensor_idx=defensor_idx)
               if defensor_idx is not None else j.atacar(self.origen, self.destino))
        if not res['ok']:
            return self._error('Ataque inválido. Revisá frontera, ejércitos, pactos y situación.')
        self._evento('ataque', self.origen, self.destino,
                     f'{self.origen} → {self.destino}: dados {res["dados_atk"]} / '
                     f'{res["dados_def"]}; bajas {res["bajas_atk"]}/{res["bajas_def"]}', res)
        self.dialogo = None
        if j.conquista_pendiente:
            p = j.conquista_pendiente
            self._dialogo('conquista', 'Ocupar territorio conquistado',
                          f'{p["hacia"]}: elegí cuántos ejércitos trasladar desde {p["desde"]}.',
                          [(str(n),f'ocupar:{n}') for n in range(1,p['max_pasar']+1)], obligatorio=True)
        else:
            self.cancelar_seleccion()
        return True

    def ver_tarjetas(self):
        j = self.juego
        jugador = j.jugadores[0]
        self.seleccion_cartas.clear()
        self.seleccion_continentes.clear()
        return self._dialogo('tarjetas', 'Tarjetas y canjes',
                             f'{len(jugador.tarjetas)}/5 cartas de país · Próximo canje +{j.valor_canje(jugador)}\n'
                             'Elegí tres figuras válidas o usá canje automático.',
                             [('Canje automático', 'canje_auto'),('Cerrar','cerrar')])

    def alternar_carta(self, indice):
        if indice in self.seleccion_cartas:self.seleccion_cartas.remove(indice)
        else:self.seleccion_cartas.add(indice)

    def alternar_continente(self, continente):
        if continente in self.seleccion_continentes:self.seleccion_continentes.remove(continente)
        else:self.seleccion_continentes.add(continente)

    def canjear(self, automatico=False):
        j = self.juego
        v = j.canjear_tarjetas() if automatico else j.canjear_tarjetas(sorted(self.seleccion_cartas), sorted(self.seleccion_continentes))
        if not v:return self._error('Canje no válido o no disponible en esta fase.')
        self.aviso=f'Canje efectuado: +{v} ejércitos.'
        self._evento('canje',texto=self.aviso)
        self.dialogo=None
        return True

    def ver_pactos(self):
        j=self.juego
        vigentes=[j.descripcion_pacto(p) for p in j.pactos_vigentes()]
        vigentes += [f'ZONA #{z["id"]}: {z["pais"]}' for z in j.zonas_internacionales if z['activa']]
        vigentes += [f'ASALTO #{a["id"]}: {a["destino"]} ({a["estado"]})'
                     for a in j.agresiones_pendientes if a['estado'] in ('pendiente','pausada')]
        acciones=[('No agresión mundial', 'proponer:mundial'),
                  ('Rupturas / zonas', 'lista_rupturas'),
                  ('Asaltos pendientes', 'lista_asaltos')]
        if self.origen and self.destino and j.es_propietario(self.origen,0):
            acciones = [(f'No agresión: {nombre}',f'proponer:{tipo}') for nombre,tipo in
                        [('países','pais'),('continente','continente'),('entre continentes','frontera'),('mundial','mundial')]]
            acciones += [('Zona internacional','proponer:zona'),('Agresión conjunta','proponer:agresion')] + acciones[-2:]
        acciones.append(('Cerrar', 'cerrar'))
        return self._dialogo('pactos','Diplomacia y pactos',
                             '\n'.join(vigentes) if vigentes else 'No hay pactos vigentes.\nElegí país propio y destino para negociar.', acciones)

    def _proponer(self, tipo, socio=None):
        j=self.juego
        a=0
        if tipo=='mundial' and socio is None:
            return self._dialogo('elegir_socio','No agresión mundial','Elegí un jugador bot para negociar.',
                   [(j.jugadores[i].color_nombre,f'socio_mundial:{i}') for i in range(1,j.n_jugadores) if not j.jugadores[i].eliminado])
        if tipo!='mundial' and (not self.origen or not self.destino or not j.es_propietario(self.origen,a)):
            return self._error('Elegí un país propio y un destino para hacer la propuesta.')
        if socio is None:
            socio = j.tablero[self.destino]['propietario']
        if socio is None or socio==0:
            return self._error('El país de destino debe ser de un bot, no un condominio.')
        if tipo == 'agresion':
            candidatos=[]
            for p in j.tablero[self.destino]['fronteras']:
                i=j.tablero[p]['propietario']
                if i is not None and i not in (a,socio) and j.ejercitos_de(p,i)>=2 and j.jugadores[i].es_bot:
                    candidatos.append((i,p))
            if self.origen in j.condominios:
                for i in j.condominios[self.origen]:
                    if i not in (a,socio) and j.ejercitos_de(self.origen,i)>=2 and j.jugadores[i].es_bot:
                        candidatos.insert(0,(i,self.origen))
            if not candidatos:return self._error('No hay aliado con 2 ejércitos adyacente al objetivo.')
            return self._dialogo('agresion', 'Agresión conjunta',
                                 'Elegí socio y país desde el cual participará.',
                                 [(f'{j.jugadores[i].color_nombre}: {p}',f'aliado:{i}:{p}') for i,p in candidatos[:10]])
        if not j.bot_acepta_pacto(socio,tipo,a,self.destino):
            return self._error('El bot rechazó la propuesta.')
        if tipo=='zona':
            resultado=j.proponer_zona_internacional(a,socio,self.destino)
        else:
            params={}
            if tipo=='pais':params['paises']=(self.origen,self.destino)
            if tipo=='continente':params['continente']=j.tablero[self.origen]['continente']
            if tipo=='frontera':params['continentes']=(j.tablero[self.origen]['continente'],j.tablero[self.destino]['continente'])
            resultado=j.proponer_no_agresion(a,socio,tipo,**params)
        if not resultado:return self._error('No se cumplen las condiciones reglamentarias del pacto.')
        self.aviso='Pacto firmado y registrado.'
        return self.ver_pactos()

    def procesar_opcion(self, codigo):
        j=self.juego
        if codigo=='cerrar':return self.cerrar_dialogo()
        if codigo=='situacion_ok':
            self.dialogo=None;return True
        if codigo.startswith('incorporar:'):return self.accion('incorporar', codigo.split(':',1)[1])
        if codigo.startswith('ocupar:'):
            if not j.resolver_conquista(int(codigo.split(':',1)[1])):return False
            self.cancelar_seleccion();self.dialogo=None;return True
        if codigo.startswith('atacar_guarnicion:'):
            return self._atacar(int(codigo.rsplit(':',1)[1]))
        if codigo.startswith('reagrupar:'):
            n=int(codigo.split(':',1)[1]);desde,hacia=self.origen,self.destino
            if not j.reagrupar(desde,hacia,n):return self._error('No se puede reagrupar esa cantidad.')
            self._evento('reagrupar',desde,hacia,f'{n} ejércitos: {desde} → {hacia}')
            self.dialogo=None;self.cancelar_seleccion();return True
        if codigo=='canje_auto':return self.canjear(automatico=True)
        if codigo=='canje_manual':return self.canjear(automatico=False)
        if codigo.startswith('proponer:'):return self._proponer(codigo.split(':',1)[1])
        if codigo.startswith('socio_mundial:'):return self._proponer('mundial',int(codigo.rsplit(':',1)[1]))
        if codigo.startswith('aliado:'):
            _,i,p=codigo.split(':',2)
            self._agresion_socio=int(i);self._agresion_origen=p
            return self._dialogo('elegir_lider','Momento del ataque conjunto',
                 f'Objetivo: {self.destino}. ¿En qué turno ejecutar?',
                 [('Mi turno','lider:0'),(f'Turno de {j.jugadores[int(i)].color_nombre}',f'lider:{i}')])
        if codigo.startswith('lider:'):
            b=self._agresion_socio;lider=int(codigo.rsplit(':',1)[1])
            if not j.bot_acepta_pacto(b,'agresion',0,self.destino):return self._error('El bot rechazó el ataque conjunto.')
            ag=j.proponer_agresion_conjunta(0,b,self.origen,self._agresion_origen,self.destino,lider=lider)
            if not ag:return self._error('No se reúnen los requisitos de agresión conjunta.')
            if j.fase==FASE_ATACAR and j.turno_idx==lider and ag['ronda']<=j.ronda:
                r=j.ejecutar_agresion_conjunta(ag['id'])
                self._evento('ataque',self.origen,self.destino,r['resultado'] if r else 'Agresión pactada')
            else:self.aviso=f'Agresión conjunta #{ag["id"]} programada para ronda {ag["ronda"]}.'
            return self.ver_pactos()
        if codigo=='lista_rupturas':
            opciones=[(f'Romper #{p["id"]}',f'romper:{p["id"]}') for p in j.pactos_vigentes()
                      if 0 in p['jugadores'] and p['ruptura_por'] is None]
            opciones += [(f'Cancelar zona #{z["id"]}',f'cancelar_zona:{z["id"]}')
                        for z in j.zonas_internacionales if z['activa'] and 0 in z['jugadores']]
            return self._dialogo('rupturas','Pactos y zonas rescindibles',
                                  'Los pactos no desaparecen hasta cumplir los plazos reglamentarios.',
                                  opciones+[('Volver','volver_pactos')])
        if codigo=='lista_asaltos':
            opciones=[]
            for ag in j.agresiones_pendientes:
                if ag['estado']=='pausada' and 0 in ag['jugadores']:
                    opciones.extend([(f'Continuar #{ag["id"]}',f'seguir_asalto:{ag["id"]}'),
                                    (f'Detener #{ag["id"]}',f'detener_asalto:{ag["id"]}')])
            return self._dialogo('asaltos','Agresiones conjuntas','Asaltos pendientes o pausados.',
                                  opciones+[('Volver','volver_pactos')])
        if codigo=='volver_pactos':return self.ver_pactos()
        if codigo.startswith('romper:'):
            res=j.romper_pacto(int(codigo.split(':')[1]),0)
            if not res:return self._error('No se puede romper ese pacto.')
            return self.ver_pactos()
        if codigo.startswith('cancelar_zona:'):
            j.cancelar_zona_internacional(int(codigo.split(':')[1]),0)
            return self.ver_pactos()
        if codigo.startswith('seguir_asalto:'):
            agid=int(codigo.split(':')[1]);res=j.ejecutar_agresion_conjunta(agid)
            self.aviso=res['resultado'] if res else 'Sólo puede ejecutarse en el turno del líder.'
            return self.ver_pactos()
        if codigo.startswith('detener_asalto:'):
            j.cancelar_agresion_voluntaria(int(codigo.split(':')[1]),0)
            return self.ver_pactos()
        if codigo.startswith('responder_bot:'):
            acepta=codigo.rsplit(':',1)[1]=='si'
            resultado=j.aceptar_propuesta_bot(acepta)
            titulo,texto=respuesta_propuesta_bot(resultado,acepta)
            self.dialogo=None
            self._dialogo('info',titulo,texto,[('Entendido','cerrar')])
            return True
        if codigo=='aliado_no':
            j.resolver_reagrupe_aliado();self.dialogo=None;return True
        if codigo.startswith('aliado_desde:'):
            pais=codigo.split(':',1)[1]
            self._reagrupe_origen=pais
            maximo=j.ejercitos_de(pais,0)-1
            if maximo<1:return self._error('No hay ejércitos para mover.')
            return self._dialogo('reagrupe_aliado','Reagrupe especial',
                                 f'Desde {pais}, hasta {maximo} ejércitos.',
                                 [(str(n),f'aliado_mover:{n}') for n in sorted(set([1,min(3,maximo),maximo]))]+
                                 [('No mover','aliado_no')],True)
        if codigo.startswith('aliado_mover:'):
            cant=int(codigo.split(':')[1])
            ok=j.resolver_reagrupe_aliado(self._reagrupe_origen,cant)
            if not ok:return self._error('No fue posible el reagrupe especial.')
            self.dialogo=None;return True
        if codigo.startswith('zona_decidir:'):
            _,num,decision=codigo.split(':')
            j.decidir_zona_incumplida(int(num),0,decision=='mantener')
            self.dialogo=None;return True
        return False

    def tick(self):
        """Procesa un paso de juego. Invocar desde Clock, nunca bloquear UI."""
        j=self.juego
        if j.fase=='VICTORIA':
            if not self.victoria_mostrada:
                self.victoria_mostrada = True
                ganador=j.jugadores[j.ganador_idx].nombre
                self._dialogo('victoria','¡VICTORIA!',f'{ganador} ganó la partida.',
                              [('Ver tablero','cerrar')])
            return None
        if j.etapa=='hostilidades' and j.ronda>=2 and j.ronda>self.situacion_anunciada:
            if self.dialogo is None:
                self.situacion_anunciada=j.ronda
                self._dialogo('situacion','Situación de la ronda',
                              f'Ronda {j.ronda}: {j.situacion}.\nAplicación obligatoria para todos los jugadores.',
                              [('Aceptar','situacion_ok')], True)
            return None
        if j.reagrupe_aliado_pendiente is not None and self.dialogo is None:
            ag=next((x for x in j.agresiones_pendientes if x['id']==j.reagrupe_aliado_pendiente),None)
            if ag:
                paises=[p for p in j.tablero[ag['destino']]['fronteras']
                        if j.es_propietario(p,0) and j.ejercitos_de(p,0)>=2]
                self._dialogo('reagrupe_aliado','Reagrupe extra del aliado',
                              f'Conquistaron {ag["destino"]}. Podés sumar ejércitos al condominio.',
                              [(f'Desde {p}',f'aliado_desde:{p}') for p in paises[:10]]+
                              [('No mover','aliado_no')],True)
                return None
        if self.dialogo is None:
            for z in j.zonas_internacionales:
                if z['activa'] and z.get('decision_pendiente')==0:
                    self._dialogo('zona_pendiente','Incumplimiento de zona',
                                  f'{z["pais"]} no fue conquistado conforme al pacto. ¿Mantenés la zona?',
                                  [('Mantener',f'zona_decidir:{z["id"]}:mantener'),
                                   ('Cancelar',f'zona_decidir:{z["id"]}:cancelar')],True)
                    return None
        if self.dialogo is None and j.propuesta_pendiente:
            pp=j.propuesta_pendiente
            texto=(f'Propuesta de {j.jugadores[pp["a"]].color_nombre}: '
                   + (f'ataque conjunto a {pp["destino"]} desde {pp["origen_a"]} y {pp["origen_b"]}'
                      if pp['tipo']=='agresion' else f'no agresión entre {pp["paises"][0]} y {pp["paises"][1]}'))
            self._dialogo('propuesta_bot','Propuesta de pacto',texto,
                          [('Aceptar','responder_bot:si'),('Rechazar','responder_bot:no')],True)
            return None
        if self.dialogo is not None:return None
        if j.fase==FASE_ATACAR and not j.conquista_pendiente:
            ag=next((a for a in j.agresiones_pendientes if a['estado']=='pendiente' and
                     a['lider']==j.turno_idx and a['ronda']<=j.ronda),None)
            if ag:
                res=j.ejecutar_agresion_conjunta(ag['id'])
                if res:
                    self._evento('ataque',texto=f'Asalto #{ag["id"]}: {res["resultado"]}')
                    self._dialogo('info','Ataque conjunto',self.aviso,[('Aceptar','cerrar')])
                return res
        if not j.jugador_actual().es_bot or self.VELOCIDADES[self.velocidad] is None:
            return None
        paso=j.paso_bot()
        if paso:
            texto=paso.get('texto','Acción del bot')
            self.aviso=texto
            if paso.get('pais'):
                tipo=paso.get('accion','ataque')
                self._evento(tipo,paso['pais'],paso.get('destino'),texto,paso.get('dados'))
            elif paso.get('accion')=='canje':
                self._evento('canje',texto=texto)
        return paso

    def resumen(self):
        j=self.juego
        jugador=j.jugador_actual()
        ref=j.desglose_incorporacion() if j.fase==FASE_INCORPORAR else None
        return dict(ronda=j.ronda,fase=j.fase,etapa=j.etapa, etapa_ronda=j.etapa_ronda,
                    turno=jugador.nombre, color=jugador.color_nombre, bot=jugador.es_bot,
                    situacion=j.situacion,refuerzos=ref, origen=self.origen,
                    destino=self.destino,inspeccion=self.inspeccion,anuncio=self.aviso,
                    jugadores=[(p.nombre,len(j.paises_de(p.idx)),p.eliminado) for p in j.jugadores])
