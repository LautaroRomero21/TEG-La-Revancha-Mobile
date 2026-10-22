"""TEG La Revancha Android v16 · interfaz nativa táctil Kivy.

El motor en engine/ es una copia sin modificaciones de la v16 de Pygame.
Ejecutar: python main.py   |   Compilar: buildozer android debug
"""

__version__ = "0.1.0"

import math
import time
from pathlib import Path

from kivy.config import Config

Config.set("graphics", "minimum_width", "860")
Config.set("graphics", "minimum_height", "470")
from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.text import Label as CoreLabel
from kivy.graphics import Color, Rectangle, RoundedRectangle, Ellipse, Line
from kivy.metrics import dp
from kivy.properties import ObjectProperty
from kivy.uix.widget import Widget
from kivy.uix.scatter import Scatter
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.stencilview import StencilView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.image import Image
from kivy.core.window import Window

from controller import ControlMovil, COLORES_OFICIALES, PAISES_DATA

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
BG = (0.045, 0.074, 0.115, 1)
PANEL = (0.075, 0.119, 0.176, 0.97)
BTN = (0.13, 0.205, 0.285, 1)
GOLD = (1, 0.74, 0.32, 1)
INK = (0.92, 0.96, 1, 1)
SOFT = (0.64, 0.73, 0.82, 1)


def etiqueta(texto="", tam=15, color=INK, **kwargs):
    # La pantalla puede sobrescribir la alineacion sin duplicar keywords.
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    l = Label(
        text=str(texto),
        font_size=dp(tam),
        color=color,
        **kwargs,
    )
    l.bind(size=lambda w, _: setattr(w, "text_size", w.size))
    return l


def boton(texto, callback, color=BTN, altura=43):
    b = Button(
        text=str(texto),
        size_hint_y=None,
        height=dp(altura),
        background_normal="",
        background_color=color,
        color=INK,
        font_size=dp(14),
        bold=True,
    )
    b.bind(on_release=lambda *_: callback())
    return b


def sombrear(widget, rgba=BG):
    with widget.canvas.before:
        Color(*rgba)
        fondo = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(
        pos=lambda _, p: setattr(fondo, "pos", p),
        size=lambda _, s: setattr(fondo, "size", s),
    )


