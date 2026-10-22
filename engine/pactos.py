"""Pactos públicos y vinculantes de TEG La Revancha (reglamento págs. 27–34).

El motor usa identificadores de jugador (no colores de pantalla) para la diplomacia.
El tablero conserva países exclusivos y agrega guarniciones compartidas únicamente
cuando se conquista por agresión conjunta o se irrumpe en un condominio.
"""
import random
from collections import deque


class DiplomaciaMixin:
    TIPOS_PACTO = {'pais', 'continente', 'frontera', 'mundial', 'condominio'}

    def _iniciar_diplomacia(self):
        self.pactos = []
        self.zonas_internacionales = []
        self.agresiones_pendientes = []
        self.condominios = {}  # nombre -> {jugador: ejercitos, jugador: ejercitos}
        self.turnos_terminados = [0] * self.n_jugadores
        self.sancion_tarjeta = [0] * self.n_jugadores
        self._proximo_pacto_id = 1
        self._ataque_conjunto_en_curso = False
        self.conquistas_colectivas = 0
        self._ultimo_evento_pactos = ''

    def ejercitos_de(self, pais, idx):
        if pais not in self.tablero:
            return 0
        if pais in self.condominios:
            return self.condominios[pais].get(idx, 0)
        return self.tablero[pais]['ejercitos'] if self.tablero[pais]['propietario'] == idx else 0

    def es_propietario(self, pais, idx):
        return self.ejercitos_de(pais, idx) > 0

    def _sincronizar_condominio(self, pais):
        tropas = {idx: n for idx, n in self.condominios[pais].items() if n > 0}
        if len(tropas) <= 1:
            self.condominios.pop(pais)
            dueño, cantidad = next(iter(tropas.items())) if tropas else (None, 0)
            self.tablero[pais]['propietario'] = dueño
            self.tablero[pais]['ejercitos'] = cantidad
        else:
            self.condominios[pais] = tropas
            self.tablero[pais]['propietario'] = None
            self.tablero[pais]['ejercitos'] = sum(tropas.values())
        # Cambiar un país a condominio puede romper el control de un continente.
        self._revocar_tarjetas_continente_por_perdida(self.tablero[pais]['continente'])

    def _ajustar_guarnicion(self, pais, jugador_idx, delta):
        if pais in self.condominios:
            self.condominios[pais][jugador_idx] = self.condominios[pais].get(jugador_idx, 0) + delta
            if self.condominios[pais][jugador_idx] < 0:
                raise ValueError('Guarnición negativa')
            self._sincronizar_condominio(pais)
        else:
            if self.tablero[pais]['propietario'] != jugador_idx:
                raise ValueError('Ejércitos ajenos')
            self.tablero[pais]['ejercitos'] += delta

    def _nuevo_pacto(self, tipo, a, b, **detalles):
        pacto = dict(id=self._proximo_pacto_id, tipo=tipo, jugadores=tuple(sorted((a, b))),
                     activo=True, ruptura_por=None, turno_liberacion=None, **detalles)
        self._proximo_pacto_id += 1
        self.pactos.append(pacto)
        self.log(f'PACTO PÚBLICO #{pacto["id"]} {tipo}: {self.jugadores[a].color_nombre} y {self.jugadores[b].color_nombre}')
        return pacto

    def pactos_vigentes(self):
        return [p for p in self.pactos if p['activo']]

    def descripcion_pacto(self, pacto):
        """Describe sólo los campos que corresponden al tipo de pacto.

        No se deben evaluar todas las variantes en un literal de diccionario:
        eso accede a ``pacto['paises']`` incluso cuando el pacto es mundial.
        """
        jugadores = ' / '.join(self.jugadores[i].color_nombre
                              for i in pacto.get('jugadores', ()))
        tipo = pacto.get('tipo', '')
        if tipo == 'pais':
            ref = 'Países: ' + ', '.join(pacto.get('paises') or ())
        elif tipo == 'continente':
            ref = pacto.get('continente') or ''
        elif tipo == 'frontera':
            ref = ' / '.join(pacto.get('continentes') or ())
        elif tipo == 'mundial':
            ref = 'Todo el mundo'
        elif tipo == 'condominio':
            ref = pacto.get('pais') or ''
        else:
            ref = ''
        fin = ' · RUPTURA PENDIENTE' if pacto.get('ruptura_por') is not None else ''
        return f'#{pacto.get("id", "?")} {tipo.upper()} · {jugadores} · {ref}{fin}'

    def _tienen_pacto_equivalente(self, tipo, a, b, detalle):
        for p in self.pactos_vigentes():
            if p['tipo'] == tipo and set(p['jugadores']) == {a,b} and p.get(detalle[0]) == detalle[1]:
                return True
        return False

    def proponer_no_agresion(self, a, b, tipo, paises=None, continente=None, continentes=None):
        """Acuerdo bilateral. La aceptación del bot se realiza en la capa de interfaz.

        Los humanos sólo firman tras confirmar el diálogo. No se admiten pactos
        ofensivo-defensivos ni cláusulas que no estén en la edición aportada.
        """
        if (tipo not in {'pais','continente','frontera','mundial'} or a == b or
            not (0 <= a < self.n_jugadores and 0 <= b < self.n_jugadores) or
            self.jugadores[a].eliminado or self.jugadores[b].eliminado):
            return None
        params={}
        if tipo == 'pais':
            if not paises or len(paises)!=2:return None
            x,y=paises
            if (x==y or not self.es_propietario(x,a) or not self.es_propietario(y,b)
                or self.distancia(x,y) is None):return None
            params['paises']=(x,y)
            key=('paises', tuple(sorted((x,y))))
        elif tipo == 'continente':
            if continente not in self.CONTINENTES_DIPLO or not any(
                self.es_propietario(p,a) for p,d in self.tablero.items() if d['continente']==continente
            ) or not any(self.es_propietario(p,b) for p,d in self.tablero.items() if d['continente']==continente):return None
            params['continente']=continente;key=('continente',continente)
        elif tipo == 'frontera':
            if not continentes or len(continentes)!=2:return None
            c1,c2=continentes
            if c1==c2 or c1 not in self.CONTINENTES_DIPLO or c2 not in self.CONTINENTES_DIPLO:return None
            # Es necesario que exista al menos una frontera efectiva entre los dos
            # continentes con territorio de cada firmante.
            existe=any(self.es_propietario(p,a) and d['continente']==c1 and
                any(self.es_propietario(q,b) and self.tablero[q]['continente']==c2 for q in d['fronteras'])
                for p,d in self.tablero.items())
            existe |= any(self.es_propietario(p,b) and d['continente']==c1 and
                any(self.es_propietario(q,a) and self.tablero[q]['continente']==c2 for q in d['fronteras'])
                for p,d in self.tablero.items())
            if not existe:return None
            params['continentes']=tuple(sorted((c1,c2)));key=('continentes',params['continentes'])
        else:key=('tipo','mundial')
        if self._tienen_pacto_equivalente(tipo,a,b,key):return None
        return self._nuevo_pacto(tipo,a,b,**params)

    @property
    def CONTINENTES_DIPLO(self):
        return {d['continente'] for d in self.tablero.values()}

    def _pacto_cubre(self, pacto, desde, hacia):
        if not pacto['activo'] or pacto['tipo']=='condominio':return False
        if pacto['tipo']=='mundial':return True
        if pacto['tipo']=='pais':return {desde,hacia}==set(pacto['paises'])
        if pacto['tipo']=='continente':
            return self.tablero[desde]['continente']==self.tablero[hacia]['continente']==pacto['continente']
        if pacto['tipo']=='frontera':
            return {self.tablero[desde]['continente'],self.tablero[hacia]['continente']}==set(pacto['continentes'])
        return False

    def _prohibido_por_pacto(self, actor, defensor, desde, hacia):
        if actor == defensor:return False
        return any(set(p['jugadores'])=={actor,defensor} and self._pacto_cubre(p,desde,hacia)
                   for p in self.pactos_vigentes())

    def romper_pacto(self, pacto_id, por_idx):
        p=next((p for p in self.pactos_vigentes() if p['id']==pacto_id),None)
        if not p or por_idx not in p['jugadores'] or p['ruptura_por'] is not None:return False
        otro=next(i for i in p['jugadores'] if i!=por_idx)
        p['ruptura_por']=por_idx
        # No deja de regir hasta FINALIZAR el próximo turno del otro jugador;
        # incluye el siguiente turno cuando el actual ya ocurrió.
        p['turno_liberacion']=(otro,self.turnos_terminados[otro]+1)
        self.log(f'RUPTURA ANUNCIADA #{pacto_id} por {self.jugadores[por_idx].color_nombre}: vigente hasta fin del próximo turno de {self.jugadores[otro].color_nombre}')
        return True

    def _cierre_turno_diplomatico(self, jugador_idx):
        self.turnos_terminados[jugador_idx]+=1
        for p in self.pactos_vigentes():
            if p['turno_liberacion'] and p['turno_liberacion'][0]==jugador_idx and self.turnos_terminados[jugador_idx]>=p['turno_liberacion'][1]:
                p['activo']=False
                self.log(f'PACTO #{p["id"]} finalizado tras el turno de {self.jugadores[jugador_idx].color_nombre}')
        for z in self.zonas_internacionales:
            if not z['activa'] or jugador_idx not in z['jugadores']:continue
            if z['pendiente']==jugador_idx:
                self._penalizar_zona(z,jugador_idx)

    def _cambio_control_diplomatico(self, pais, viejo, nuevo):
        if viejo == nuevo:return
        for p in self.pactos_vigentes():
            if p['tipo']=='pais' and pais in p['paises']:
                duenos=[next((idx for idx in p['jugadores'] if self.es_propietario(nombre,idx)),None) for nombre in p['paises']]
                if set(duenos)!=set(p['jugadores']):
                    p['activo']=False;self.log(f'PACTO #{p["id"]} roto por ocupación de {pais}')
            if p.get('condominio_origen')==pais and not set(p['jugadores']).issubset(self.condominios.get(pais,{})):
                p['activo']=False
            if p['tipo']=='condominio' and p['pais']==pais and not set(p['jugadores']).issubset(self.condominios.get(pais,{})):
                p['activo']=False
        for z in self.zonas_internacionales:
            if not z['activa'] or z['pais']!=pais:continue
            if nuevo not in z['jugadores']:
                z['activa']=False;self.log(f'ZONA INTERNACIONAL {pais} terminada por un tercero')
            elif z['pendiente']==nuevo:
                z['pendiente']=next(i for i in z['jugadores'] if i!=nuevo)
                z['cumplimientos']+=1
                self.log(f'ZONA INTERNACIONAL {pais}: cumplió {self.jugadores[nuevo].color_nombre}')

    def distancia_misil_legal(self, origen, destino, actor):
        """Distancia de ruta legal sin sobrevolar una frontera cubierta por pacto.

        Un misil no puede utilizar territorios del socio para sortear un pacto.
        Ante rutas alternativas, se usa la más corta que no infringe acuerdos.
        """
        q=deque([(origen, [origen])])
        while q:
            pais,ruta=q.popleft()
            if pais==destino:return len(ruta)-1
            if len(ruta)>3:continue
            for vecino in self.tablero[pais]['fronteras']:
                if vecino in ruta:continue
                bloqueada=False
                for pacto in self.pactos_vigentes():
                    if actor not in pacto['jugadores'] or pacto['tipo']=='condominio':continue
                    otro=next(i for i in pacto['jugadores'] if i!=actor)
                    if self._pacto_cubre(pacto,pais,vecino) and (
                            self.es_propietario(pais,actor) and self.es_propietario(vecino,otro)
                            or self.es_propietario(vecino,actor) and self.es_propietario(pais,otro)):
                        bloqueada=True;break
                    if pacto['tipo']=='pais' and origen in pacto['paises'] and vecino==next((x for x in pacto['paises'] if x!=origen),None):
                        bloqueada=True;break
                if not bloqueada:q.append((vecino,ruta+[vecino]))
        return None

    def proponer_zona_internacional(self,a,b,pais):
        if a==b or self.jugadores[a].canjes_realizados<3 or self.jugadores[b].canjes_realizados<3:
            return None
        if any(z['activa'] and (a in z['jugadores'] or b in z['jugadores']) for z in self.zonas_internacionales):return None
        if pais not in self.tablero or self.tablero[pais]['ejercitos']!=1 or pais in self.condominios:return None
        actual=self.tablero[pais]['propietario']
        if actual not in (a,b):return None
        if not all(any(self.es_propietario(p,idx) for p in self.tablero[pais]['fronteras']) for idx in (a,b)):
            return None
        z={'id':self._proximo_pacto_id,'pais':pais,'jugadores':tuple(sorted((a,b))),
           'activa':True,'pendiente':b if actual==a else a, 'cumplimientos':0}
        self._proximo_pacto_id+=1
        self.zonas_internacionales.append(z)
        self.log(f'ZONA INTERNACIONAL #{z["id"]}: {pais}; un ejército y conquista alternada obligatoria')
        return z

    def _penalizar_zona(self,z,actor):
        j=self.jugadores[actor]
        if j.tarjetas:
            carta=random.choice(j.tarjetas);j.tarjetas.remove(carta)
            self.descarte_cartas.append(carta)
            self.log(f'PENALIZACIÓN ZONA {z["pais"]}: {j.nombre} devuelve {carta}')
        else:
            self.sancion_tarjeta[actor]+=1
            self.log(f'PENALIZACIÓN ZONA {z["pais"]}: {j.nombre} pierde próximo derecho a tarjeta')
        z['pendiente']=actor  # Si la zona se conserva, sigue siendo su obligación.
        z['incumplio']=actor
        perjudicado=next(i for i in z['jugadores'] if i!=actor)
        # El jugador perjudicado conserva el derecho de decidir la continuidad.
        if self.jugadores[perjudicado].es_bot:
            if random.random()<.3:
                z['activa']=False
                self.log(f'ZONA INTERNACIONAL {z["pais"]} cancelada por el perjudicado')
        else:
            z['decision_pendiente']=perjudicado

    def cancelar_zona_internacional(self,zona_id,idx):
        z=next((z for z in self.zonas_internacionales if z['id']==zona_id and z['activa']),None)
        if not z or idx not in z['jugadores']:return False
        z['activa']=False
        self.log(f'ZONA INTERNACIONAL {z["pais"]} cancelada por {self.jugadores[idx].nombre}')
        return True

    def decidir_zona_incumplida(self,zona_id,perjudicado,mantener):
        z=next((z for z in self.zonas_internacionales if z['id']==zona_id and z['activa']),None)
        if not z or z.get('decision_pendiente')!=perjudicado:return False
        z.pop('decision_pendiente',None)
        if not mantener:
            z['activa']=False
        self.log(f'ZONA {z["pais"]}: el perjudicado {"la mantiene" if mantener else "la cancela"}')
        return True

    def zona_para(self,pais):
        return next((z for z in self.zonas_internacionales if z['activa'] and z['pais']==pais),None)

    def proponer_agresion_conjunta(self,a,b,origen_a,origen_b,destino,lider=None):
        """Pacto público para ejecutar en el próximo turno de ataque del líder.

        Dos aliados pueden atacar desde países diferentes, o desde la misma
        guarnición compartida, caso en que el ataque es voluntario.
        """
        lider=a if lider is None else lider
        if (a==b or lider not in (a,b) or self.etapa!='hostilidades' or
            self.fase=='VICTORIA' or self.conquista_pendiente or
            any(self.jugadores[i].eliminado for i in (a,b))):return None
        if destino not in self.tablero or destino in self.condominios or self.tablero[destino]['propietario'] in (a,b):return None
        if not (self.es_propietario(origen_a,a) and self.es_propietario(origen_b,b)):return None
        if min(self.ejercitos_de(origen_a,a),self.ejercitos_de(origen_b,b))<2:return None
        fuente_compartida=origen_a==origen_b
        if fuente_compartida and origen_a not in self.condominios:return None
        if not self.son_adyacentes(origen_a,destino) or not self.son_adyacentes(origen_b,destino):return None
        if self._prohibido_por_pacto(a,self.tablero[destino]['propietario'],origen_a,destino):return None
        if self._prohibido_por_pacto(b,self.tablero[destino]['propietario'],origen_b,destino):return None
        ronda_destino=self.ronda
        if self.etapa_ronda=='ATAQUE':
            # Si el líder ya terminó su turno de ataque en esta ronda,
            # el compromiso se ejecuta en la siguiente.
            orden=[i for i in self.orden_ronda if not self.jugadores[i].eliminado]
            if orden.index(lider)<orden.index(self.turno_idx) or (
                lider==self.turno_idx and self.fase not in ('ATACAR',)):
                ronda_destino+=1
        ag={'id':self._proximo_pacto_id, 'jugadores':(a,b),'lider':lider,
            'origenes':{a:origen_a,b:origen_b},'destino':destino,'estado':'pendiente',
            'resultado':None,'tiradas':0,'ronda':ronda_destino,'reagrupe_resuelto':False,
            'forzoso':not fuente_compartida}
        self._proximo_pacto_id+=1
        self.agresiones_pendientes.append(ag)
        self.log(f'PACTO DE AGRESIÓN #{ag["id"]}: {self.jugadores[a].nombre} + '
                 f'{self.jugadores[b].nombre} contra {destino}; turno líder {self.jugadores[lider].nombre}')
        return ag

    def ejecutar_agresion_conjunta(self,agresion_id):
        ag=next((x for x in self.agresiones_pendientes if x['id']==agresion_id and
                 x['estado'] in ('pendiente','pausada')),None)
        if not ag or self.turno_idx!=ag['lider'] or self.fase!='ATACAR' or self.ronda<ag['ronda']:
            return None
        a,b=ag['jugadores'];destino=ag['destino'];lider=ag['lider']
        aliado=b if lider==a else a
        defensor=self.tablero[destino]['propietario']
        if (defensor in (a,b) or defensor is None or destino in self.condominios or
            any(self.ejercitos_de(ag['origenes'][i],i)<2 for i in (a,b)) or
            any(not self._ataque_permitido(ag['origenes'][i],destino,actor_idx=i) for i in (a,b)) or
            any(self.situacion==f'Descanso {self.jugadores[i].color_nombre}' for i in (a,b))):
            ag['estado']='fallida';ag['resultado']='Condiciones de ataque ya no válidas'
            return ag
        ag['ronda']=self.ronda
        ag['estado']='en_curso'
        self._ataque_conjunto_en_curso=True
        tiradas_inicio=ag['tiradas']
        try:
            while self.tablero[destino]['propietario']==defensor:
                pudieron=False
                for atacante in (lider,aliado):
                    if any(self.ejercitos_de(ag['origenes'][i],i)<2 for i in (a,b)):
                        break
                    origen=ag['origenes'][atacante]
                    pudieron=True
                    res=self.atacar(origen,destino,actor_idx=atacante,conjunto=True)
                    if not res['ok']:
                        ag['estado']='fallida';ag['resultado']='Ataque inválido';return ag
                    ag['tiradas']+=1
                    if res['conquisto']:
                        ag['estado']='conquistada';ag['resultado']='Condominio establecido'
                        self._nuevo_pacto('condominio',a,b,pais=destino)
                        if ag['origenes'][a]!=ag['origenes'][b]:
                            p=self._nuevo_pacto('pais',a,b,paises=(ag['origenes'][a],ag['origenes'][b]),
                                                condominio_origen=destino)
                            falta_aliado=(self.orden_ronda.index(aliado)>self.orden_ronda.index(lider))
                            p['turno_liberacion']=(aliado,self.turnos_terminados[aliado]+(2 if falta_aliado else 1))
                        self.log(f'CONDOMINIO {destino}: {self.condominios[destino]}')
                        return ag
                if not pudieron:break
                if not ag['forzoso'] and ag['tiradas']-tiradas_inicio>=2:
                    ag['estado']='pausada';ag['resultado']='Asalto voluntario pausado: se puede continuar o cancelar'
                    return ag
            ag['estado']='fallida';ag['resultado']='No quedan ejércitos suficientes para ocupar el condominio'
            return ag
        finally:
            self._ataque_conjunto_en_curso=False

    def cancelar_agresion_voluntaria(self,agresion_id,idx):
        ag=next((ag for ag in self.agresiones_pendientes if ag['id']==agresion_id and
                 ag['estado']=='pausada' and not ag['forzoso'] and idx in ag['jugadores']),None)
        if not ag:return False
        ag['estado']='cancelada';self.log(f'ASALTO VOLUNTARIO #{ag["id"]} cancelado')
        return True

    def conquistar_en_condominio(self,desde,destino,actor,aliado):
        """Al ganar asalto conjunto pasan 1–2 ejércitos desde cada origen."""
        ag=next(a for a in self.agresiones_pendientes if a['estado']=='en_curso' and a['destino']==destino)
        p1=ag['origenes'][actor];p2=ag['origenes'][aliado]
        n1=min(2,self.ejercitos_de(p1,actor)-1)
        n2=min(2,self.ejercitos_de(p2,aliado)-1)
        if min(n1,n2)<1:raise AssertionError('Condominio sin un ejército por socio')
        self._ajustar_guarnicion(p1,actor,-n1)
        self._ajustar_guarnicion(p2,aliado,-n2)
        self.condominios[destino]={actor:n1,aliado:n2}
        self._sincronizar_condominio(destino)
        self.conquistas_colectivas+=1
        for idx in (actor,aliado):
            self.conquistas_compartidas_por_jugador[idx]+=1
        self.log(f'OCUPACIÓN COMPARTIDA {destino}: {n1} de {self.jugadores[actor].color_nombre} + {n2} de {self.jugadores[aliado].color_nombre}')

    def reagrupar_en_condominio(self,desde,destino,cantidad,actor_idx=None):
        actor=self.turno_idx if actor_idx is None else actor_idx
        if (self.fase!='REAGRUPAR' or destino not in self.condominios or
            actor not in self.condominios[destino] or cantidad<1 or
            not self.son_adyacentes(desde,destino) or
            not self.es_propietario(desde,actor) or
            self.ejercitos_de(desde,actor)-1-self.reagrupados_recibidos.get((desde,actor),0)<cantidad):return False
        if actor!=self.turno_idx:
            # Única excepción: el aliado que participó en la conquista de ese
            # condominio, después de reagrupar el líder y antes del próximo turno.
            if not any(a['estado']=='conquistada' and a['destino']==destino and
                actor in a['jugadores'] and self.turno_idx==a['lider'] and self.ronda==a['ronda']
                for a in self.agresiones_pendientes):return False
        self._ajustar_guarnicion(desde,actor,-cantidad)
        self._ajustar_guarnicion(destino,actor,cantidad)
        self.reagrupados_recibidos[(destino,actor)]=self.reagrupados_recibidos.get((destino,actor),0)+cantidad
        self.log(f'REAGRUPA EN CONDOMINIO {actor}: {desde} -> {destino} (+{cantidad})')
        return True

    def preparar_reagrupe_aliado(self):
        """Antes de tarjetas: único reagrupamiento fuera de turno del socio."""
        for ag in self.agresiones_pendientes:
            if (ag['estado']!='conquistada' or ag['reagrupe_resuelto'] or
                ag['ronda']!=self.ronda or ag['lider']!=self.turno_idx or
                ag['destino'] not in self.condominios):continue
            aliado=next(i for i in ag['jugadores'] if i!=ag['lider'])
            if self.jugadores[aliado].es_bot:
                vecinos=[p for p in self.tablero[ag['destino']]['fronteras']
                         if self.es_propietario(p,aliado) and self.ejercitos_de(p,aliado)>=2]
                if vecinos:
                    origen=max(vecinos,key=lambda p:self.ejercitos_de(p,aliado))
                    cantidad=min(3,self.ejercitos_de(origen,aliado)-1)
                    self.reagrupar_en_condominio(origen,ag['destino'],cantidad,actor_idx=aliado)
                ag['reagrupe_resuelto']=True
            else:
                self.reagrupe_aliado_pendiente=ag['id']
                return False
        return True

    def resolver_reagrupe_aliado(self,origen=None,cantidad=0):
        idp=self.reagrupe_aliado_pendiente
        if idp is None:return False
        ag=next((ag for ag in self.agresiones_pendientes if ag['id']==idp),None)
        if not ag:return False
        aliado=next(i for i in ag['jugadores'] if i!=ag['lider'])
        if cantidad>0 and not self.reagrupar_en_condominio(origen,ag['destino'],cantidad,actor_idx=aliado):
            return False
        ag['reagrupe_resuelto']=True
        self.reagrupe_aliado_pendiente=None
        return True

    def atacar_condominio(self,desde,pais,defensor_idx=None,actor_idx=None):
        """Ataque contra guarnición elegida, incluso desde el propio condominio."""
        actor=self.turno_idx if actor_idx is None else actor_idx
        res={'ok':False,'dados_atk':[],'dados_def':[],'bajas_atk':0,'bajas_def':0,'conquisto':False}
        if (self.fase!='ATACAR' or self.conquista_pendiente or pais not in self.condominios
            or self.situacion==f'Descanso {self.jugadores[actor].color_nombre}'
            or not self.es_propietario(desde,actor)):
            return res
        posibles=[i for i in self.condominios[pais] if i!=actor]
        if not posibles:return res
        if defensor_idx is None:defensor_idx=max(posibles,key=lambda i:self.ejercitos_de(pais,i))
        if defensor_idx not in posibles:return res
        interior=desde==pais
        if not interior and not self._ataque_permitido(desde,pais):return res
        if self._prohibido_por_pacto(actor,defensor_idx,desde,pais):return res
        dueños_actuales=set(self.condominios[pais])
        # Para los firmantes ORIGINALES, después de la ruptura, la disputa por
        # el mismo condominio se resuelve exclusivamente dentro de él.
        if not interior and actor in dueños_actuales and any(
            p['tipo']=='condominio' and p['pais']==pais and set(p['jugadores'])==dueños_actuales
            for p in self.pactos):return res
        if interior and any(p['activo'] and p['tipo']=='condominio' and p['pais']==pais and
            set(p['jugadores'])=={actor,defensor_idx} for p in self.pactos):return res
        a=self.ejercitos_de(desde,actor); b=self.ejercitos_de(pais,defensor_idx)
        if a<2 or b<1:return res
        max_atk,razon_4_dados=self._dados_para_ataque(a,b)
        max_def=min(3,b)
        if self.situacion=='Nieve':max_def=min(4,max_def+1)
        da=sorted((random.randint(1,6) for _ in range(max_atk)),reverse=True)
        dd=sorted((random.randint(1,6) for _ in range(max_def)),reverse=True)
        ba=min(a-1,sum(x<=y for x,y in zip(da,dd)))
        bd=min(b,sum(x>y for x,y in zip(da,dd)))
        self._ajustar_guarnicion(desde,actor,-ba)
        self._ajustar_guarnicion(pais,defensor_idx,-bd)
        expulsado=self.ejercitos_de(pais,defensor_idx)==0
        if expulsado:
            if interior:
                self.conquisto_pais=True;self.conquistas_turno+=1
            else:
                max_pasar=min(3,self.ejercitos_de(desde,actor)-1)
                if max_pasar>0:
                    self._ajustar_guarnicion(desde,actor,-max_pasar)
                    if pais in self.condominios:self.condominios[pais][actor]=self.condominios[pais].get(actor,0)+max_pasar
                    elif self.tablero[pais]['propietario'] is None:
                        self.tablero[pais]['propietario']=actor;self.tablero[pais]['ejercitos']=max_pasar
                    else:
                        # Desalojado uno: atacante comparte con el superviviente;
                        # desalojados ambos: conquista exclusiva.
                        otro=self.tablero[pais]['propietario']
                        if otro!=actor:
                            self.condominios[pais]={actor:max_pasar,otro:self.tablero[pais]['ejercitos']}
                    if pais in self.condominios:self._sincronizar_condominio(pais)
                    self.conquisto_pais=True;self.conquistas_turno+=1
                self._revocar_tarjetas_continente_por_perdida(self.tablero[pais]['continente'])
            for p in self.pactos_vigentes():
                if (p['tipo']=='condominio' and p['pais']==pais) or p.get('condominio_origen')==pais:
                    p['activo']=False
            self._verificar_eliminacion(defensor_idx,actor)
        self.log(f'ATAQUE CONDOMINIO {desde} -> {pais} (contra {self.jugadores[defensor_idx].color_nombre}): {da} vs {dd} {ba}/{bd}')
        res.update(ok=True,dados_atk=da,dados_def=dd,bajas_atk=ba,bajas_def=bd,
                   conquisto=expulsado,desde=desde,hacia=pais,razon_4_dados=razon_4_dados,
                   atacante_idx=actor,defensor_anterior_idx=defensor_idx,
                   ejercitos_defensor_antes=b)
        self._verificar_victoria(self.jugadores[actor])
        return res
