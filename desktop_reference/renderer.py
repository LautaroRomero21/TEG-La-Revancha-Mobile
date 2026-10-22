"""
renderer.py - Renderizado del juego TEG La Revancha con Pygame.
Gestiona el mapa, el panel lateral y todos los elementos visuales.
"""
import pygame
import os
import math
from data import CONTINENTES, PLAYER_COLORS, COLORES_OFICIALES
from logic import (FASE_INCORPORAR, FASE_MISILES, FASE_ATACAR, FASE_REAGRUPAR, FASE_TARJETA)

# ─── Colores ─────────────────────────────────────────────────────────
# Paleta de interfaz: marino profundo, turquesa y dorado.
C_BG           = (  8,  16,  27)
C_PANEL        = ( 15,  27,  44)
C_PANEL_BORDER = ( 54,  77, 102)
C_TEXT         = (242, 247, 252)
C_TEXT_DIM     = (163, 182, 202)
C_ACCENT       = (247, 192,  92)
C_ACCENT2      = (104, 213, 230)
C_SUCCESS      = (107, 219, 165)
C_DANGER       = (255, 110, 112)
C_BTN_NORMAL   = ( 30,  53,  76)
C_BTN_HOVER    = ( 42,  78, 108)
C_BTN_ACTIVE   = ( 39, 113, 139)
C_BTN_DISABLED = ( 22,  36,  51)
C_HIGHLIGHT_ATK= (255, 126,  90)
C_HIGHLIGHT_DEF= ( 59, 173, 255)
C_HIGHLIGHT_SEL= (250, 199,  92)


FONT_PATH = None   # usa fuente del sistema


class Boton:
    """Acción con alto contraste, indicador lateral y retroalimentación de hover."""
    def __init__(self, rect, texto, accion, color=None, font=None, tooltip=""):
        self.rect = pygame.Rect(rect)
        self.texto = texto
        self.accion = accion
        self.color = color or C_BTN_NORMAL
        self.font = font
        self.tooltip = tooltip
        self.hover = False
        self.activo = True

    def draw(self, surface):
        activo, hover = self.activo, self.hover and self.activo
        col = C_BTN_HOVER if hover else (self.color if activo else C_BTN_DISABLED)
        borde = C_ACCENT2 if hover else (C_PANEL_BORDER if activo else (32, 46, 61))
        pygame.draw.rect(surface, (5, 12, 23), self.rect.move(0, 2), border_radius=9)
        pygame.draw.rect(surface, col, self.rect, border_radius=9)
        pygame.draw.rect(surface, borde, self.rect, 1 if not hover else 2, border_radius=9)
        if activo:
            pygame.draw.rect(surface, C_ACCENT2 if hover else C_ACCENT,
                             (self.rect.x+2, self.rect.y+8, 3, self.rect.h-16), border_radius=2)
        if self.font:
            texto = self.font.render(self.texto, True, C_TEXT if activo else (107, 126, 144))
            if self.rect.h<=32:
                surface.blit(texto,texto.get_rect(center=self.rect.center))
            else:
                surface.blit(texto, texto.get_rect(midleft=(self.rect.x+14,self.rect.centery)))
        if activo and self.rect.h>32:
            xc,yc=self.rect.right-17,self.rect.centery
            pygame.draw.line(surface, C_ACCENT2 if hover else C_TEXT_DIM,
                             (xc-5,yc-4),(xc,yc),2)
            pygame.draw.line(surface, C_ACCENT2 if hover else C_TEXT_DIM,
                             (xc,yc),(xc-5,yc+4),2)

    def check_hover(self, pos):
        self.hover = self.rect.collidepoint(pos) and self.activo

    def check_click(self, pos) -> bool:
        return self.activo and self.rect.collidepoint(pos)