class SuperficieMapa(Widget):
    """Mapa original + fichas dibujadas juntas en canvas, no 72 widgets."""

    def __init__(self, controller, **kw):
        super().__init__(**kw)
        self.size_hint = (None, None)
        self.size = (1200, 900)
        self.c = controller
        self.img = CoreImage(str(ASSETS / "mapa_ui.jpg")).texture
        self.texturas = {}
        self._estado = None
        self.comienzo_fx = 0
        self.anterior_fx = None
        self.renderizar()

    @staticmethod
    def coord(pais):
        x, y = PAISES_DATA[pais]["coords"]
        # Coordenadas del juego PC en 1280x960, origen arriba a la izquierda.
        return x * 1200 / 1280, 900 - y * 900 / 960

    def pais_cercano(self, x, y, radio=24):
        candidatos = sorted(
            (
                (math.hypot(x - px, y - py), p)
                for p in PAISES_DATA
                for px, py in [self.coord(p)]
            )
        )
        # Radio deliberadamente más amplio que el token; pinch para países juntos.
        if candidatos and candidatos[0][0] <= radio:
            return candidatos[0][1]
        return None

    def textura(self, texto, tam=17, color=(1, 1, 1, 1)):
        llave = (str(texto), tam, tuple(color))
        if llave not in self.texturas:
            lbl = CoreLabel(text=str(texto), font_size=tam, bold=True, color=color)
            lbl.refresh()
            self.texturas[llave] = lbl.texture
        return self.texturas[llave]

    def dibujar_texto(self, texto, x, y, tam=17, color=(1, 1, 1, 1)):
        t = self.textura(texto, tam, color)
        Rectangle(texture=t, size=t.size, pos=(x - t.width / 2, y - t.height / 2))

    def renderizar(self):
        j = self.c.juego
        if self.c.fx is not self.anterior_fx:
            self.anterior_fx = self.c.fx
            self.comienzo_fx = time.monotonic()
        diff = time.monotonic() - self.comienzo_fx
        with self.canvas:
            self.canvas.clear()
            Color(1, 1, 1, 1)
            Rectangle(texture=self.img, pos=(0, 0), size=(1200, 900))
            # Pactos sobre países específicos, zonas y propuestas obligatorias.
            pactados = {
                p
                for ac in j.pactos_vigentes()
                if ac["tipo"] == "pais"
                for p in ac.get("paises", ())
            }
            pactados.update(z["pais"] for z in j.zonas_internacionales if z["activa"])
            propuesta = j.propuesta_pendiente or {}
            focos = (
                list(propuesta.get("paises", ()))
                if propuesta.get("tipo") == "pais"
                else [
                    propuesta[k]
                    for k in ("origen_a", "origen_b", "destino")
                    if k in propuesta
                ]
            )
            # Dibujar ficha por país. Los condominios conservan ambos colores.
            for p, d in j.tablero.items():
                x, y = self.coord(p)
                due = d["propietario"]
                if p in j.condominios:
                    idxs = list(j.condominios[p])
                    col1 = tuple(v / 255 for v in j.jugadores[idxs[0]].color[:3])
                    col2 = tuple(v / 255 for v in j.jugadores[idxs[-1]].color[:3])
                else:
                    col1 = (
                        (0.54, 0.59, 0.62)
                        if due is None
                        else tuple(v / 255 for v in j.jugadores[due].color)
                    )
                    col2 = col1
                if (
                    self.c.fx
                    and self.c.fx.get("tipo") == "ataque"
                    and p == self.c.fx.get("destino")
                    and diff < 0.9
                ):
                    r = self.c.fx.get("resultado") or {}
                    anterior = r.get("defensor_anterior_idx")
                    if anterior is not None:
                        col1 = tuple(v / 255 for v in j.jugadores[anterior].color)
                        col2 = col1
                Color(0.015, 0.033, 0.06, 0.95)
                Ellipse(pos=(x - 17.8, y - 17.8), size=(35.6, 35.6))
                Color(*col1, 1)
                Ellipse(pos=(x - 15.2, y - 15.2), size=(30.4, 30.4))
                if col1 != col2:
                    Color(*col2, 1)
                    Line(points=[x - 10, y - 11, x + 11, y + 10], width=3)
                if p in pactados:
                    Color(0.16, 0.86, 0.76, 0.9)
                    Line(circle=(x, y, 21), width=1.4)
                if p in focos:
                    Color(0.29, 0.91, 1, 1)
                    Line(circle=(x, y, 25), width=3.2)
                    self.dibujar_texto(
                        str(focos.index(p) + 1), x, y + 32, 17, (0.1, 0.52, 0.9, 1)
                    )
                if self.c.origen == p:
                    Color(1, 0.82, 0.22, 1)
                    Line(circle=(x, y, 20), width=2.4)
                elif self.c.destino == p:
                    Color(0.4, 0.87, 1, 1)
                    Line(circle=(x, y, 20), width=2.4)
                elif self.c.inspeccion == p:
                    Color(0.84, 0.95, 1, 0.75)
                    Line(circle=(x, y, 20), width=1.1)
                cantidad = str(d["ejercitos"])
                tcolor = (
                    (0.045, 0.055, 0.075, 1) if sum(col1[:3]) > 1.85 else (1, 1, 1, 1)
                )
                Color(1, 1, 1, 1)
                self.dibujar_texto(cantidad, x, y + 1, 17, tcolor)
                if d["misiles"]:
                    Color(0.02, 0.03, 0.04, 0.95)
                    RoundedRectangle(pos=(x + 8, y - 21), size=(21, 14), radius=[4])
                    Color(1, 0.82, 0.3, 1)
                    self.dibujar_texto("M" + str(d["misiles"]), x + 18.5, y - 14, 10)
                if p in j.condominios:
                    Color(0.13, 0.15, 0.16, 1)
                    RoundedRectangle(pos=(x - 26, y + 15), size=(53, 13), radius=[3])
                    Color(1, 1, 1, 1)
                    detalle = "/".join(str(n) for n in j.condominios[p].values())
                    self.dibujar_texto(detalle, x, y + 22, 10)
            # Línea temporal de ataques, misiles y movimientos sobre el mapa.
            fx = self.c.fx
            if self.c.animaciones and fx and diff < 1.65:
                p, q = fx.get("origen"), fx.get("destino")
                if p in PAISES_DATA:
                    x, y = self.coord(p)
                    pulso = 21 + 8 * abs(math.sin(diff * 8))
                    Color(1, 0.78, 0.25, max(0.08, 1 - diff / 1.65))
                    Line(circle=(x, y, pulso), width=2.8)
                    if q in PAISES_DATA:
                        X, Y = self.coord(q)
                        Color(1, 0.56, 0.28, max(0.05, 1 - diff / 1.65))
                        Line(points=[x, y, X, Y], width=2.7)
                        Line(circle=(X, Y, pulso), width=2.5)
                        t = min(1, diff / 1.0)
                        Color(1, 1, 0.6, 1)
                        Ellipse(
                            pos=(x + (X - x) * t - 4, y + (Y - y) * t - 4), size=(8, 8)
                        )


class TableroTactil(Scatter):
    """Dos dedos amplían/reducen, uno arrastra. Un toque corto selecciona."""

    def __init__(self, surface, callback, **kw):
        super().__init__(**kw)
        self.do_rotation = False
        self.do_scale = True
        self.do_translation = True
        self.scale_min = 0.23
        self.scale_max = 3.8
        self.auto_bring_to_front = False
        self.size_hint = (None, None)
        self.size = (1200, 900)
        self.add_widget(surface)
        self._inicios = {}
        self._callback = callback
        self._multitouch = False

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._inicios[touch.uid] = (touch.pos[:], time.monotonic())
            if len(self._inicios) > 1:
                self._multitouch = True
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        inicio = self._inicios.pop(touch.uid, None)
        if inicio:
            cx, cy = touch.pos
            x, y = self.to_local(cx, cy)
            if (
                not self._multitouch
                and math.dist(inicio[0], (cx, cy)) < dp(14)
                and time.monotonic() - inicio[1] < 0.65
            ):
                self._callback(x, y)
        if not self._inicios:
            self._multitouch = False
        return super().on_touch_up(touch)


class PantallaInicio(BoxLayout):
    def __init__(self, iniciar, **kw):
        super().__init__(orientation="vertical", spacing=dp(14), padding=dp(15), **kw)
        sombrear(self)
        self.add_widget(
            etiqueta(
                "TEG  ·  LA REVANCHA",
                tam=33,
                color=GOLD,
                halign="center",
                size_hint_y=None,
                height=dp(60),
                bold=True,
            )
        )
        self.add_widget(
            etiqueta(
                "Versión Android · Offline · 1 humano contra bots",
                tam=15,
                color=SOFT,
                halign="center",
                size_hint_y=None,
                height=dp(24),
            )
        )
        centro = BoxLayout(spacing=dp(20))
        previa = Image(
            source=str(ASSETS / "mapa_ui.jpg"), allow_stretch=True, keep_ratio=True
        )
        centro.add_widget(previa)
        panel = BoxLayout(
            orientation="vertical",
            spacing=dp(12),
            padding=[dp(10), 0, dp(10), 0],
            size_hint_x=0.42,
        )
        panel.add_widget(
            etiqueta(
                "Configuración de partida",
                tam=21,
                color=GOLD,
                size_hint_y=None,
                height=dp(38),
            )
        )
        panel.add_widget(
            etiqueta("Jugadores (incluido vos)", size_hint_y=None, height=dp(22))
        )
        jugadores = Spinner(
            text="4",
            values=[str(i) for i in range(2, 7)],
            size_hint_y=None,
            height=dp(46),
        )
        panel.add_widget(jugadores)
        panel.add_widget(
            etiqueta("Color de tu ejército", size_hint_y=None, height=dp(22))
        )
        color = Spinner(
            text="Blanco", values=COLORES_OFICIALES, size_hint_y=None, height=dp(46)
        )
        panel.add_widget(color)
        line1 = BoxLayout(size_hint_y=None, height=dp(36))
        ch_eliminar = CheckBox(active=True, size_hint_x=None, width=dp(50))
        line1.add_widget(ch_eliminar)
        line1.add_widget(etiqueta("Incluir objetivos de destrucción", tam=13))
        panel.add_widget(line1)
        line2 = BoxLayout(size_hint_y=None, height=dp(36))
        ch_anim = CheckBox(active=True, size_hint_x=None, width=dp(50))
        line2.add_widget(ch_anim)
        line2.add_widget(etiqueta("Activar animaciones", tam=13))
        panel.add_widget(line2)
        panel.add_widget(
            boton(
                "COMENZAR PARTIDA",
                lambda: iniciar(
                    int(jugadores.text),
                    COLORES_OFICIALES.index(color.text),
                    ch_eliminar.active,
                    ch_anim.active,
                ),
                color=(0.15, 0.44, 0.34, 1),
                altura=52,
            )
        )
        panel.add_widget(
            etiqueta(
                "Modo horizontal · sin cuentas ni permisos de Internet",
                tam=12,
                color=SOFT,
            )
        )
        centro.add_widget(panel)
        self.add_widget(centro)