class Renderer:
    """Gestiona toda la interfaz grafica del juego."""

    WIN_W, WIN_H = 1880, 900
    LEFT_W = 280
    MAP_X = LEFT_W
    MAP_W = 1200   # mapa en proporción 4:3
    MAP_H = 900
    PANEL_X = MAP_X + MAP_W
    PANEL_W = 400

    RADIO_TOKEN  = 16  # radio del circulo de token de pais

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("TEG · La Revancha | Edición digital")
        # SCALED adapta la ventana física en pantallas menores conservando
        # coordenadas lógicas del mapa, botones y clics.
        self.screen = pygame.display.set_mode((self.WIN_W, self.WIN_H), pygame.SCALED)
        self.clock  = pygame.time.Clock()

        # Renderizado antialias con tipografía del sistema (sin dependencias extra).
        # Inter en Linux; Segoe UI en Windows. La resolución mayor evita texto diminuto.
        familia = "Inter,Segoe UI,Arial"
        self.font_micro = pygame.font.SysFont(familia, 12, bold=True)
        self.font_sm  = pygame.font.SysFont(familia, 14)
        self.font_md  = pygame.font.SysFont(familia, 15, bold=True)
        self.font_lg  = pygame.font.SysFont(familia, 19, bold=True)
        self.font_xl  = pygame.font.SysFont(familia, 25, bold=True)
        self.font_title = pygame.font.SysFont(familia, 30, bold=True)
        self.font_hero = pygame.font.SysFont(familia, 43, bold=True)
        self.font_token_1d = pygame.font.SysFont(familia, 18, bold=True)
        self.font_token_2d = pygame.font.SysFont(familia, 15, bold=True)
        self.font_misil    = pygame.font.SysFont(familia, 11, bold=True)

        # Cargar mapa
        base=os.path.dirname(__file__)
        map_path=os.path.join(base,'mapa_ui.jpg')
        if not os.path.exists(map_path):
            map_path=os.path.join(base,'mapa.jpg')
        if os.path.exists(map_path):
            raw=pygame.image.load(map_path)
            if raw.get_size()==(self.MAP_W,self.MAP_H):
                self.mapa=raw.convert()
            else:
                self.mapa=pygame.transform.smoothscale(raw,(self.MAP_W,self.MAP_H)).convert()
        else:
            self.mapa = pygame.Surface((self.MAP_W, self.MAP_H))
            self.mapa.fill((50, 80, 60))

        # Estado de UI
        self.pais_seleccionado = None   # primer clic (origen)
        self.pais_objetivo     = None   # segundo clic (destino)
        self.modo              = "normal"  # "normal" | "atacar" | "reagrupar" | "incorporar"
        self.resultado_dados   = None   # ultimo resultado de combate para animacion
        self.dado_alpha        = 0      # para fade
        self.botones           = []
        self.scroll_log        = 0      # scroll del historial
        self._conexion_cache_key = None
        self._conexion_cache = None
        self.popup             = None   # popup modal (dict con texto)
        self.menu_contextual   = None   # lista de acciones al pulsar botón derecho
        self._pacto_contexto   = {}
        self.animacion_timer   = 0
        # Efecto independiente de los dados: sigue el ataque directamente sobre
        # el mapa, incluso cuando el bot realiza acciones encadenadas.
        self.combate_visual = None
        self.ultima_conquista_visual = None
        # Países recién conquistados: el motor cambia de dueño inmediatamente,
        # pero se conserva brevemente el defensor en el mapa para ver el ataque.
        self.transiciones_conquista = {}
        self.incorporacion_visual = None
        self.reagrupe_visual = None
        self.canje_visual = None
        self.vista_tarjetas = None
        self.ultimo_evento_bot = ''
        self.animaciones_activas = True
        self.velocidades_bot = [("PAUSA",None),("1x",1100),("2x",550),("4x",250),("8x",90)]
        self.velocidad_bot_idx = 1
        # Las misiones son imágenes recortadas y orientadas del PDF aportado.
        self.imagenes_objetivos = {}
        for numero in range(19):
            archivo=os.path.join(os.path.dirname(__file__),'objetivos_imagenes',f'obj_{numero:02d}.png')
            if os.path.exists(archivo):
                self.imagenes_objetivos[numero]=pygame.image.load(archivo).convert_alpha()
        self._miniaturas_objetivos = {}
        for numero, imagen in self.imagenes_objetivos.items():
            self._miniaturas_objetivos[numero]=pygame.transform.smoothscale(imagen,(65,48))
        self.iconos_cartas = {}
        for figura in ('Soldado','Granada','Tanque','Avion','Barco'):
            archivo=os.path.join(os.path.dirname(__file__),'iconos_cartas',figura+'.png')
            if os.path.exists(archivo):
                original=pygame.image.load(archivo).convert_alpha()
                # Los cinco PNG del juego están ahora verticales, girados 90° horario.
                # Se adaptan a su espacio sin cortar ninguna parte de la figura.
                ancho,alto=original.get_size()
                escala=min(76/ancho,71/alto)
                self.iconos_cartas[figura]=pygame.transform.smoothscale(
                    original,(max(1,int(ancho*escala)),max(1,int(alto*escala))))
        self.icono_misil = None
        archivo_misil=os.path.join(base,'iconos_ui','misil.png')
        if os.path.exists(archivo_misil):
            self.icono_misil=pygame.transform.smoothscale(
                pygame.image.load(archivo_misil).convert_alpha(),(27,50))


    def _texto(self, cadena, x, y, font=None, color=C_TEXT, max_ancho=None):
        """Texto con antialias; elipsis según los píxeles disponibles."""
        f=font or self.font_sm
        cadena=str(cadena)
        if max_ancho is not None and f.size(cadena)[0]>max_ancho:
            while cadena and f.size(cadena+'…')[0]>max_ancho:
                cadena=cadena[:-1]
            cadena+='…'
        img=f.render(cadena,True,color)
        self.screen.blit(img,(round(x),round(y)))
        return img.get_width()

    def _tarjeta(self, rect, color=(21,38,59), borde=(47,73,99), radio=11):
        r=pygame.Rect(rect)
        pygame.draw.rect(self.screen,(7,16,29),r.move(0,2),border_radius=radio)
        pygame.draw.rect(self.screen,color,r,border_radius=radio)
        pygame.draw.rect(self.screen,borde,r,1,border_radius=radio)

    def _layout_panel(self, juego):
        """Una única geometría para dibujar y para zonas clicables de botones."""
        filas=len(juego.jugadores)
        fin_jugadores=168 + filas*38
        fase_y=fin_jugadores+12
        # La tarjeta de incorporación crece según los continentes pendientes.
        # Dos columnas permiten ver todos los destinos obligatorios sin tapar
        # los botones del turno, incluso con cinco o seis participantes.
        if juego.fase==FASE_INCORPORAR:
            n_continentes=len(juego.desglose_incorporacion()['continentes'])
            fase_alto=100+((n_continentes+1)//2)*21
        else:
            fase_alto=78
        usuario_y=fase_y+fase_alto+10
        acciones_titulo_y=usuario_y+88
        inicio_botones=acciones_titulo_y+25
        # Preparación/canje/ataque/reagrupación: como máximo cuatro acciones.
        util_y=inicio_botones+4*46+6
        return dict(fase_y=fase_y, fase_alto=fase_alto, usuario_y=usuario_y,
                    acciones_y=acciones_titulo_y, boton_y=inicio_botones,
                    util_y=util_y, log_y=util_y+43)

    def _coord_local(self, coords: tuple) -> tuple:
        x_orig, y_orig = coords
        x = int(x_orig * self.MAP_W / 1280)
        y = int(y_orig * self.MAP_H / 960)
        return (x, y)

    def _escalar_coords(self, coords: tuple) -> tuple:
        """
        Las coordenadas en data.py estan definidas para 1280x960.
        Las escalamos al area visible de mapa de 1200x900.
        """
        x, y = self._coord_local(coords)
        return (self.MAP_X + x, y)

    # ─── Construccion de botones ────────────────────────────────────

    def construir_botones(self, juego):
        """Reconstruye controles con la misma geometría que el panel responsivo."""
        self.botones=[]
        px=self.PANEL_X+16
        pw=self.PANEL_W-32
        fase=juego.fase
        jugador=juego.jugador_actual()
        descansa=juego.situacion==f'Descanso {jugador.color_nombre}'
        elegido=self.pais_seleccionado
        propio=elegido in juego.tablero and juego.tablero[elegido]['propietario']==jugador.idx
        destino=self.pais_objetivo is not None
        if fase==FASE_INCORPORAR:
            canje=(juego.etapa=='hostilidades' and jugador.canje_ultima_ronda!=juego.ronda
                   and juego.opcion_canje(jugador) is not None)
            acciones=[
                ('CANJEAR TARJETAS','ver_tarjetas',canje,'Abrí tus tarjetas y elegí un canje válido.'),
                ('COMPRAR MISIL · 6 REF.','misil_nuevo',propio and juego.ejercitos_a_colocar>=6,'Clic derecho sobre un país propio para seleccionarlo.'),
                ('CONVERTIR 6 EJ. EN MISIL','misil_convertir',propio and juego.tablero[elegido]['ejercitos']>=7 if propio else False,'Convertí seis ejércitos propios en un misil.'),
            ]
        elif fase==FASE_ATACAR:
            acciones=[
                ('ATACAR','atacar_4',propio and destino and not descansa,'Primero seleccioná origen y país enemigo limítrofe.'),
                ('LANZAR MISIL','lanzar_misil',propio and destino and not descansa and juego.tablero[elegido]['misiles']>0 if propio else False,'Alcance: uno, dos o tres países de distancia.'),
                ('LIMPIAR SELECCIÓN','cancelar',True,'Reiniciá la selección de países.'),
                ('IR A REAGRUPAR','pasar',True,'Al avanzar ya no podrás atacar en este turno.'),
            ]
        elif fase==FASE_REAGRUPAR:
            acciones=[
                ('MOVER EJÉRCITOS','reagrupar',propio and destino and not descansa,'Entre dos territorios propios limítrofes.'),
                ('MOVER MISIL','reagrupar_misil',propio and destino and not descansa,'Entre dos territorios propios limítrofes.'),
                ('LIMPIAR SELECCIÓN','cancelar',True,''),
                ('IR A TARJETAS','pasar',True,'Pasás a solicitar tarjeta si conquistaste.'),
            ]
        elif fase==FASE_TARJETA:
            acciones=[
                ('SOLICITAR TARJETA','solicitar_tarjeta',juego.puede_solicitar_tarjeta(),'Una carta, si cumplís los requisitos de conquista.'),
                ('TERMINAR TURNO','pasar',True,'Si no pedís la tarjeta ahora, perdés el derecho.'),
            ]
        else:
            acciones=[]
        layout=self._layout_panel(juego)
        # Hay cuatro espacios reservados: orden y posición consistentes en todas las fases.
        for i,(texto,accion,activo,ayuda) in enumerate(acciones):
            b=Boton((px,layout['boton_y']+i*46,pw,40),texto,accion,
                    font=self.font_md,tooltip=ayuda)
            b.activo=activo and not jugador.es_bot
            self.botones.append(b)
        etiquetas=[('CARTAS [T]','ver_tarjetas'),('MISIÓN [O]','ver_objetivos'),
                   ('LOG [H]','ver_historial'),('PACTOS [P]','ver_pactos'),
                   ('BOT '+self.velocidades_bot[self.velocidad_bot_idx][0]+' [F]','velocidad_bot')]
        btn_gap=6
        btn_w=(pw-btn_gap*4)//5
        for i,(txt,act) in enumerate(etiquetas):
            x=px+i*(btn_w+btn_gap)
            ancho=btn_w if i<4 else pw-(btn_w+btn_gap)*4
            b=Boton((x,layout['util_y'],ancho,32),txt,act,font=self.font_micro)
            self.botones.append(b)

    def cambiar_velocidad_bot(self):
        self.velocidad_bot_idx = (self.velocidad_bot_idx+1)%len(self.velocidades_bot)
        return self.velocidades_bot[self.velocidad_bot_idx][1]

    def ms_entre_pasos_bot(self):
        return self.velocidades_bot[self.velocidad_bot_idx][1]

    # ─── Render principal ───────────────────────────────────────────

    def render(self, juego):
        self.screen.fill(C_BG)

        # Mapa centrado entre los paneles.
        self.screen.blit(self.mapa, (self.MAP_X, 0))
        self._dibujar_conexiones_mar(juego)
        self._dibujar_tokens(juego)
        if self.animaciones_activas:
            self._dibujar_efecto_combate()
            self._dibujar_efecto_incorporacion()
            self._dibujar_efecto_reagrupe()

        # Paneles laterales
        self._dibujar_panel_izquierdo(juego)
        self._dibujar_panel(juego)

        # Tooltip en botones.
        for btn in self.botones:
            if btn.hover and btn.tooltip:
                mensaje=self.font_sm.render(btn.tooltip, True, C_TEXT)
                ancho=min(self.PANEL_W-16,mensaje.get_width()+14)
                y=min(self.WIN_H-34,btn.rect.bottom+2)
                pygame.draw.rect(self.screen,(32,42,65),(self.PANEL_X+8,y,ancho,25),border_radius=5)
                self._texto(btn.tooltip,self.PANEL_X+14,y+5,self.font_sm,C_TEXT,max_ancho=ancho-12)
                break

        if self.vista_tarjetas:
            self._dibujar_vista_tarjetas(juego)

        if self.menu_contextual and not self.popup:
            self._dibujar_menu_contextual()

        if self.popup:
            self._dibujar_popup(juego)

        pygame.display.flip()
        self.clock.tick(60)

    def _resumen_hover_o_seleccion(self, juego):
        mouse=pygame.mouse.get_pos()
        en_mapa=self.MAP_X <= mouse[0] < self.MAP_X + self.MAP_W
        hover=self.pais_en_pos(mouse,juego.tablero) if en_mapa else None
        if hover:
            p=juego.tablero[hover]
            propietario=p['propietario']
            if hover in juego.condominios:
                nombre=' + '.join(f'{juego.jugadores[i].color_nombre} {n}' for i,n in juego.condominios[hover].items())
            else:
                nombre=juego.jugadores[propietario].color_nombre if propietario is not None else 'Sin dueño'
            texto=f'{hover} · {nombre} · {p["ejercitos"]} ej.'
            if p['misiles']:
                texto+=f' · {p["misiles"]} misil(es)'
            return texto
        if self.pais_seleccionado:
            texto='Origen: '+self.pais_seleccionado
            if self.pais_objetivo:
                texto+=' → Destino: '+self.pais_objetivo
            return texto
        return 'Seleccioná un territorio del mapa para jugar'

    def _dibujar_panel_izquierdo(self, juego):
        x,w=0,self.LEFT_W
        pygame.draw.rect(self.screen,C_PANEL,(x,0,w,self.WIN_H))
        pygame.draw.line(self.screen,C_PANEL_BORDER,(w-1,0),(w-1,self.WIN_H),2)
        self._texto('CENTRO DE EVENTOS',16,14,self.font_lg,C_ACCENT)
        self._texto('Animaciones '+('activas' if self.animaciones_activas else 'desactivadas'),16,42,self.font_sm,C_TEXT_DIM)
        y=74
        # Evento principal del momento
        titulo='ESTADO'
        lineas=[]
        color=C_ACCENT2
        if self.combate_visual:
            c=self.combate_visual
            titulo='ATAQUE EN CURSO'
            color=C_HIGHLIGHT_ATK if c['tipo']!='misil' else C_ACCENT
            duelo=(f"{c['atacante_color_nombre']} ataca a {c['defensor_color_nombre']}"
                  if c.get('defensor_color_nombre') else c['jugador'])
            lineas=[duelo, f"{c['desde']} → {c['hacia']}",
                    ('Conquista confirmada' if c.get('conquista') else 'Combate activo'),
                    f"Bajas A/D: {c.get('bajas_atk',0)} / {c.get('bajas_def',0)}"]
        elif self.reagrupe_visual:
            r=self.reagrupe_visual
            titulo='REAGRUPAMIENTO'
            color=C_SUCCESS
            item='misil' if r['tipo']=='misil' else 'ejércitos'
            detalle='1 misil' if r['tipo']=='misil' else f"{r['cantidad']} ejércitos"
            lineas=[f"{r['desde']} → {r['hacia']}", f"Traslado de {detalle}"]
        elif self.incorporacion_visual:
            r=self.incorporacion_visual
            titulo='INCORPORACIÓN'
            color=C_SUCCESS if r['tipo']=='ejercitos' else C_ACCENT
            detalle='1 misil' if r['tipo']=='misil' else f"+{r['cantidad']} ejércitos"
            lineas=[r['pais'], detalle]
        elif self.canje_visual:
            c=self.canje_visual
            titulo='CANJE REALIZADO'
            color=C_ACCENT
            lineas=[c['jugador'], f"+{c['valor']} ejércitos"]
        elif self.ultimo_evento_bot:
            titulo='ÚLTIMO EVENTO'
            color=C_ACCENT2
            lineas=self._ajustar_lineas(self.ultimo_evento_bot,self.font_sm,w-34)[:3]
        self._tarjeta((12,y,w-24,110),(20,39,58),(54,84,106),12)
        self._texto(titulo,24,y+10,self.font_md,color,max_ancho=w-48)
        ty=y+36
        for linea in lineas[:4]:
            self._texto(linea,24,ty,self.font_sm,C_TEXT,max_ancho=w-48)
            ty+=19
        y+=120
        # Resultado de dados / canje / conquista
        if self.resultado_dados and self.animacion_timer > 0:
            r=self.resultado_dados
            self._tarjeta((12,y,w-24,154),(22,42,63),(62,92,112),12)
            self._texto('DADOS DEL COMBATE',24,y+10,self.font_md,C_ACCENT,max_ancho=w-48)
            self._texto('ATACA',24,y+37,self.font_micro,C_DANGER)
            self._texto('DEFIENDE',24,y+73,self.font_micro,C_ACCENT2)
            for fila,(clave,tono) in enumerate((('dados_atk',C_DANGER),('dados_def',C_ACCENT2))):
                for i,dado in enumerate(r.get(clave,[])[:3]):
                    self._dibujar_dado(96+i*41,y+31+fila*36,dado,tono,tamano=30)
            bajas=f'-{r.get("bajas_atk",0)} atk / -{r.get("bajas_def",0)} def'
            self._texto(bajas,24,y+111,self.font_sm,C_TEXT,max_ancho=w-48)
            extra=r.get('razon_4_dados') or ('Territorio conquistado' if r.get('conquisto') else '')
            if extra:
                self._texto(extra,24,y+131,self.font_micro,C_ACCENT,max_ancho=w-48)
            self.animacion_timer -= 1
            y+=164
        if self.ultima_conquista_visual:
            c=self.ultima_conquista_visual
            if pygame.time.get_ticks()-c['inicio']<c['duracion']:
                self._tarjeta((12,y,w-24,76),(22,40,58),(90,120,142),12)
                self._texto('PAÍS CONQUISTADO',24,y+10,self.font_md,C_ACCENT,max_ancho=w-48)
                self._texto(c['pais'],24,y+35,self.font_lg,C_TEXT,max_ancho=w-48)
                self._texto(c['jugador'],24,y+56,self.font_sm,C_TEXT_DIM,max_ancho=w-48)
                y+=86
            else:
                self.ultima_conquista_visual=None
        if self.canje_visual and pygame.time.get_ticks()-self.canje_visual['inicio']<self.canje_visual['duracion']:
            c=self.canje_visual
            self._tarjeta((12,y,w-24,74),(34,54,40),(98,146,89),12)
            self._texto('CANJE DE CARTAS',24,y+10,self.font_md,C_SUCCESS,max_ancho=w-48)
            self._texto(c['jugador'],24,y+34,self.font_sm,C_TEXT,max_ancho=w-48)
            self._texto(f'+{c["valor"]} ejércitos',24,y+53,self.font_md,C_ACCENT,max_ancho=w-48)
            y+=84
        elif self.canje_visual and pygame.time.get_ticks()-self.canje_visual['inicio']>=self.canje_visual['duracion']:
            self.canje_visual=None
        # Ayuda fija abajo
        hud_h=86
        by=self.WIN_H-hud_h-14
        self._tarjeta((12,by,w-24,hud_h),(19,35,52),(53,82,104),12)
        self._texto('MAPA Y SELECCIÓN',24,by+10,self.font_md,C_ACCENT2,max_ancho=w-48)
        resumen=self._resumen_hover_o_seleccion(juego)
        lineas=self._ajustar_lineas(resumen,self.font_sm,w-42)[:3]
        ty=by+34
        for linea in lineas:
            self._texto(linea,24,ty,self.font_sm,C_TEXT,max_ancho=w-48)
            ty+=18

    def _dibujar_ayuda_mapa(self, juego):
        return

    def _estado_visual_token(self, pais, juego, ahora=None):
        """Devuelve la ficha a dibujar sin alterar nunca el tablero real.

        Un país conquistado mantiene brevemente el color PREVIO del defensor,
        y después revela el color y las tropas reales del vencedor. Un ataque
        posterior desde ese mismo país lo revela inmediatamente para evitar
        que parezca que un color enemigo lanzó el siguiente ataque.
        """
        datos=juego.tablero[pais]
        actual=(datos['propietario'],datos['ejercitos'])
        if not getattr(self,'animaciones_activas',True):
            return actual
        transiciones=getattr(self,'transiciones_conquista',{})
        trans=transiciones.get(pais)
        if not trans:
            return actual
        tiempo=pygame.time.get_ticks() if ahora is None else ahora
        transcurrido=tiempo-trans['inicio']
        if (transcurrido>=trans['duracion'] or
            datos['propietario']!=trans['atacante_idx']):
            transiciones.pop(pais,None)
            return actual
        nuevo_ataque=getattr(self,'combate_visual',None)
        if (nuevo_ataque and nuevo_ataque['desde']==pais and
            nuevo_ataque['inicio']>trans['inicio']):
            transiciones.pop(pais,None)
            return actual
        if transcurrido<trans['mostrar_defensor_ms']:
            return (trans['defensor_idx'],trans['ejercitos_defensor'])
        return actual

    def _dibujar_tokens(self, juego):
        """Dibuja las fichas, manteniendo el color anterior en una conquista animada."""
        for nombre, datos in juego.tablero.items():
            cx, cy = self._escalar_coords(datos["coords"])
            dueno_idx,ejercitos=self._estado_visual_token(nombre,juego)
            color = juego.jugadores[dueno_idx].color if dueno_idx is not None else (100, 100, 100)
            misiles   = datos["misiles"]

            # Determinar borde segun seleccion
            borde_color = None
            borde_w     = 2

            if nombre == self.pais_seleccionado:
                borde_color = C_HIGHLIGHT_SEL
                borde_w     = 3
            elif nombre == self.pais_objetivo:
                borde_color = C_HIGHLIGHT_DEF
                borde_w     = 3
            elif (self.pais_seleccionado and
                  nombre in juego.tablero[self.pais_seleccionado]["fronteras"] and
                  juego.tablero[nombre]["propietario"] != juego.tablero[self.pais_seleccionado]["propietario"]):
                borde_color = C_HIGHLIGHT_ATK
                borde_w     = 2

            # Sombra del token
            pygame.draw.circle(self.screen, (5, 11, 22), (cx+2, cy+3), self.RADIO_TOKEN+3)
            # Contraste adicional para el jugador negro y blanco.
            pygame.draw.circle(self.screen, color, (cx, cy), self.RADIO_TOKEN)
            if nombre in juego.condominios:
                # Una mitad de color por firmante, ejércitos en mini-etiquetas.
                duo=list(juego.condominios[nombre].items())
                pygame.draw.circle(self.screen,juego.jugadores[duo[0][0]].color,(cx,cy),self.RADIO_TOKEN)
                pygame.draw.polygon(self.screen,juego.jugadores[duo[1][0]].color,
                    [(cx,cy-self.RADIO_TOKEN),(cx+self.RADIO_TOKEN,cy),(cx,cy+self.RADIO_TOKEN)])
                color=(21,35,53)
            borde_externo=(214,232,242) if dueno_idx is not None and juego.jugadores[dueno_idx].color_nombre=='Negro' else (28,40,53)
            pygame.draw.circle(self.screen,borde_externo,(cx,cy),self.RADIO_TOKEN,2)

            # Borde del token
            if borde_color:
                pygame.draw.circle(self.screen, borde_color, (cx, cy), self.RADIO_TOKEN + 1, borde_w)
                pygame.draw.circle(self.screen, (20, 20, 20), (cx, cy), self.RADIO_TOKEN + borde_w, 1)
            else:
                pygame.draw.circle(self.screen, borde_externo, (cx, cy), self.RADIO_TOKEN, 2)

            # Numero de ejercitos (grande, en negrita y con contraste optimo)
            font_num = self.font_token_1d if ejercitos < 10 else self.font_token_2d
            lum = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
            txt_color = (15, 15, 15) if lum > 150 else (255, 255, 255)

            etiqueta=(str(ejercitos) if nombre not in juego.condominios
                      else '/'.join(str(n) for n in juego.condominios[nombre].values()))
            if nombre in juego.condominios:font_num=self.font_misil;txt_color=(255,255,255)
            txt = font_num.render(etiqueta, True, txt_color)
            trect = txt.get_rect(center=(cx, cy))
            self.screen.blit(txt, trect)

            # Misil realista vertical, pegado al costado izquierdo del círculo
            # (como en el ejemplo), superponiéndose sólo al borde del token.
            if misiles > 0:
                mx,my=cx-29,cy-28
                if self.icono_misil:
                    self.screen.blit(self.icono_misil,(mx,my))
                else:
                    # Fallback si el archivo del recurso no está disponible.
                    pygame.draw.polygon(self.screen,(54,59,68),
                        [(cx-16,cy-27),(cx-25,cy-12),(cx-25,cy+11),
                         (cx-30,cy+20),(cx-7,cy+20),(cx-12,cy+11),(cx-12,cy-12)])
                # 1 solo misil no necesita número; varios muestran su cantidad.
                if misiles>1:
                    etiqueta=str(misiles)
                    centro=(cx-14,cy-26)
                    font=self.font_misil
                    tw,th=font.size(etiqueta)
                    radio=max(10,(tw+8)//2)
                    pygame.draw.circle(self.screen,(12,26,41),centro,radio+2)
                    pygame.draw.circle(self.screen,C_ACCENT,centro,radio)
                    imagen=font.render(etiqueta,True,(12,20,30))
                    self.screen.blit(imagen,imagen.get_rect(center=centro))

    def _dibujar_conexiones_mar(self, juego):
        """Resalta sólo la conexión seleccionada, si figura en el grafo vigente.

        El mapa JPG ya contiene todas las líneas punteadas oficiales; dibujar aquí
        una lista antigua agregaba erróneamente enlaces que el usuario eliminó.
        """
        a,b=self.pais_seleccionado,self.pais_objetivo
        if not a or not b or a not in juego.tablero or b not in juego.tablero:
            return
        if b not in juego.tablero[a]['fronteras']:
            return
        ca=self._coord_local(juego.tablero[a]['coords'])
        cb=self._coord_local(juego.tablero[b]['coords'])
        dx,dy=cb[0]-ca[0],cb[1]-ca[1]
        distancia=math.hypot(dx,dy)
        if distancia < 2: return
        # Superficie cacheada para no crear 4 MB de píxeles en cada frame.
        tono=C_HIGHLIGHT_DEF if juego.tablero[b]['propietario']==juego.tablero[a]['propietario'] else C_HIGHLIGHT_ATK
        clave=(a,b,tono)
        if clave!=self._conexion_cache_key:
            trazo=pygame.Surface((self.MAP_W,self.MAP_H),pygame.SRCALPHA)
            for i in range(int(distancia//14)+1):
                t=i*14/distancia
                u=min(1.0,(i*14+7)/distancia)
                if t>=1:break
                ini=(int(ca[0]+dx*t),int(ca[1]+dy*t))
                fin=(int(ca[0]+dx*u),int(ca[1]+dy*u))
                pygame.draw.line(trazo,(*tono,115),ini,fin,3)
            self._conexion_cache_key=clave
            self._conexion_cache=trazo
        self.screen.blit(self._conexion_cache,(self.MAP_X,0))

    # ─── Panel lateral ──────────────────────────────────────────────

    def _dibujar_panel(self, juego):
        """Dashboard con orden de turno realmente rotativo y jerarquía legible."""
        x=self.PANEL_X
        w=self.PANEL_W
        px=x+16
        pw=w-32
        layout=self._layout_panel(juego)
        pygame.draw.rect(self.screen,C_PANEL,(x,0,w,self.WIN_H))
        pygame.draw.rect(self.screen,(12,24,41),(x,0,w,91))
        pygame.draw.line(self.screen,C_ACCENT2,(x,0),(x,self.WIN_H),2)
        pygame.draw.line(self.screen,C_PANEL_BORDER,(x+16,90),(x+w-16,90),1)

        # Marca con un icono vectorial de globo, sin cargar recursos externos.
        cx,cy=x+39,40
        pygame.draw.circle(self.screen,(29,69,86),(cx,cy),23)
        pygame.draw.circle(self.screen,C_ACCENT2,(cx,cy),15,2)
        pygame.draw.ellipse(self.screen,C_ACCENT2,(cx-7,cy-15,14,30),1)
        pygame.draw.line(self.screen,C_ACCENT2,(cx-15,cy),(cx+15,cy),1)
        self._texto('TEG',x+69,15,self.font_title,C_ACCENT)
        self._texto('LA REVANCHA',x+72,53,self.font_md,C_TEXT)
        self._texto('EDICIÓN DIGITAL',x+w-126,24,self.font_micro,C_TEXT_DIM)
        self._texto('PYGAME  •  72 PAÍSES',x+w-145,48,self.font_micro,C_ACCENT2)

        # Cinta de ronda, situación y dueño del turno.
        self._tarjeta((px,99,pw,43),(22,44,65),(48,82,102),9)
        self._texto('RONDA '+str(juego.ronda) if juego.ronda else 'PREPARACIÓN',px+11,105,self.font_micro,C_ACCENT)
        self._texto(juego.situacion,px+11,120,self.font_sm,C_TEXT,max_ancho=pw-140)
        jugador=juego.jugador_actual()
        pygame.draw.circle(self.screen,jugador.color,(px+pw-108,120),8)
        pygame.draw.circle(self.screen,C_TEXT_DIM,(px+pw-108,120),8,1)
        self._texto('TURNO ACTUAL',px+pw-93,114,self.font_micro,C_TEXT_DIM,max_ancho=91)

        self._texto('ORDEN DE JUEGO',px,151,self.font_micro,C_TEXT_DIM)
        self._texto('ROTACIÓN POR RONDA',px+pw-162,151,self.font_micro,C_ACCENT2)

        # IMPORTANTE: se itera orden_ronda y NO jugadores. Eliminados al pie.
        indices=juego.orden_visual_jugadores()
        for pos,idx in enumerate(indices):
            jug=juego.jugadores[idx]
            yy=168+pos*38
            activo=(idx==juego.turno_idx)
            eliminado=jug.eliminado
            bg=(35,65,83) if activo else ((19,31,45) if eliminado else (24,41,59))
            border=C_ACCENT2 if activo else (42,64,83)
            self._tarjeta((px,yy,pw,34),bg,border,8)
            if activo:
                pygame.draw.rect(self.screen,C_ACCENT2,(px+1,yy+6,3,22),border_radius=2)
            self._texto(f'{pos+1:02d}',px+10,yy+9,self.font_micro,C_ACCENT if activo else C_TEXT_DIM)
            col=jug.color if not eliminado else (71,79,91)
            pygame.draw.circle(self.screen,(6,14,24),(px+52,yy+17),11)
            pygame.draw.circle(self.screen,col,(px+52,yy+17),8)
            pygame.draw.circle(self.screen,(223,234,246) if jug.color_nombre=='Negro' else (148,171,190),
                               (px+52,yy+17),8,1)
            if activo:
                pygame.draw.circle(self.screen,C_ACCENT2,(px+52,yy+17),12,1)
            nombre=(jug.nombre.replace('Humano ','Vos · ').replace('Bot ','Bot · '))
            self._texto(nombre,px+70,yy+8,self.font_md if activo else self.font_sm,
                        C_TEXT if not eliminado else C_TEXT_DIM,max_ancho=pw-162)
            paises=len(juego.paises_de(idx))
            if eliminado:
                etiqueta='FUERA'
            else:
                etiqueta=f'{paises} países'
            ancho=self.font_micro.size(etiqueta)[0]
            self._texto(etiqueta,px+pw-10-ancho,yy+9,self.font_micro,
                        C_ACCENT if activo else C_TEXT_DIM)

        # Estado de fase + mini progreso visual de las cuatro etapas.
        fy=layout['fase_y']
        self._tarjeta((px,fy,pw,layout['fase_alto']),(25,48,68),(46,83,104),11)
        etapa={
            FASE_INCORPORAR:('INCORPORAR',C_SUCCESS,0),
            FASE_MISILES:('MISILES',C_ACCENT,0),
            FASE_ATACAR:('ATACAR',C_DANGER,1),
            FASE_REAGRUPAR:('REAGRUPAR',C_ACCENT2,2),
            FASE_TARJETA:('TARJETAS',C_SUCCESS,3),
            'VICTORIA':('VICTORIA',C_ACCENT,3),
        }
        nombre,col,estado=etapa.get(juego.fase,(juego.fase,C_TEXT,0))
        self._texto('FASE ACTUAL',px+13,fy+10,self.font_micro,C_TEXT_DIM)
        self._texto(nombre,px+13,fy+28,self.font_lg,col,max_ancho=pw-155)
        if juego.fase==FASE_INCORPORAR:
            if juego.etapa_ronda=='INCORPORACION':
                actual=len(juego.incorporaciones_completadas)+1
                total=len([j for j in juego.jugadores if not j.eliminado])
                self._texto(f'TODOS INCORPORAN · {actual}/{total}',px+13,fy+49,self.font_micro,C_ACCENT2)
            else:
                self._texto('INCORPORACIÓN INICIAL',px+13,fy+49,self.font_micro,C_ACCENT2)
            self._texto(str(juego.ejercitos_a_colocar),px+pw-66,fy+12,self.font_xl,C_SUCCESS)
            self._texto('POR PONER',px+pw-105,fy+43,self.font_micro,C_TEXT_DIM)
            pygame.draw.line(self.screen,C_PANEL_BORDER,(px+12,fy+63),(px+pw-12,fy+63),1)
            resumen=juego.desglose_incorporacion()
            pygame.draw.circle(self.screen,C_SUCCESS,(px+17,fy+77),4)
            self._texto('LIBRES · EN CUALQUIER PAÍS',px+29,fy+70,
                        self.font_micro,C_TEXT,max_ancho=pw-95)
            libres=str(resumen['libres'])
            ancho=self.font_md.size(libres)[0]
            self._texto(libres,px+pw-16-ancho,fy+68,self.font_md,C_SUCCESS)
            abreviaciones={
                'America del Norte':'AM. DEL NORTE','America Central':'AM. CENTRAL',
                'America del Sur':'AM. DEL SUR','Africa':'ÁFRICA',
                'Oceania':'OCEANÍA','Europa':'EUROPA','Asia':'ASIA'}
            for ind,(cont,cantidad) in enumerate(resumen['continentes'].items()):
                fila,columna=divmod(ind,2)
                xx=px+13+columna*(pw//2)
                yy=fy+91+fila*21
                pygame.draw.circle(self.screen,C_ACCENT,(xx+4,yy+7),3)
                self._texto(abreviaciones.get(cont,cont.upper()),xx+13,yy,
                            self.font_micro,C_TEXT,max_ancho=135)
                qty=str(cantidad)
                ancho=self.font_md.size(qty)[0]
                self._texto(qty,xx+pw//2-13-ancho,yy-1,self.font_md,C_ACCENT)
        elif self.pais_seleccionado:
            self._texto(self.pais_seleccionado,px+pw-160,fy+29,self.font_sm,C_ACCENT,max_ancho=148)
        for idx in range(4):
            bx=px+14+idx*((pw-28-15)/4+5)
            bw=(pw-28-15)/4
            estado_col=(col if idx==estado else ((67,94,112) if idx<estado else (39,59,76)))
            by=fy+layout['fase_alto']-11
            pygame.draw.rect(self.screen,estado_col,(int(bx),by,int(bw),4),border_radius=2)

        # Información del usuario: objetivo legible, detalle completo desde OBJETIVOS.
        uy=layout['usuario_y']
        self._tarjeta((px,uy,pw,80),(22,38,56),(42,64,86),11)
        humano=juego.jugadores[0]
        misiles=sum(juego.tablero[p]['misiles'] for p in juego.paises_de(0))
        self._texto('TU MISIÓN',px+12,uy+8,self.font_micro,C_ACCENT)
        stats=f'{len(humano.tarjetas)} cartas   ·   {misiles} misiles'
        tw=self.font_micro.size(stats)[0]
        self._texto(stats,px+pw-tw-12,uy+8,self.font_micro,C_ACCENT2)
        objetivos=humano.objetivos if hasattr(humano,'objetivos') else [humano.objetivo]
        if not objetivos:
            self._texto('Sin objetivo asignado',px+12,uy+31,self.font_sm,C_TEXT_DIM)
        for i,obj in enumerate(objetivos[:2]):
            if obj:
                self._texto(f'{i+1}. '+obj['descripcion'],px+12,uy+27+i*22,
                            self.font_sm,C_TEXT,max_ancho=pw-116)
                mini=self._miniaturas_objetivos.get(obj.get('tarjeta_id'))
                if mini:
                    # Para dos cartas: miniaturas superpuestas; al hacer clic en MISIÓN se ven grandes.
                    mx=px+pw-82+(i*12)
                    my=uy+26+(i*7)
                    self.screen.blit(mini,(mx,my))

        self._texto('ACCIONES DEL TURNO',px,layout['acciones_y']+4,self.font_micro,C_TEXT_DIM)
        indicacion=('Clic derecho: acciones sobre país' if juego.fase==FASE_INCORPORAR else
                    'Clic derecho en destino: menú')
        self._texto(indicacion,px+pw-234,layout['acciones_y']+4,
                    self.font_micro,C_ACCENT2,max_ancho=230)
        for btn in self.botones:
            btn.draw(self.screen)

        # Actividad: 2–9 líneas según jugadores; rueda del mouse para recorrer.
        ly=layout['log_y']
        pygame.draw.line(self.screen,C_PANEL_BORDER,(px,ly-3),(px+pw,ly-3),1)
        self._texto('ACTIVIDAD RECIENTE · H PARA AMPLIAR',px,ly+4,self.font_micro,C_TEXT_DIM)
        total=len(juego.historial)
        visibles=max(0,(self.WIN_H-ly-31)//18)
        if visibles:
            max_desfase=max(0,total-visibles)
            self.scroll_log=max(0,min(self.scroll_log,max_desfase))
            fin=total-self.scroll_log
            mensajes=juego.historial[max(0,fin-visibles):fin]
            for i,msg in enumerate(mensajes):
                upper=msg.upper()
                if 'ATAQUE' in upper or 'MISIL' in upper:mc=C_DANGER
                elif 'CONQUISTA' in upper or 'GANA' in upper or 'VICTORIA' in upper:mc=C_ACCENT
                elif 'INCORPORA' in upper or 'BONUS' in upper:mc=C_SUCCESS
                else:mc=C_TEXT_DIM
                self._texto('• '+msg,px+1,ly+26+i*18,self.font_sm,mc,max_ancho=pw-6)
        if total>visibles:
            etiqueta=f'↑ {self.scroll_log} / {total}'
            self._texto(etiqueta,px+pw-self.font_micro.size(etiqueta)[0],ly+4,
                        self.font_micro,C_ACCENT2)

    # ─── Indicadores animados de combate sobre el tablero ───────────

    def registrar_combate(self, desde, hacia, resultado, juego, tipo='ataque', jugador_idx=None):
        """Guarda un efecto visual sin alterar la lógica, los turnos ni los dados.

        El efecto es temporal, pero una conquista conserva un aviso propio que
        no desaparece aunque el bot lance inmediatamente otro ataque.
        """
        if desde not in juego.tablero or hacia not in juego.tablero:
            return False
        idx=(jugador_idx if jugador_idx is not None else
             (resultado or {}).get('atacante_idx',juego.turno_idx))
        if idx is None or not 0 <= idx < len(juego.jugadores):
            return False
        ahora=pygame.time.get_ticks()
        conquista=bool(resultado and resultado.get('conquisto'))
        color=juego.jugadores[idx].color
        anterior=(resultado or {}).get('defensor_anterior_idx')
        defensor_nombre=(juego.jugadores[anterior].color_nombre
                         if isinstance(anterior,int) and 0<=anterior<len(juego.jugadores) else None)
        self.combate_visual={
            'desde':desde, 'hacia':hacia,
            'pos_desde':self._escalar_coords(juego.tablero[desde]['coords']),
            'pos_hacia':self._escalar_coords(juego.tablero[hacia]['coords']),
            'jugador':juego.jugadores[idx].nombre,
            'atacante_color_nombre':juego.jugadores[idx].color_nombre,
            'defensor_color_nombre':defensor_nombre,
            'color':color, 'tipo':tipo, 'conquista':conquista,
            'bajas_atk':(resultado or {}).get('bajas_atk',0),
            'bajas_def':(resultado or {}).get('bajas_def',0),
            'inicio':ahora,
            # En 1x es bien visible; en modos rápidos, el último trazo no
            # parpadea ni consume los eventos del juego.
            'duracion':1450 if conquista else 1050,
        }
        if (conquista and getattr(self,'animaciones_activas',True) and
            defensor_nombre and anterior!=idx and
            hacia not in juego.condominios and
            juego.tablero[hacia]['propietario']==idx and
            (resultado or {}).get('ejercitos_defensor_antes',0)>0):
            # Se muestra el rival al principio del ataque y recién después
            # el nuevo propietario. Funciona igual para humanos y bots.
            if not hasattr(self,'transiciones_conquista'):
                self.transiciones_conquista={}
            self.transiciones_conquista[hacia]={
                'inicio':ahora,'duracion':1450,'mostrar_defensor_ms':950,
                'defensor_idx':anterior,'atacante_idx':idx,
                'ejercitos_defensor':resultado['ejercitos_defensor_antes'],
            }
        if conquista:
            self.ultima_conquista_visual={
                'pais':hacia, 'jugador':juego.jugadores[idx].nombre,
                'color':color, 'inicio':ahora, 'duracion':4200,
            }
        return True

    def registrar_incorporacion(self, pais, cantidad, juego, tipo='ejercitos', jugador_idx=None):
        if pais not in juego.tablero:
            return False
        idx = juego.turno_idx if jugador_idx is None else jugador_idx
        self.incorporacion_visual={
            'pais':pais,'cantidad':cantidad,'tipo':tipo,
            'pos':self._escalar_coords(juego.tablero[pais]['coords']),
            'color':juego.jugadores[idx].color,
            'inicio':pygame.time.get_ticks(),'duracion':1200 if tipo=='ejercitos' else 1450,
        }
        return True

    def registrar_reagrupe(self, desde, hacia, cantidad, juego, tipo='ejercitos', jugador_idx=None):
        if desde not in juego.tablero or hacia not in juego.tablero:
            return False
        idx = juego.turno_idx if jugador_idx is None else jugador_idx
        self.reagrupe_visual={
            'desde':desde,'hacia':hacia,'cantidad':cantidad,'tipo':tipo,
            'pos_desde':self._escalar_coords(juego.tablero[desde]['coords']),
            'pos_hacia':self._escalar_coords(juego.tablero[hacia]['coords']),
            'color':juego.jugadores[idx].color,
            'inicio':pygame.time.get_ticks(),'duracion':1400 if tipo=='ejercitos' else 1600,
        }
        return True

    def registrar_canje(self, jugador_nombre, valor):
        self.canje_visual={'jugador':jugador_nombre,'valor':valor,
                           'inicio':pygame.time.get_ticks(),'duracion':4200}
        return True

    def _dibujar_efecto_incorporacion(self):
        e=self.incorporacion_visual
        if not e:return
        t=pygame.time.get_ticks()-e['inicio']
        if t>=e['duracion']:
            self.incorporacion_visual=None
            return
        (cx,cy)=e['pos']
        onda=0.5+0.5*math.sin(t*.02)
        radio=24+int(10*onda)
        color=C_SUCCESS if e['tipo']=='ejercitos' else C_ACCENT
        pygame.draw.circle(self.screen,(8,22,32),(cx,cy),radio+6,4)
        pygame.draw.circle(self.screen,color,(cx,cy),radio,3)
        texto=('+'+str(e['cantidad'])) if e['tipo']=='ejercitos' else '+MISIL'
        ancho=max(74,self.font_md.size(texto)[0]+18)
        rect=pygame.Rect(max(self.MAP_X+8,min(self.MAP_X+self.MAP_W-ancho-8,cx-ancho//2)),
                         max(8,cy-65),ancho,30)
        pygame.draw.rect(self.screen,(9,24,40),rect,border_radius=8)
        pygame.draw.rect(self.screen,color,rect,2,border_radius=8)
        self._texto(texto,rect.x+10,rect.y+6,self.font_md,C_TEXT,max_ancho=ancho-18)

    def _dibujar_efecto_reagrupe(self):
        e=self.reagrupe_visual
        if not e:return
        t=pygame.time.get_ticks()-e['inicio']
        if t>=e['duracion']:
            self.reagrupe_visual=None
            return
        (ax,ay),(bx,by)=e['pos_desde'],e['pos_hacia']
        color=C_SUCCESS if e['tipo']=='ejercitos' else C_ACCENT
        pygame.draw.line(self.screen,(10,24,36),(ax,ay),(bx,by),10)
        pygame.draw.line(self.screen,color,(ax,ay),(bx,by),4)
        dx,dy=bx-ax,by-ay
        distancia=max(1,math.hypot(dx,dy))
        paso=(t%700)/700
        px=int(ax+dx*paso);py=int(ay+dy*paso)
        pygame.draw.circle(self.screen,(9,22,34),(px,py),11)
        pygame.draw.circle(self.screen,color,(px,py),7)
        for posicion in ((ax,ay),(bx,by)):
            pygame.draw.circle(self.screen,color,posicion,23,3)
        # La cantidad trasladada permanece disponible en el panel izquierdo.
        # No se dibujan etiquetas sobre el mapa durante el reagrupamiento.

    def _etiqueta_combate(self, texto, centro, y, color):
        """Etiqueta pequeña, contrastada y contenida dentro del mapa."""
        ancho=min(330,self.font_md.size(texto)[0]+24)
        alto=29
        x=max(self.MAP_X+5,min(self.MAP_X+self.MAP_W-ancho-5,centro[0]-ancho//2))
        y=max(6,min(self.MAP_H-alto-6,int(y)))
        rect=pygame.Rect(x,y,ancho,alto)
        pygame.draw.rect(self.screen,(10,22,34),rect,border_radius=8)
        pygame.draw.rect(self.screen,color,rect,2,border_radius=8)
        self._texto(texto,x+12,y+6,self.font_md,C_TEXT,max_ancho=ancho-22)

    def _dibujar_efecto_combate(self):
        """Ruta de ataque y destellos pulsantes: la ubicación importa más que los dados."""
        c=self.combate_visual
        if not c:return
        transcurrido=pygame.time.get_ticks()-c['inicio']
        if transcurrido>=c['duracion']:
            self.combate_visual=None
            return
        progreso=max(0.0,min(1.0,transcurrido/c['duracion']))
        (ax,ay),(bx,by)=c['pos_desde'],c['pos_hacia']
        misil=c['tipo']=='misil'
        tono=(250,202,96) if misil else C_HIGHLIGHT_ATK
        defensa=C_HIGHLIGHT_DEF
        onda=0.5+0.5*math.sin(transcurrido*.018)
        radio=23+int(7*onda)
        # Línea luminosa, flecha móvil y halo sobre cada ficha.
        pygame.draw.line(self.screen,(13,22,34),(ax,ay),(bx,by),12)
        pygame.draw.line(self.screen,tono,(ax,ay),(bx,by),5)
        pygame.draw.line(self.screen,C_TEXT,(ax,ay),(bx,by),1)
        dx,dy=bx-ax,by-ay
        distancia=math.hypot(dx,dy)
        if distancia>0.01:
            ux,uy=dx/distancia,dy/distancia
            punta=(int(bx-ux*21),int(by-uy*21))
            lado=(-uy,ux)
            triangulo=[punta,
                (int(punta[0]-ux*17+lado[0]*9),int(punta[1]-uy*17+lado[1]*9)),
                (int(punta[0]-ux*17-lado[0]*9),int(punta[1]-uy*17-lado[1]*9))]
            pygame.draw.polygon(self.screen,tono,triangulo)
            # Proyectil desplazándose de origen a destino repetidamente.
            paso=(transcurrido%580)/580
            px=int(ax+dx*paso);py=int(ay+dy*paso)
            pygame.draw.circle(self.screen,(12,22,33),(px,py),10)
            pygame.draw.circle(self.screen,(255,245,194) if misil else (255,235,217),(px,py),6)
        for posicion,col in (((ax,ay),tono),((bx,by),defensa)):
            pygame.draw.circle(self.screen,(11,21,32),posicion,radio+5,4)
            pygame.draw.circle(self.screen,col,posicion,radio,4)
            pygame.draw.circle(self.screen,col,posicion,radio+8,1)
        # Los datos del combate se muestran en la columna izquierda.
        if c['conquista']:
            pygame.draw.circle(self.screen,C_ACCENT,(bx,by),radio+15,3)

    def _dibujar_aviso_conquista(self):
        """Aviso persistente, independiente del siguiente ataque del bot."""
        c=self.ultima_conquista_visual
        if not c:return
        if pygame.time.get_ticks()-c['inicio']>=c['duracion']:
            self.ultima_conquista_visual=None
            return
        x,y,w,h=786,self.MAP_H-68,402,52
        fondo=pygame.Surface((w,h),pygame.SRCALPHA)
        fondo.fill((10,24,38,234))
        self.screen.blit(fondo,(x,y))
        pygame.draw.rect(self.screen,C_ACCENT,(x,y,w,h),2,border_radius=10)
        self._texto('★  PAÍS CONQUISTADO',x+12,y+5,self.font_md,C_ACCENT)
        self._texto(f'{c["pais"]}  ·  {c["jugador"]}',x+12,y+29,self.font_sm,C_TEXT,max_ancho=w-25)

    # ─── Resultado de dados ─────────────────────────────────────────

    def mostrar_resultado_dados(self, resultado: dict, frames=120):
        self.resultado_dados = resultado
        self.animacion_timer = frames

    def _dibujar_resultado_dados(self):
        """Resumen compacto a la derecha del indicador de ataque.

        Antes aparecía sobre el centro del tablero y ocultaba justamente los
        territorios donde los bots peleaban; ahora deja libre todo el mapa.
        """
        r=self.resultado_dados
        if not r:return
        x,y,w,h=self.MAP_W-394,12,382,154
        fondo=pygame.Surface((w,h),pygame.SRCALPHA)
        fondo.fill((12,24,41,234))
        self.screen.blit(fondo,(x,y))
        pygame.draw.rect(self.screen,C_PANEL_BORDER,(x,y,w,h),2,border_radius=11)
        self._texto('DADOS DEL COMBATE',x+12,y+8,self.font_lg,C_ACCENT)
        self._texto('ATACA',x+13,y+41,self.font_micro,C_DANGER)
        self._texto('DEFIENDE',x+13,y+76,self.font_micro,C_ACCENT2)
        for fila,(clave,tono) in enumerate((('dados_atk',C_DANGER),('dados_def',C_ACCENT2))):
            for i,dado in enumerate(r.get(clave,[])):
                self._dibujar_dado(x+92+i*45,y+38+fila*35,dado,tono,tamano=29)
        bajas=f'-{r.get("bajas_atk",0)} atacante  /  -{r.get("bajas_def",0)} defensor'
        self._texto(bajas,x+14,y+113,self.font_sm,C_TEXT,max_ancho=w-28)
        if r.get('razon_4_dados'):
            self._texto('4 DADOS: '+r['razon_4_dados'],x+14,y+133,
                        self.font_micro,C_ACCENT,max_ancho=w-28)
        elif r.get('conquisto'):
            self._texto('¡TERRITORIO CONQUISTADO!',x+14,y+133,self.font_micro,C_ACCENT)

    def _dibujar_dado(self,x,y,valor,color,tamano=40):
        pygame.draw.rect(self.screen,(29,42,58),(x,y,tamano,tamano),border_radius=5)
        pygame.draw.rect(self.screen,color,(x,y,tamano,tamano),2,border_radius=5)
        texto=self.font_md.render(str(valor),True,color)
        self.screen.blit(texto,texto.get_rect(center=(x+tamano//2,y+tamano//2)))

    # ─── Mano de cartas: consultas, símbolos y selección de canjes ──

    def abrir_tarjetas(self, juego, jugador_idx=0):
        self.vista_tarjetas={'jugador':jugador_idx,'pagina':0,'paises':set(),'continentes':set()}

    def _dibujar_vista_tarjetas(self, juego):
        v=self.vista_tarjetas
        w,h=1150,672
        x,y=(self.WIN_W-w)//2,(self.WIN_H-h)//2
        shade=pygame.Surface((self.WIN_W,self.WIN_H),pygame.SRCALPHA)
        shade.fill((3,7,17,212));self.screen.blit(shade,(0,0))
        pygame.draw.rect(self.screen,(26,36,59),(x,y,w,h),border_radius=14)
        pygame.draw.rect(self.screen,C_ACCENT,(x,y,w,h),2,border_radius=14)
        draw=lambda txt,color,xy,font=None:self.screen.blit((font or self.font_md).render(txt,True,color),xy)
        draw('CARTAS DE PAÍS Y CONTINENTE',C_ACCENT,(x+25,y+17),self.font_xl)
        draw('Información abierta: también se pueden consultar cartas de rivales.',C_TEXT_DIM,(x+25,y+46),self.font_sm)
        btns=[]
        def boton(rect,texto,accion,selected=False,enable=True,font=None):
            col=(72,104,154) if selected else ((51,72,106) if enable else (38,42,52))
            pygame.draw.rect(self.screen,col,rect,border_radius=7)
            pygame.draw.rect(self.screen,C_ACCENT if selected else C_PANEL_BORDER,rect,1,border_radius=7)
            f=font or self.font_sm;lbl=f.render(texto,True,C_TEXT if enable else C_TEXT_DIM)
            self.screen.blit(lbl,lbl.get_rect(center=rect.center))
            if enable:btns.append((rect,accion))
        boton(pygame.Rect(x+w-112,y+13,90,31),'CERRAR','cerrar')
        for i,j in enumerate(juego.jugadores):
            rect=pygame.Rect(x+25+i*181,y+83,171,40)
            boton(rect,f'{j.nombre[:15]} ({len(j.tarjetas)})','jugador:'+str(i),v['jugador']==i)
        elegido=juego.jugadores[v['jugador']]
        es_humano=v['jugador']==0
        cartas=[('pais',i,p,juego.figuras_cartas[p]) for i,p in enumerate(elegido.tarjetas)]
        cartas += [('continente',i,c,'+'.join(juego._figuras_continente(c)) or 'CANJE') for i,c in enumerate(sorted(elegido.cartas_continente))]
        paginas=max(1,(len(cartas)+11)//12)
        v['pagina']=min(v['pagina'],paginas-1)
        inicio=v['pagina']*12
        visibles=cartas[inicio:inicio+12]
        for k,(tipo,ind,nombre,figura) in enumerate(visibles):
            r,c=divmod(k,4)
            rx=x+25+c*277; ry=y+145+r*133
            rect=pygame.Rect(rx,ry,264,120)
            marcado=(ind in v['paises'] if tipo=='pais' else nombre in v['continentes']) and es_humano
            disponible=es_humano and juego.fase==FASE_INCORPORAR and juego.etapa=='hostilidades' and juego.jugador_actual().idx==0 and juego.jugador_actual().canje_ultima_ronda!=juego.ronda
            bg=(65,83,97) if marcado else (38,50,76)
            pygame.draw.rect(self.screen,bg,rect,border_radius=8)
            pygame.draw.rect(self.screen,C_ACCENT if marcado else C_PANEL_BORDER,rect,2 if marcado else 1,border_radius=8)
            draw(('✓ ' if marcado else '')+nombre[:29],C_TEXT,(rx+11,ry+10),self.font_md)
            if tipo=='pais':
                ico=self.iconos_cartas.get(figura)
                if ico:self.screen.blit(ico,(rx+14,ry+38))
                draw(figura.upper(),C_ACCENT2,(rx+94,ry+58),self.font_lg)
            else:
                simbolos=juego._figuras_continente(nombre)
                if not simbolos:draw('CANJE COMPLETO',C_ACCENT,(rx+12,ry+65),self.font_lg)
                else:
                    for ix,simbolo in enumerate(simbolos):
                        ico=self.iconos_cartas.get(simbolo)
                        if ico:self.screen.blit(pygame.transform.smoothscale(ico,(52,52)),(rx+11+ix*57,ry+49))
                    draw(' + '.join(simbolos),C_ACCENT2,(rx+12,ry+100),self.font_sm)
                draw('CONTINENTE',C_SUCCESS,(rx+169,ry+38),self.font_sm)
            if disponible:btns.append((rect,('pais:' if tipo=='pais' else 'continente:')+str(ind if tipo=='pais' else nombre)))
        draw(f'Página {v["pagina"]+1}/{paginas}',C_TEXT_DIM,(x+492,y+555),self.font_md)
        boton(pygame.Rect(x+370,y+547,105,36),'ANTERIOR','pagina:-1',enable=v['pagina']>0)
        boton(pygame.Rect(x+615,y+547,105,36),'SIGUIENTE','pagina:1',enable=v['pagina']<paginas-1)
        if es_humano:
            sc=len(v['paises'])+len(v['continentes'])
            valid=juego.canje_valido(sorted(v['paises']),sorted(v['continentes']))
            est=('Combinación válida: ' if valid else 'Seleccioná cartas con 3 símbolos iguales o distintos. ')
            draw(est+f'{sc} seleccionada(s)',C_SUCCESS if valid else C_TEXT_DIM,(x+25,y+610),self.font_md)
            boton(pygame.Rect(x+w-245,y+605,217,39),f'CANJEAR (+{juego.valor_canje()})','canjear_seleccion',enable=valid)
        else:
            draw('Consulta de tarjetas del rival',C_TEXT_DIM,(x+25,y+615),self.font_md)
        v['_rects']=btns

    def click_vista_tarjetas(self,pos,juego):
        v=self.vista_tarjetas
        if not v:return None
        for rect,accion in v.get('_rects',[]):
            if not rect.collidepoint(pos):continue
            if accion=='cerrar':self.vista_tarjetas=None
            elif accion.startswith('jugador:'):
                v['jugador']=int(accion.split(':',1)[1]);v['pagina']=0
            elif accion.startswith('pagina:'):
                v['pagina']+=int(accion.split(':',1)[1])
            elif accion.startswith('pais:'):
                i=int(accion.split(':',1)[1]);v['paises'].symmetric_difference_update({i})
            elif accion.startswith('continente:'):
                cont=accion.split(':',1)[1];v['continentes'].symmetric_difference_update({cont})
            elif accion=='canjear_seleccion':return ('canjear_seleccion',sorted(v['paises']),sorted(v['continentes']))
            return 'vista'
        return 'vista'

    # ─── Popup ──────────────────────────────────────────────────────

    def mostrar_popup(self, titulo, mensaje, botones=None):
        self.popup = {"titulo": titulo, "mensaje": mensaje,
                      "botones": botones or [("OK", "ok")]}

    def mostrar_propuesta_pacto(self, juego, propuesta):
        """Diplomacia legible: decisión en panel derecho sin oscurecer el mapa.

        Los nombres, colores y posiciones se calculan desde el tablero REAL;
        las fichas y sus textos impresos en el mapa pueden tapar topónimos.
        """
        a = propuesta['a']
        if propuesta['tipo'] == 'pais':
            propio_bot, propio_humano = propuesta['paises']
            focos = [
                {'pais': propio_bot, 'rol': 'PAÍS DEL PROPONENTE', 'jugador': a},
                {'pais': propio_humano, 'rol': 'TU PAÍS', 'jugador': 0},
            ]
            titulo = 'NO AGRESIÓN'
            descripcion = 'Los dos territorios quedarán protegidos contra ataques y misiles entre los firmantes.'
        elif propuesta['tipo'] == 'agresion':
            focos = [
                {'pais': propuesta['origen_a'], 'rol': 'ORIGEN DEL PROPONENTE', 'jugador': a},
                {'pais': propuesta['origen_b'], 'rol': 'TU ORIGEN ALIADO', 'jugador': 0},
                {'pais': propuesta['destino'], 'rol': 'PAÍS A CONQUISTAR',
                 'jugador': juego.tablero[propuesta['destino']]['propietario']},
            ]
            titulo = 'ATAQUE CONJUNTO'
            descripcion = 'Atacarán por turnos y, si ganan, compartirán el país como condominio.'
        else:
            return False
        self.popup = {
            'tipo': 'pacto_propuesta', 'titulo': titulo, 'mensaje': descripcion,
            'proponente': juego.jugadores[a].nombre, 'focos': focos,
            'inspeccion': None, 'obligatorio': True,
            'botones': [('ACEPTAR', 'pacto_aceptar_bot'),
                        ('RECHAZAR', 'pacto_rechazar_bot')],
        }
        self.menu_contextual = None
        return True

    def inspeccionar_pais_pacto(self, pos, juego):
        """Mientras un bot espera respuesta, el mapa es consultable pero no jugable."""
        if not self.popup or self.popup.get('tipo') != 'pacto_propuesta':
            return None
        pais = self.pais_en_pos(pos, juego.tablero)
        if pais:
            self.popup['inspeccion'] = pais
        return pais

    def _dibujar_popup_pacto(self, juego):
        """Panel fijo y resaltados en tablero: no oscurecer ni cubrir territorios."""
        pop = self.popup
        focos = pop['focos']
        colores = [C_ACCENT, C_ACCENT2, C_DANGER]
        pop['_btn_rects'] = []

        # Nombres sobre el mapa: anillos alrededor de las fichas y etiquetas
        # diferenciadas por número, para que sean localizables aun si el mapa
        # original imprime el nombre debajo de un ejército.
        cab_x=self.MAP_X+18
        pygame.draw.rect(self.screen,(12,29,45),(cab_x,12,795,55),border_radius=10)
        pygame.draw.rect(self.screen,(93,136,160),(cab_x,12,795,55),1,border_radius=10)
        self._texto('INSPECCIONÁ LOS PAÍSES MARCADOS',cab_x+16,20,self.font_md,C_ACCENT,max_ancho=740)
        self._texto('Mové el cursor o hacé clic en un ejército para consultar su país.',cab_x+16,42,
                    self.font_sm,C_TEXT,max_ancho=750)

        for i, foco in enumerate(focos):
            pais = foco['pais']
            if pais not in juego.tablero:
                continue
            cx, cy = self._escalar_coords(juego.tablero[pais]['coords'])
            c = colores[min(i,2)]
            pygame.draw.circle(self.screen,(8,18,30),(cx,cy),30,5)
            pygame.draw.circle(self.screen,c,(cx,cy),27,4)
            pygame.draw.circle(self.screen,(241,249,255),(cx,cy),21,1)
            badge = (cx+23,cy-23)
            pygame.draw.circle(self.screen,(8,20,33),badge,14)
            pygame.draw.circle(self.screen,c,badge,12)
            number = self.font_md.render(str(i+1),True,(8,18,28))
            self.screen.blit(number,number.get_rect(center=badge))
            # Etiqueta desplazada de forma distinta para evitar colisiones
            # cuando las fronteras están muy cerca (p. ej. Polonia-Albania).
            label = f'{i+1}  {pais}'
            ancho = min(245,self.font_md.size(label)[0]+22)
            tx = max(self.MAP_X+7,min(self.MAP_X+self.MAP_W-ancho-7, cx-ancho//2))
            ty = cy-78 if i % 2 == 0 else cy+41
            if i == 2:
                ty = cy+54
            ty = max(72,min(self.MAP_H-65,ty))
            rect = pygame.Rect(tx,ty,ancho,29)
            pygame.draw.rect(self.screen,(8,24,40),rect,border_radius=7)
            pygame.draw.rect(self.screen,c,rect,2,border_radius=7)
            self._texto(label,tx+11,ty+6,self.font_md,C_TEXT,max_ancho=ancho-18)
            extremo = (max(tx+12,min(cx,tx+ancho-12)),ty+29 if ty<cy else ty)
            pygame.draw.line(self.screen,c,(cx,cy-30 if ty<cy else cy+30),extremo,2)

        # Información del territorio bajo el cursor o seleccionado con clic.
        mouse = pygame.mouse.get_pos()
        hover = self.pais_en_pos(mouse,juego.tablero) if self.MAP_X <= mouse[0] < self.MAP_X+self.MAP_W else None
        inspeccion = hover or pop.get('inspeccion')
        if inspeccion in juego.tablero:
            d = juego.tablero[inspeccion]
            propietario = d['propietario']
            nombre_j = (juego.jugadores[propietario].nombre if propietario is not None
                        else 'Territorio compartido')
            linea = (f'{inspeccion}   ·   {nombre_j}   ·   '
                     f'{d["ejercitos"]} ejércitos   ·   {d["misiles"]} misiles')
            info_x=self.MAP_X+18
            pygame.draw.rect(self.screen,(9,26,44),(info_x,74, min(945,max(390,self.font_md.size(linea)[0]+36)),37),border_radius=7)
            self._texto(linea,info_x+15,84,self.font_md,C_TEXT,max_ancho=920)

        # Las decisiones aparecen a la derecha, SIN velo oscuro sobre el mapa.
        x, y, w, h = self.PANEL_X+10, 112, self.PANEL_W-20, 638
        self._tarjeta((x,y,w,h),(17,35,55),(105,155,184),14)
        pygame.draw.rect(self.screen,C_ACCENT,(x+14,y+14,4,39),border_radius=2)
        self._texto('PROPUESTA DE PACTO',x+30,y+15,self.font_lg,C_ACCENT,max_ancho=w-43)
        self._texto(pop['titulo'],x+21,y+55,self.font_title,C_TEXT,max_ancho=w-43)
        self._texto('De: '+pop['proponente'],x+23,y+103,self.font_md,C_ACCENT2,max_ancho=w-45)
        pygame.draw.line(self.screen,C_PANEL_BORDER,(x+20,y+135),(x+w-20,y+135),1)

        top=y+154
        alto=91 if len(focos)==3 else 112
        for i,foco in enumerate(focos):
            c=colores[min(i,2)]
            r=pygame.Rect(x+17,top+i*alto,w-34,alto-9)
            pygame.draw.rect(self.screen,(25,51,73),r,border_radius=9)
            pygame.draw.rect(self.screen,c,r,1,border_radius=9)
            pygame.draw.circle(self.screen,c,(r.x+19,r.y+25),12)
            n=self.font_md.render(str(i+1),True,(8,18,28))
            self.screen.blit(n,n.get_rect(center=(r.x+19,r.y+25)))
            self._texto(foco['rol'],r.x+39,r.y+12,self.font_micro,C_TEXT_DIM,max_ancho=r.w-52)
            self._texto(foco['pais'],r.x+16,r.y+35,self.font_lg,C_TEXT,max_ancho=r.w-32)
            idx=foco['jugador']
            nombre_j=juego.jugadores[idx].nombre if idx is not None else 'Condominio'
            d=juego.tablero[foco['pais']]
            resumen=f'{nombre_j}  ·  {d["ejercitos"]} ej.  ·  {d["misiles"]} mis.'
            self._texto(resumen,r.x+17,r.y+64,self.font_sm,C_ACCENT2,max_ancho=r.w-32)

        mtop=top+len(focos)*alto+9
        for linea in self._ajustar_lineas(pop['mensaje'],self.font_sm,w-49)[:3]:
            self._texto(linea,x+22,mtop,self.font_sm,C_TEXT,max_ancho=w-44)
            mtop+=20
        self._texto('Acuerdo obligatorio si lo aceptás.',x+22,y+h-145,
                    self.font_sm,C_ACCENT,max_ancho=w-44)
        self._texto('El juego se detiene mientras decidís.',x+22,y+h-124,
                    self.font_sm,C_TEXT_DIM,max_ancho=w-44)

        ancho_b=(w-52)//2
        botones=[('ACEPTAR [A]','pacto_aceptar_bot',(32,111,103),C_SUCCESS),
                 ('RECHAZAR [R]','pacto_rechazar_bot',(79,49,56),C_DANGER)]
        for i,(nombre,accion,fondo,borde) in enumerate(botones):
            rect=pygame.Rect(x+18+i*(ancho_b+16),y+h-79,ancho_b,54)
            encima=rect.collidepoint(mouse)
            pygame.draw.rect(self.screen,fondo if not encima else C_BTN_HOVER,rect,border_radius=9)
            pygame.draw.rect(self.screen,borde,rect,2,border_radius=9)
            t=self.font_md.render(nombre,True,C_TEXT)
            self.screen.blit(t,t.get_rect(center=rect.center))
            pop['_btn_rects'].append((rect,accion))

    def abrir_menu_contextual(self, pais, posicion, juego):
        """Clic derecho: mismo conjunto de acciones que el panel lateral."""
        if pais is None or juego.jugador_actual().es_bot:return
        self.pais_objetivo=self.pais_objetivo if self.pais_objetivo!=pais else pais
        jugador=juego.turno_idx
        es_mio=juego.es_propietario(pais,jugador)
        fase=juego.fase
        items=[]
        if fase==FASE_INCORPORAR and es_mio:
            items=[('Incorporar +1','ctx_ref_1'),('Incorporar +3','ctx_ref_3'),
                   ('Incorporar +10','ctx_ref_10'),('Comprar misil (6)','ctx_misil_nuevo'),
                   ('Convertir 6 en misil','ctx_misil_convertir')]
        elif fase==FASE_ATACAR:
            if es_mio:
                items.append(('Elegir como origen','ctx_origen'))
            if self.pais_seleccionado and self.pais_seleccionado!=pais:
                self.pais_objetivo=pais
                if not es_mio or pais in juego.condominios:
                    items.extend([('Atacar con dados','atacar_4'),('Lanzar misil','lanzar_misil')])
                items.append(('Pactos con este país','ver_pactos'))
            else:
                items.append(('Pactos y diplomacia','ver_pactos'))
        elif fase==FASE_REAGRUPAR:
            if es_mio:items.append(('Elegir como origen','ctx_origen'))
            if self.pais_seleccionado and self.pais_seleccionado!=pais and es_mio:
                self.pais_objetivo=pais
                items.extend([('Mover ejércitos','reagrupar'),('Mover misil','reagrupar_misil')])
            items.append(('Pactos y diplomacia','ver_pactos'))
        else:
            items.append(('Pactos y diplomacia','ver_pactos'))
        if es_mio and fase!=FASE_INCORPORAR and not any(x[1]=='ctx_origen' for x in items):
            items.insert(0,('Elegir como origen','ctx_origen'))
        items.append(('Cerrar menú','ctx_cerrar'))
        self.menu_contextual={'pais':pais,'items':items,'pos':posicion,'rects':[]}

    def _dibujar_menu_contextual(self):
        m=self.menu_contextual
        x,y=m['pos'];ancho=246;alto=44+len(m['items'])*37
        x=max(self.MAP_X+8,min(x,self.MAP_X+self.MAP_W-ancho-8));y=max(8,min(y,self.MAP_H-alto-8))
        sombra=pygame.Rect(x+3,y+3,ancho,alto)
        pygame.draw.rect(self.screen,(7,17,28),sombra,border_radius=11)
        pygame.draw.rect(self.screen,(23,41,63),(x,y,ancho,alto),border_radius=11)
        pygame.draw.rect(self.screen,C_ACCENT2,(x,y,ancho,alto),1,border_radius=11)
        self._texto(m['pais'],x+12,y+11,self.font_md,C_ACCENT,max_ancho=ancho-24)
        m['rects']=[]
        for i,(texto,accion) in enumerate(m['items']):
            r=pygame.Rect(x+7,y+41+i*37,ancho-14,34)
            hover=r.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(self.screen,(44,73,100) if hover else (30,52,77),r,border_radius=6)
            self._texto(texto,r.x+12,r.y+9,self.font_sm,C_TEXT,max_ancho=r.width-19)
            m['rects'].append((r,accion))

    def click_menu_contextual(self,pos):
        m=self.menu_contextual
        if not m:return None
        respuesta=next((accion for r,accion in m.get('rects',[]) if r.collidepoint(pos)),None)
        self.menu_contextual=None
        return respuesta

    def mostrar_pactos(self,juego):
        """Acuerdos públicos, propuestas y rupturas desde el tablero."""
        a=0  # Los pactos se pueden consultar y romper fuera de turno.
        origen=self.pais_seleccionado
        destino=self.pais_objetivo
        vigente=[juego.descripcion_pacto(p) for p in juego.pactos_vigentes()]
        vigente += [f'ZONA #{z["id"]} · {z["pais"]}' for z in juego.zonas_internacionales if z['activa']]
        vigente += [f'AGRESIÓN #{ag["id"]} · {ag["destino"]} · {ag["estado"]}' for ag in juego.agresiones_pendientes if ag['estado'] in ('pendiente','pausada')]
        texto=('PACTOS VIGENTES:\n'+'\n'.join(vigente[-10:]) if vigente else 'No hay pactos vigentes.')
        otro=(juego.tablero[destino]['propietario'] if destino in juego.tablero else None)
        if origen in juego.tablero and destino in juego.tablero and juego.es_propietario(origen,a) and otro is not None and otro!=a:
            texto+=f'\n\nSelección: {origen} -> {destino} ({juego.jugadores[otro].color_nombre}).'
            botones=[('Entre países','pacto_pais'),('Continente','pacto_continente'),
                     ('Entre continentes','pacto_frontera'),('Mundial','pacto_mundial'),
                     ('Zona internac.','pacto_zona'),('Ataque conjunto','pacto_agresion'),
                     ('Romper pacto','pacto_romper_lista'),('Asaltos','pacto_asaltos'),('Cerrar','ok')]
        else:
            texto+='\n\nPara acordar: seleccioná tu país de origen y el país destino; luego P.'
            botones=[('No agresión mundial','pacto_mundial_lista'),('Romper pacto','pacto_romper_lista'),('Asaltos','pacto_asaltos'),('Cerrar','ok')]
        self.mostrar_popup('DIPLOMACIA Y PACTOS',texto,botones)

    def mostrar_historial(self, juego):
        """Listado ampliado; útil con 5-6 participantes cuando el panel se llena."""
        entradas=juego.historial[-23:]
        self.mostrar_popup('HISTORIAL DE LA PARTIDA','\n'.join(entradas) if entradas else 'No hay movimientos registrados.')

    def mostrar_objetivos(self, juego):
        """Lectura completa y sin recortes de las misiones secretas del humano."""
        j=juego.jugadores[0]
        objetivos=j.objetivos if hasattr(j,'objetivos') else [j.objetivo]
        mensajes=[f"OBJETIVO {n+1}: {o['descripcion']}" for n,o in enumerate(objetivos) if o]
        mensajes += ['Victoria alternativa: ocupar al menos 45 países.']
        self.popup = {'tipo':'objetivos', 'titulo':'TUS OBJETIVOS SECRETOS',
                      'objetivos':[o for o in objetivos if o], 'botones':[('CERRAR','ok')]}


    def _ajustar_lineas(self, texto, font, ancho):
        """Ajuste de texto por píxeles para popups, respetando saltos explícitos."""
        lineas=[]
        for parrafo in str(texto).split('\n'):
            if not parrafo:
                lineas.append('')
                continue
            partes=parrafo.split(' ')
            actual=''
            for palabra in partes:
                frase=(actual+' '+palabra).strip()
                if font.size(frase)[0] <= ancho:
                    actual=frase
                elif actual:
                    lineas.append(actual)
                    actual=palabra
                else:
                    # Palabra excepcionalmente larga, cortar por ancho.
                    segmento=''
                    for letra in palabra:
                        if font.size(segmento+letra)[0]>ancho and segmento:
                            lineas.append(segmento)
                            segmento=''
                        segmento+=letra
                    actual=segmento
            lineas.append(actual)
        return lineas

    def mostrar_popup_conquista(self, desde: str, hacia: str, max_pasar: int, disponibles: int):
        botones = []
        for i in range(1, max_pasar + 1):
            lbl = f"{i} Ejército" if i == 1 else f"{i} Ejércitos"
            botones.append((lbl, f"pasar_ejercitos_{i}"))

        titulo = "¡PAÍS CONQUISTADO!"
        mensaje = (f"Has conquistado {hacia} atacando desde {desde}.\n"
                   f"Disponibles en origen: {disponibles}. Mové entre 1 y {max_pasar}.\n"
                   f"¿Cuántos ejércitos deseas pasar a {hacia} en total?")
        self.mostrar_popup(titulo, mensaje, botones)

    def mostrar_popup_reagrupar(self, desde: str, hacia: str, maximo_disponible: int):
        # Guardar el estado para uso en el popup
        self._reagrupar_state = {
            "desde": desde,
            "hacia": hacia,
            "maximo_disponible": maximo_disponible,
            "cantidad_actual": 1  # Empezar con 1
        }

        titulo = "REAGRUPAR EJÉRCITOS"
        mensaje = (f"Mover ejércitos de {desde} a {hacia}.\n"
                   f"En {desde} hay {maximo_disponible + 1} ejércitos (debes dejar al menos 1).\n"
                   f"Selecciona la cantidad a mover:")

        # Crear botones de control
        botones = [
            ("-10", "reagrupar_ajustar_-10"),
            ("-1", "reagrupar_ajustar_-1"),
            ("+1", "reagrupar_ajustar_+1"),
            ("+10", "reagrupar_ajustar_+10"),
            ("Máx", "reagrupar_maximo"),
            ("Confirmar", "reagrupar_confirmar")
        ]

        self.mostrar_popup(titulo, mensaje, botones)

    def mostrar_popup_situacion(self, juego):
        """Aviso modal obligatorio una vez por ronda, antes de permitir acciones."""
        instrucciones={
            'Clásico':'Se aplican las reglas normales del combate.',
            'Nieve':'Los defensores disponen de un dado adicional, hasta cuatro.',
            'Viento a favor':'Los atacantes disponen de un dado adicional, hasta cuatro.',
            'Crisis':'Los jugadores que obtuvieron la tirada mínima del sorteo no pueden solicitar tarjeta de país esta ronda.',
            'Refuerzos extras':'Cada participante obtiene refuerzos adicionales según la mitad de sus países.',
            'Fronteras abiertas':'Solo se permite atacar entre países de continentes diferentes.',
            'Fronteras cerradas':'Solo se permite atacar entre países del mismo continente.',
        }
        detalle=instrucciones.get(juego.situacion,
            'El ejército indicado no puede atacar ni reagrupar durante esta ronda.')
        if juego.situacion=='Crisis' and juego.crisis_sin_tarjeta:
            detalle+='\nSin tarjeta: '+', '.join(juego.jugadores[i].nombre for i in sorted(juego.crisis_sin_tarjeta))+'.'
        self.popup={'tipo':'situacion','titulo':'TARJETA DE SITUACIÓN',
                    'situacion':juego.situacion, 'ronda':juego.ronda,
                    'mensaje':detalle, 'obligatorio':True,
                    'botones':[('ACEPTAR · INICIAR RONDA','ok')]}

    def _dibujar_popup_especial(self):
        pop=self.popup
        oscurecer=pygame.Surface((self.WIN_W,self.WIN_H),pygame.SRCALPHA)
        oscurecer.fill((4,10,20,211))
        self.screen.blit(oscurecer,(0,0))
        if pop.get('tipo')=='situacion':
            w,h=750,430
            x,y=(self.WIN_W-w)//2,(self.WIN_H-h)//2
            self._tarjeta((x,y,w,h),(20,37,56),(94,158,169),18)
            pygame.draw.rect(self.screen,C_ACCENT,(x+25,y+25,5,40),border_radius=3)
            self._texto('RONDA '+str(pop['ronda']),x+50,y+27,self.font_md,C_ACCENT2)
            self._texto('TARJETA DE SITUACIÓN',x+50,y+65,self.font_title,C_TEXT)
            pygame.draw.line(self.screen,C_PANEL_BORDER,(x+35,y+115),(x+w-35,y+115),2)
            pygame.draw.rect(self.screen,(40,72,90),(x+45,y+145,w-90,100),border_radius=14)
            self._texto(pop['situacion'].upper(),x+64,y+166,self.font_hero,C_ACCENT,max_ancho=w-128)
            lineas=self._ajustar_lineas(pop['mensaje'],self.font_lg,w-100)
            for i,linea in enumerate(lineas[:4]):
                self._texto(linea,x+48,y+263+i*27,self.font_md,C_TEXT,max_ancho=w-96)
            rect=pygame.Rect(x+190,y+h-69,w-380,44)
            pygame.draw.rect(self.screen,(30,130,137),rect,border_radius=11)
            pygame.draw.rect(self.screen,C_ACCENT2,rect,2,border_radius=11)
            self._texto('ACEPTAR · INICIAR RONDA',rect.x+47,rect.y+12,self.font_md,C_TEXT)
            pop['_btn_rects']=[(rect,'ok')]
            return
        # Cartas originales de objetivos, con gráfico en posición vertical correcta.
        objetivos=pop.get('objetivos',[])
        n=max(1,len(objetivos))
        w,h=(890 if n>1 else 695), (650 if n>1 else 680)
        x,y=(self.WIN_W-w)//2,(self.WIN_H-h)//2
        self._tarjeta((x,y,w,h),(19,36,54),(93,149,161),18)
        self._texto('MISIÓN SECRETA',x+32,y+21,self.font_micro,C_ACCENT2)
        self._texto('TUS OBJETIVOS',x+32,y+42,self.font_title,C_ACCENT)
        for i,obj in enumerate(objetivos):
            cardw=380 if n>1 else 585
            cardh=274 if n>1 else 420
            cx=x+(46+i*440 if n>1 else 55)
            cy=y+146 if n>1 else y+119
            self._texto('TARJETA '+str(i+1),cx,cy-30,self.font_md,C_ACCENT2)
            pygame.draw.rect(self.screen,(238,241,241),(cx-3,cy-3,cardw+6,cardh+6),border_radius=9)
            im=self.imagenes_objetivos.get(obj.get('tarjeta_id'))
            if im:
                ancho,alto=im.get_size()
                factor=min(cardw/ancho,cardh/alto)
                ww,hh=int(ancho*factor),int(alto*factor)
                imagen=pygame.transform.smoothscale(im,(ww,hh))
                self.screen.blit(imagen,(cx+(cardw-ww)//2,cy+(cardh-hh)//2))
            if obj['tipo']=='eliminacion':
                if 'objetivo_idx' in obj:
                    self._texto('OBJETIVO: '+str(obj['descripcion']),cx,cy+cardh+12,
                                self.font_sm,C_TEXT,max_ancho=cardw)
            else:
                self._texto('Objetivo de ocupación',cx,cy+cardh+13,self.font_sm,C_TEXT_DIM)
        self._texto('VICTORIA ALTERNATIVA: CONTROLAR 45 PAÍSES',x+32,y+h-104,
                    self.font_md,C_SUCCESS,max_ancho=w-70)
        rect=pygame.Rect(x+w//2-118,y+h-65,236,43)
        pygame.draw.rect(self.screen,(31,106,118),rect,border_radius=9)
        pygame.draw.rect(self.screen,C_ACCENT2,rect,2,border_radius=9)
        text=self.font_md.render('CERRAR TARJETAS',True,C_TEXT)
        self.screen.blit(text,text.get_rect(center=rect.center))
        pop['_btn_rects']=[(rect,'ok')]

    def _dibujar_popup(self, juego):
        if not self.popup:return
        if self.popup.get('tipo') == 'pacto_propuesta':
            self._dibujar_popup_pacto(juego)
            return
        if self.popup.get('tipo') in ('situacion','objetivos'):
            self._dibujar_popup_especial()
            return
        w=700
        lineas=self._ajustar_lineas(self.popup['mensaje'],self.font_md,w-55)
        filas_botones=(len(self.popup['botones'])+3)//4
        h=max(242,min(self.WIN_H-96,112+len(lineas)*25+max(1,filas_botones)*46))
        x,y=(self.WIN_W-w)//2,(self.WIN_H-h)//2
        oscurecer=pygame.Surface((self.WIN_W,self.WIN_H),pygame.SRCALPHA)
        oscurecer.fill((5,11,22,190))
        self.screen.blit(oscurecer,(0,0))
        self._tarjeta((x,y,w,h),(20,36,55),(96,147,164),16)
        pygame.draw.rect(self.screen,C_ACCENT,(x+17,y+17,4,32),border_radius=2)
        titulo=self.font_xl.render(self.popup['titulo'],True,C_ACCENT)
        self.screen.blit(titulo,(x+35,y+18))
        pygame.draw.line(self.screen,C_PANEL_BORDER,(x+20,y+62),(x+w-20,y+62),1)
        txt_y=y+75
        for linea in lineas:
            self._texto(linea,x+28,txt_y,self.font_md,C_TEXT,max_ancho=w-54)
            txt_y+=25
            if txt_y>=y+h-18-max(1,filas_botones)*46:break

        botones=self.popup['botones']
        n=len(botones)
        columnas=min(4,n)
        filas=(n+columnas-1)//columnas
        gap=9
        bw=min(154,(w-44-(columnas-1)*gap)//columnas)
        total=columnas*bw+(columnas-1)*gap
        bx=x+(w-total)//2
        by=y+h-16-filas*46
        self.popup['_btn_rects']=[]
        cursor=pygame.mouse.get_pos()
        for i,(nombre,accion) in enumerate(botones):
            rect=pygame.Rect(bx+(i%columnas)*(bw+gap),by+(i//columnas)*46,bw,39)
            encima=rect.collidepoint(cursor)
            pygame.draw.rect(self.screen,C_BTN_HOVER if encima else C_BTN_NORMAL,rect,border_radius=9)
            pygame.draw.rect(self.screen,C_ACCENT if encima else C_PANEL_BORDER,rect,2 if encima else 1,border_radius=9)
            f=self.font_md if len(nombre)<15 else self.font_sm
            text=f.render(nombre,True,C_TEXT)
            self.screen.blit(text,text.get_rect(center=rect.center))
            self.popup['_btn_rects'].append((rect,accion))

    def click_popup(self, pos) -> str | None:
        """Retorna la accion si se hizo clic en un boton del popup."""
        if not self.popup or "_btn_rects" not in self.popup:
            return None
        for rect, act in self.popup["_btn_rects"]:
            if rect.collidepoint(pos):
                self.popup = None
                return act
        return None

    # ─── Utilidades UI ──────────────────────────────────────────────

    def pais_en_pos(self, pos, tablero) -> str | None:
        """Detecta el pais mas cercano al clic (radio de tolerancia)."""
        mx, my = pos
        if mx < self.MAP_X or mx >= self.MAP_X + self.MAP_W:
            return None
        mejor = None
        mejor_dist = self.RADIO_TOKEN + 8
        for nombre, datos in tablero.items():
            cx, cy = self._escalar_coords(datos["coords"])
            dist = math.hypot(mx - cx, my - cy)
            if dist < mejor_dist:
                mejor_dist = dist
                mejor = nombre
        return mejor

    def update_hover(self, pos):
        for btn in self.botones:
            btn.check_hover(pos)

    def pantalla_menu(self):
        """Portada con el mapa original, colores oficiales y configuración clara."""
        opciones=(2,3,4,5,6)
        seleccion=4
        color_humano=0
        permitir_destruccion=True
        animaciones=True
        running=True
        mapa_portada=pygame.transform.smoothscale(self.mapa,(750,563))
        while running:
            self.screen.fill(C_BG)
            # Rayas decorativas muy tenues en fondo.
            for y in range(0,self.WIN_H,55):
                pygame.draw.line(self.screen,(16,29,45),(0,y),(self.WIN_W,y),1)
            self._texto('ESTRATEGIA  ·  CONQUISTA  ·  REVANCHA',72,55,
                        self.font_md,C_ACCENT2)
            self._texto('TEG',72,83,self.font_hero,C_ACCENT)
            self._texto('LA REVANCHA',187,94,self.font_xl,C_TEXT)
            self._texto('El mundo es tu tablero. Elegí tu ejército.',74,139,
                        self.font_lg,C_TEXT_DIM)
            self._tarjeta((69,189,763,587),(24,43,63),(78,115,128),16)
            self.screen.blit(mapa_portada,(76,195))
            # Tope y pie del mapa como cartela, sin ocultar la geografía central.
            pygame.draw.rect(self.screen,(18,35,53),(75,728,750,48))
            self._texto('72 PAÍSES',95,743,self.font_md,C_ACCENT)
            self._texto('7 CONTINENTES',271,743,self.font_md,C_TEXT)
            self._texto('1 OBJETIVO: LA VICTORIA',497,743,self.font_md,C_ACCENT2)

            dx,dy,dw,dh=862,190,660,587
            self._tarjeta((dx,dy,dw,dh),(20,36,55),(57,83,108),16)
            self._texto('PREPARÁ TU PARTIDA',dx+29,dy+23,self.font_xl,C_TEXT)
            self._texto('1 jugador humano + adversarios controlados por IA',
                        dx+29,dy+62,self.font_sm,C_TEXT_DIM)
            pygame.draw.line(self.screen,C_PANEL_BORDER,(dx+29,dy+91),(dx+dw-29,dy+91),1)
            self._texto('CANTIDAD DE PARTICIPANTES',dx+29,dy+111,self.font_micro,C_ACCENT2)
            btn_rects=[]
            bx=dx+29
            for n in opciones:
                rect=pygame.Rect(bx,dy+138,106,59)
                elegido=(n==seleccion)
                pygame.draw.rect(self.screen,(49,90,113) if elegido else (33,56,78),rect,border_radius=10)
                pygame.draw.rect(self.screen,C_ACCENT if elegido else C_PANEL_BORDER,
                                 rect,2 if elegido else 1,border_radius=10)
                text=self.font_xl.render(str(n),True,C_TEXT)
                self.screen.blit(text,text.get_rect(center=rect.center))
                btn_rects.append((rect,n))
                bx+=120
            self._texto('COLOR DE TUS EJÉRCITOS',dx+29,dy+222,self.font_micro,C_ACCENT2)
            colores_rect=[]
            for ci,nom in enumerate(COLORES_OFICIALES):
                bx=dx+29+ci*100
                rect=pygame.Rect(bx,dy+249,91,88)
                elegido=(ci==color_humano)
                pygame.draw.rect(self.screen,(48,78,97) if elegido else (32,53,73),rect,border_radius=9)
                pygame.draw.rect(self.screen,C_ACCENT if elegido else C_PANEL_BORDER,
                                 rect,2 if elegido else 1,border_radius=9)
                pygame.draw.circle(self.screen,PLAYER_COLORS[ci],(bx+45,dy+281),18)
                pygame.draw.circle(self.screen,(224,235,243),
                                   (bx+45,dy+281),18,2 if ci==1 else 1)
                nombre=self.font_micro.render(nom,True,C_TEXT)
                self.screen.blit(nombre,nombre.get_rect(center=(bx+45,dy+320)))
                colores_rect.append((rect,ci))
            self._texto('ORDEN ALEATORIO • TODOS INCORPORAN ANTES DE ATACAR',
                        dx+29,dy+347,self.font_micro,C_TEXT_DIM)
            check_rect=pygame.Rect(dx+29,dy+372,dw-58,52)
            pygame.draw.rect(self.screen,(33,57,78),check_rect,border_radius=10)
            pygame.draw.rect(self.screen,C_ACCENT2 if permitir_destruccion else C_PANEL_BORDER,
                             check_rect,2 if permitir_destruccion else 1,border_radius=10)
            cuadrado=pygame.Rect(check_rect.x+12,check_rect.y+13,26,26)
            pygame.draw.rect(self.screen,C_SUCCESS if permitir_destruccion else (30,44,59),cuadrado,border_radius=5)
            self._texto('✓' if permitir_destruccion else ' ',cuadrado.x+4,cuadrado.y+1,
                        self.font_lg,(12,35,42))
            self._texto('INCLUIR OBJETIVOS DE DESTRUCCIÓN',check_rect.x+50,check_rect.y+7,
                        self.font_md,C_TEXT)
            self._texto('Solo afecta partidas de 4 a 6 jugadores',check_rect.x+50,check_rect.y+29,
                        self.font_micro,C_TEXT_DIM)
            anim_rect=pygame.Rect(dx+29,dy+431,dw-58,52)
            pygame.draw.rect(self.screen,(33,57,78),anim_rect,border_radius=10)
            pygame.draw.rect(self.screen,C_ACCENT2 if animaciones else C_PANEL_BORDER,
                             anim_rect,2 if animaciones else 1,border_radius=10)
            cuadrado2=pygame.Rect(anim_rect.x+12,anim_rect.y+13,26,26)
            pygame.draw.rect(self.screen,C_SUCCESS if animaciones else (30,44,59),cuadrado2,border_radius=5)
            self._texto('✓' if animaciones else ' ',cuadrado2.x+4,cuadrado2.y+1,
                        self.font_lg,(12,35,42))
            self._texto('MOSTRAR ANIMACIONES Y EVENTOS VISUALES',anim_rect.x+50,anim_rect.y+7,
                        self.font_md,C_TEXT)
            self._texto('Ataques, refuerzos, reagrupes y canjes visibles',anim_rect.x+50,anim_rect.y+29,
                        self.font_micro,C_TEXT_DIM)
            jugar_rect=pygame.Rect(dx+29,dy+498,dw-58,58)
            hover=jugar_rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(self.screen,(38,136,139) if hover else (28,106,114),jugar_rect,border_radius=12)
            pygame.draw.rect(self.screen,C_ACCENT2,jugar_rect,2,border_radius=12)
            start_txt=self.font_lg.render('COMENZAR PARTIDA   →',True,C_TEXT)
            self.screen.blit(start_txt,start_txt.get_rect(center=jugar_rect.center))
            self._texto('CONTROLES',dx+29,dy+571,self.font_micro,C_ACCENT)
            self._texto('Clic: países y acciones    •    T: cartas    •    O: objetivos',
                        dx+29,dy+593,self.font_sm,C_TEXT_DIM,max_ancho=dw-53)
            self._texto('F: bots    •    H: historial    •    Espacio: fase    •    ESC: salir',
                        dx+29,dy+617,self.font_sm,C_TEXT_DIM,max_ancho=dw-53)
            self._texto('TEG LA REVANCHA  |  PYGAME  |  MODO LOCAL',72,812,
                        self.font_micro,C_TEXT_DIM)
            self._texto('Reglas y mapa del material oficial proporcionado',72,834,
                        self.font_sm,C_TEXT_DIM)
            pygame.display.flip()
            self.clock.tick(60)
            for ev in pygame.event.get():
                if ev.type==pygame.QUIT:
                    pygame.quit()
                    import sys;sys.exit()
                if ev.type==pygame.MOUSEBUTTONDOWN and ev.button==1:
                    for rect,n in btn_rects:
                        if rect.collidepoint(ev.pos):seleccion=n
                    for rect,i in colores_rect:
                        if rect.collidepoint(ev.pos):color_humano=i
                    if check_rect.collidepoint(ev.pos):permitir_destruccion=not permitir_destruccion
                    if anim_rect.collidepoint(ev.pos):animaciones=not animaciones
                    if jugar_rect.collidepoint(ev.pos):running=False
                if ev.type==pygame.KEYDOWN and ev.key==pygame.K_RETURN:
                    running=False
        return seleccion,color_humano,permitir_destruccion,animaciones