class VistaJuego(BoxLayout):
    """Tablero amplio a la izquierda y todos los mandos a la derecha."""

    def __init__(self, c, **kw):
        super().__init__(
            orientation="horizontal", spacing=dp(6), padding=dp(5), **kw
        )
        self.c = c
        sombrear(self)

        # La zona izquierda recorta el mapa al desplazar o ampliar.
        self.zona_mapa = StencilView(size_hint=(1, 1))
        sombrear(self.zona_mapa)
        self.mapa = SuperficieMapa(c)
        self.scatter = TableroTactil(self.mapa, self._pais_tocado)
        self.zona_mapa.add_widget(self.scatter)
        self.add_widget(self.zona_mapa)
        self._posicionado = False
        self.zona_mapa.bind(size=self.ajustar_mapa)

        # Barra derecha fija, fuera de la superficie tactil del mapa.
        self.lateral = BoxLayout(
            orientation="vertical", size_hint=(None, 1),
            spacing=dp(5), padding=[dp(7), dp(6)]
        )
        sombrear(self.lateral, (0.075, 0.119, 0.176, 1))
        self.add_widget(self.lateral)
        self.bind(size=self.ajustar_ancho_lateral)
        self.ajustar_ancho_lateral()

        self.hud = BoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(69)
        )
        self.texto_hud = etiqueta("", tam=14)
        self.hud.add_widget(self.texto_hud)
        self.lateral.add_widget(self.hud)

        herramientas = BoxLayout(
            orientation="horizontal", size_hint_y=None,
            height=dp(45), spacing=dp(4)
        )
        herramientas.add_widget(boton("ESTADO", self.abrir_panel, altura=43))
        herramientas.add_widget(
            boton("OBJETIVO", lambda: self.abrir_accion("objetivos"), altura=43)
        )
        herramientas.add_widget(
            boton("CARTAS", lambda: self.abrir_accion("tarjetas"), altura=43)
        )
        self.lateral.add_widget(herramientas)

        self.titulo_turnos = etiqueta(
            "ORDEN DE TURNOS", tam=14, color=GOLD,
            size_hint_y=None, height=dp(24), bold=True
        )
        self.lateral.add_widget(self.titulo_turnos)
        self.lista_turnos = BoxLayout(
            orientation="vertical", size_hint_y=None, spacing=dp(2)
        )
        self.lateral.add_widget(self.lista_turnos)

        # Los botones de fase y los dialogos comparten esta columna;
        # no se superponen al tablero. En pantallas bajas hay scroll.
        self.cuerpo_lateral = BoxLayout(orientation="vertical")
        self.lateral.add_widget(self.cuerpo_lateral)
        self.acciones = BoxLayout(
            orientation="vertical", size_hint_y=None,
            spacing=dp(6), padding=[dp(2), dp(4)]
        )
        self.acciones.bind(minimum_height=self.acciones.setter("height"))
        self.scroll_acciones = ScrollView(do_scroll_x=False)
        self.scroll_acciones.add_widget(self.acciones)
        self.cuerpo_lateral.add_widget(self.scroll_acciones)

        self.cajon = None
        self.modo_panel = "normal"
        self._ultima_ui = None
        self._ultimo_dialogo = None
        self._ultimo_estado = None
        self._ultima_orden = None
        self._ultima_actualizacion = 0
        self._ultimo_paso = time.monotonic()
        self.actualizar_orden_turnos()
        Clock.schedule_interval(self.actualizar, 1 / 24)
        Clock.schedule_once(lambda _dt: self.ajustar_mapa(), 0)

    def ajustar_ancho_lateral(self, *_):
        # Mantener al mapa la mayor parte de la pantalla.
        self.lateral.width = min(
            self.width * 0.44, max(self.width * 0.34, dp(220))
        )

    def ajustar_mapa(self, *_):
        if self._posicionado or self.zona_mapa.width < 200 or self.zona_mapa.height < 180:
            return
        escala = min(self.zona_mapa.width / 1200, self.zona_mapa.height / 900) * 0.98
        self.scatter.scale = escala
        self.scatter.center = (
            self.zona_mapa.width / 2,
            self.zona_mapa.height / 2
        )
        self._posicionado = True

    def actualizar_orden_turnos(self):
        j = self.c.juego
        orden = j.orden_visual_jugadores()
        firma = (
            j.ronda, tuple(orden), j.turno_idx,
            tuple((len(j.paises_de(i)), j.jugadores[i].eliminado) for i in orden),
        )
        if firma == self._ultima_orden:
            return
        self._ultima_orden = firma
        self.titulo_turnos.text = (
            f"ORDEN · RONDA {j.ronda}" if j.ronda else "ORDEN · PREPARACIÓN"
        )
        self.lista_turnos.clear_widgets()
        for puesto, idx in enumerate(orden, 1):
            jugador = j.jugadores[idx]
            actual = idx == j.turno_idx
            fila = BoxLayout(
                orientation="horizontal", size_hint_y=None,
                height=dp(28), spacing=dp(7), padding=[dp(5), 0]
            )
            if actual:
                sombrear(fila, (0.16, 0.28, 0.38, 1))
            muestra = Widget(size_hint=(None, 1), width=dp(14))
            with muestra.canvas:
                rgb = tuple(v / 255 for v in jugador.color[:3])
                Color(*rgb, 1)
                figura = RoundedRectangle(
                    pos=(muestra.x, muestra.y + dp(7)),
                    size=(dp(13), dp(13)), radius=[dp(3)]
                )
            muestra.bind(
                pos=lambda w, _p, f=figura: setattr(
                    f, "pos", (w.x, w.y + dp(7))
                )
            )
            fila.add_widget(muestra)
            estado = " · FUERA" if jugador.eliminado else ""
            aviso = "  ◀ AHORA" if actual else ""
            fila.add_widget(etiqueta(
                f"{puesto}. {jugador.nombre} · {len(j.paises_de(idx))} países"
                f"{estado}{aviso}",
                tam=12, color=GOLD if actual else SOFT,
                shorten=True, shorten_from="right"
            ))
            self.lista_turnos.add_widget(fila)
        self.lista_turnos.height = len(orden) * dp(30)

    def _pais_tocado(self, x, y):
        p = self.mapa.pais_cercano(
            x, y, radio=max(24, dp(23) / max(0.2, self.scatter.scale))
        )
        if p:
            estaba_en_pactos = bool(
                self.c.dialogo and self.c.dialogo["kind"] == "pactos"
            )
            self.c.tocar_pais(p)
            self._ultima_ui = None
            # No obligar a cerrar un panel cada vez que se toca una ficha.
            # Si el usuario estaba negociando, refrescar las opciones de pacto.
            if estaba_en_pactos:
                self.c.ver_pactos()
            elif self.c.dialogo and self.c.dialogo["kind"] == "propuesta_bot":
                self._llenar_panel()
            elif self.cajon and self.modo_panel == "pais":
                self._llenar_panel()

    def abrir_accion(self, accion):
        if self.c.dialogo and self.c.dialogo["obligatorio"]:
            return
        self.c.accion(accion)
        self._abrir_si_dialogo()
        self._ultima_ui = None

    def _abrir_si_dialogo(self):
        if self.c.dialogo:
            self.abrir_panel("dialogo")

    def elegir(self, codigo):
        # Al ingresar una decisión, el controlador valida contra el motor.
        anterior = self.c.dialogo
        self.c.procesar_opcion(codigo)
        if self.c.dialogo:
            self.abrir_panel("dialogo")
        elif anterior:
            self.cerrar_panel()
        self._ultimo_dialogo = None
        self._ultima_ui = None

    def abrir_panel(self, modo="normal"):
        if self.c.dialogo:
            modo = "dialogo"
        if self.cajon:
            self.cuerpo_lateral.remove_widget(self.cajon)
        else:
            self.cuerpo_lateral.remove_widget(self.scroll_acciones)
        self.cajon = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            padding=[dp(5), dp(5)]
        )
        sombrear(self.cajon, PANEL)
        cabeza = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
        self.titulo_cajon = etiqueta("DETALLE", tam=16, color=GOLD)
        cabeza.add_widget(self.titulo_cajon)
        cabeza.add_widget(boton("CERRAR", self.cerrar_panel, altura=36))
        self.cajon.add_widget(cabeza)
        self.scroll = ScrollView(do_scroll_x=False)
        self.contenido = BoxLayout(
            orientation="vertical",
            size_hint_y=None, spacing=dp(7),
            padding=[0, 0, dp(7), dp(10)]
        )
        self.contenido.bind(minimum_height=self.contenido.setter("height"))
        self.scroll.add_widget(self.contenido)
        self.cajon.add_widget(self.scroll)
        self.cuerpo_lateral.add_widget(self.cajon)
        self.modo_panel = modo
        self._llenar_panel()

    def cerrar_panel(self, *_):
        if self.c.dialogo and self.c.dialogo["obligatorio"]:
            return
        if self.cajon:
            self.cuerpo_lateral.remove_widget(self.cajon)
            self.cajon = None
            self.cuerpo_lateral.add_widget(self.scroll_acciones)
        if self.c.dialogo:
            self.c.cerrar_dialogo()
        self._ultimo_dialogo = None

    def _agregar_texto(self, texto, tam=14, color=INK, alto=None):
        n = max(1, len(str(texto)) // 37 + str(texto).count("\n") + 1)
        lbl = etiqueta(
            texto,
            tam=tam,
            color=color,
            size_hint_y=None,
            height=dp(alto or max(31, n * 25)),
        )
        self.contenido.add_widget(lbl)
        return lbl

    def _agregar_boton(self, texto, callback, especial=False):
        b = boton(texto, callback, color=(0.19, 0.40, 0.34, 1) if especial else BTN)
        self.contenido.add_widget(b)

    def _llenar_panel(self):
        if not self.cajon:
            return
        self.contenido.clear_widgets()
        j = self.c.juego
        d = self.c.dialogo
        if d:
            self.titulo_cajon.text = d["titulo"].upper()
            self._agregar_texto(
                d["texto"], alto=max(64, len(d["texto"].splitlines()) * 28 + 25)
            )
            if d["kind"] == "tarjetas":
                jugador = j.jugadores[0]
                for i, p in enumerate(jugador.tarjetas):
                    fila = BoxLayout(size_hint_y=None, height=dp(62), spacing=dp(5))
                    ico = ASSETS / "iconos_cartas" / f"{j.figuras_cartas[p]}.png"
                    if ico.exists():
                        fila.add_widget(
                            Image(source=str(ico), size_hint_x=None, width=dp(46))
                        )
                    fila.add_widget(etiqueta(f"{p}\n{j.figuras_cartas[p]}", tam=13))
                    chk = CheckBox(
                        active=i in self.c.seleccion_cartas,
                        size_hint_x=None,
                        width=dp(42),
                    )
                    chk.bind(active=lambda _w, val, k=i: self.c.alternar_carta(k))
                    fila.add_widget(chk)
                    self.contenido.add_widget(fila)
                if jugador.cartas_continente:
                    self._agregar_texto("TARJETAS CONTINENTALES", color=GOLD)
                    for cont in sorted(jugador.cartas_continente):
                        fila = BoxLayout(size_hint_y=None, height=dp(40))
                        fila.add_widget(etiqueta(cont, tam=13))
                        chk = CheckBox(
                            active=cont in self.c.seleccion_continentes,
                            size_hint_x=None,
                            width=dp(42),
                        )
                        chk.bind(
                            active=lambda _w, val, k=cont: self.c.alternar_continente(k)
                        )
                        fila.add_widget(chk)
                        self.contenido.add_widget(fila)
                self._agregar_boton(
                    "CANJEAR SELECCIÓN", lambda: self.elegir("canje_manual"), True
                )
            if d["kind"] == "objetivos":
                for o in j.jugadores[0].objetivos:
                    src = (
                        ASSETS / "objetivos_imagenes" / f'obj_{o["tarjeta_id"]:02d}.png'
                    )
                    if src.exists():
                        self.contenido.add_widget(
                            Image(
                                source=str(src),
                                allow_stretch=True,
                                keep_ratio=True,
                                size_hint_y=None,
                                height=dp(160),
                            )
                        )
            if d["kind"] == "propuesta_bot":
                self._agregar_texto(
                    "Podés tocar países y hacer zoom en el mapa mientras decidís.",
                    color=SOFT,
                )
                pais = self.c.inspeccion
                if pais in j.tablero:
                    dato = j.tablero[pais]
                    propietario = (
                        j.jugadores[dato["propietario"]].color_nombre
                        if dato["propietario"] is not None
                        else "Condominio"
                    )
                    self._agregar_texto(
                        f"INSPECCIÓN: {pais} · {propietario} · "
                        f'{dato["ejercitos"]} ejércitos · {dato["misiles"]} misiles',
                        color=GOLD,
                        alto=55,
                    )
            for nombre, accion in d["opciones"]:
                self._agregar_boton(
                    nombre,
                    lambda cod=accion: self.elegir(cod),
                    accion in ("situacion_ok", "responder_bot:si"),
                )
            return
        if self.modo_panel == "pais" and self.c.inspeccion in j.tablero:
            p = self.c.inspeccion
            d = j.tablero[p]
            self.titulo_cajon.text = p.upper()
            self._agregar_texto("Continente: " + d["continente"])
            nombre = (
                "Condominio: "
                + ", ".join(j.jugadores[i].color_nombre for i in j.condominios[p])
                if p in j.condominios
                else (
                    j.jugadores[d["propietario"]].nombre
                    if d["propietario"] is not None
                    else "Sin dueño"
                )
            )
            self._agregar_texto(nombre)
            self._agregar_texto(
                f'Ejércitos: {d["ejercitos"]}  ·  Misiles: {d["misiles"]}'
            )
            self._agregar_texto(
                "Fronteras: " + ", ".join(d["fronteras"]),
                tam=13,
                alto=max(58, len(d["fronteras"]) * 17),
            )
            if self.c.origen:
                self._agregar_texto("Origen: " + self.c.origen, color=GOLD)
            if self.c.destino:
                self._agregar_texto("Destino: " + self.c.destino, color=GOLD)
            self._agregar_boton(
                "Marcar como origen",
                lambda: (self.c.seleccionar_origen(p), self._llenar_panel()),
            )
        else:
            self.titulo_cajon.text = "ESTADO DE PARTIDA"
            estado = self.c.resumen()
            self._agregar_texto(
                f'Ronda {estado["ronda"]}  ·  {estado["situacion"]}', color=GOLD
            )
            self._agregar_texto(f'Fase: {estado["fase"]} · {estado["etapa_ronda"]}')
            for nombre, n, elim in estado["jugadores"]:
                self._agregar_texto(
                    f"{nombre}: {n} países" + (" · eliminado" if elim else ""), tam=13
                )
            if estado["refuerzos"]:
                r = estado["refuerzos"]
                self._agregar_texto(f'Refuerzos: {r["total"]}; libres {r["libres"]}')
                self._agregar_texto(
                    "Por continente: "
                    + ", ".join(f"{c}: {n}" for c, n in r["continentes"].items()),
                    tam=13,
                )
            self._agregar_texto("ÚLTIMOS EVENTOS", color=GOLD)
            self._agregar_texto("\n".join(j.historial[-8:]), tam=12, alto=155)
            self._agregar_boton("PACTOS", lambda: self.abrir_accion("pactos"))
            self._agregar_boton(
                "HISTORIAL COMPLETO", lambda: self.abrir_accion("historial")
            )
            self._agregar_boton(
                "VELOCIDAD BOTS", lambda: self.abrir_accion("velocidad")
            )
            self._agregar_boton(
                "ACTIVAR / DESACTIVAR ANIMACIONES",
                lambda: self.abrir_accion("animaciones"),
            )

    def actualizar(self, dt):
        j = self.c.juego
        ahora = time.monotonic()
        intervalo = self.c.VELOCIDADES[self.c.velocidad]
        if (
            not j.jugador_actual().es_bot
            or intervalo is None
            or ahora - self._ultimo_paso >= intervalo
        ):
            self._ultimo_paso = ahora
            self.c.tick()
        estado = (
            j.ronda,
            j.turno_idx,
            j.fase,
            j.etapa_ronda,
            j.ejercitos_a_colocar,
            self.c.origen,
            self.c.destino,
            self.c.inspeccion,
            self.c.aviso,
            self.c.velocidad,
            self.c.animaciones,
        )
        self.actualizar_orden_turnos()
        if estado != self._ultimo_estado:
            self._ultimo_estado = estado
            seleccion = (
                f"{self.c.origen} → {self.c.destino}"
                if self.c.destino
                else f"Origen: {self.c.origen}" if self.c.origen else ""
            )
            self.texto_hud.text = (
                f"R{j.ronda}  ·  {j.fase}  ·  {j.jugador_actual().nombre}  ·  {seleccion}\n"
                f"{j.situacion}  |  {self.c.aviso[:100]}"
            )
        if self.c.dialogo is not self._ultimo_dialogo:
            self._ultimo_dialogo = self.c.dialogo
            if self.c.dialogo:
                self.abrir_panel("dialogo")
            elif self.cajon and self.modo_panel == "dialogo":
                self.cerrar_panel()
        acciones = tuple(self.c.acciones_disponibles())
        if acciones != self._ultima_ui:
            self._ultima_ui = acciones
            self.acciones.clear_widgets()
            nombres = {
                "incorporar": "+ EJÉRCITOS",
                "misil_nuevo": "+ MISIL",
                "misil_convertir": "CAMBIAR A MISIL",
                "atacar": "ATACAR",
                "lanzar_misil": "LANZAR MISIL",
                "reagrupar": "MOVER TROPAS",
                "reagrupar_misil": "MOVER MISIL",
                "pactos": "PACTOS",
                "canje": "CANJEAR",
                "pasar": "PASAR FASE",
                "solicitar_tarjeta": "PEDIR TARJETA",
            }
            if not acciones:
                self.acciones.add_widget(
                    etiqueta(
                        "Esperando al rival o una decisión pendiente…",
                        halign="center",
                        color=SOFT, size_hint_y=None,
                        height=dp(45),
                    )
                )
            for a in acciones:
                self.acciones.add_widget(
                    boton(
                        nombres.get(a, a),
                        lambda op=a: self.abrir_accion(op),
                        color=(0.17, 0.39, 0.29, 1) if a == "pasar" else BTN,
                        altura=48,
                    )
                )
            self.acciones.add_widget(
                boton("ANULAR", lambda: self.abrir_accion("cancelar"), altura=59)
            )
        if ahora - self._ultima_actualizacion > 0.16 or (
            self.c.animaciones and self.c.fx and ahora - self.mapa.comienzo_fx < 1.7
        ):
            self._ultima_actualizacion = ahora
            self.mapa.renderizar()


class TegAndroid(App):
    title = "TEG La Revancha"

    def build(self):
        self.rootview = FloatLayout()
        self.rootview.add_widget(PantallaInicio(self.iniciar))
        try:
            # No se solicitan permisos de red ni se usa ningún servicio externo.
            Window.softinput_mode = "below_target"
        except Exception:
            pass
        Window.bind(on_keyboard=self.tecla_atras)
        return self.rootview

    def tecla_atras(self, _window, key, *_args):
        if key != 27:
            return False
        for vista in self.rootview.children:
            if isinstance(vista, VistaJuego):
                if vista.c.dialogo and vista.c.dialogo["obligatorio"]:
                    return True
                if vista.cajon:
                    vista.cerrar_panel()
                    return True
        return False

    def iniciar(self, n, color, eliminacion, animaciones):
        c = ControlMovil(n, color, eliminacion, animaciones)
        self.rootview.clear_widgets()
        self.rootview.add_widget(VistaJuego(c))


if __name__ == "__main__":
    TegAndroid().run()
