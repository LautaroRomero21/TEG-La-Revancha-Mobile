"""
data.py - Datos del tablero TEG La Revancha
Contiene los 72 paises, sus continentes, fronteras y coordenadas en el mapa.
Fronteras ajustadas segun las conexiones revisadas hasta la v11, en ambos sentidos.
"""

# ─────────────────────────────────────────────
# CONTINENTES y sus bonificaciones de ejercitos
# ─────────────────────────────────────────────
CONTINENTES = {
    "America del Norte": {"bonus": 6, "color": (205, 133,  63)},
    "America Central":   {"bonus": 3, "color": (180, 150,  40)},
    "America del Sur":   {"bonus": 4, "color": ( 60, 160,  60)},
    "Europa":            {"bonus": 8, "color": (160, 160, 180)},
    "Asia":              {"bonus": 8, "color": (200, 180, 100)},
    "Africa":            {"bonus": 4, "color": (210, 140, 100)},
    "Oceania":           {"bonus": 3, "color": (100, 180, 140)},
}

# ─────────────────────────────────────────────
# PAISES
# coords: posicion en espacio 1280x960
# ─────────────────────────────────────────────
PAISES_DATA = {
    'Alaska': {"continente": 'America del Norte', "fronteras": ['Canada', 'Chukchi', 'Kamchatka'], "coords": (146, 89)},
    'Canada': {"continente": 'America del Norte', "fronteras": ['Alaska', 'Isla Victoria', 'Oregon', 'Terranova'], "coords": (180, 168)},
    'Isla Victoria': {"continente": 'America del Norte', "fronteras": ['Canada', 'Groenlandia'], "coords": (275, 85)},
    'Groenlandia': {"continente": 'America del Norte', "fronteras": ['Isla Victoria', 'Islandia', 'Labrador', 'Nueva York'], "coords": (430, 81)},
    'Labrador': {"continente": 'America del Norte', "fronteras": ['Groenlandia', 'Terranova'], "coords": (345, 130)},
    'Oregon': {"continente": 'America del Norte', "fronteras": ['Canada', 'Chicago', 'Las Vegas', 'Terranova'], "coords": (185, 248)},
    'Terranova': {"continente": 'America del Norte', "fronteras": ['Canada', 'Chicago', 'Labrador', 'Oregon'], "coords": (270, 208)},
    'Nueva York': {"continente": 'America del Norte', "fronteras": ['Chicago', 'Groenlandia'], "coords": (390, 205)},
    'Las Vegas': {"continente": 'America del Norte', "fronteras": ['California', 'Chicago', 'Florida', 'Oregon'], "coords": (163, 315)},
    'Chicago': {"continente": 'America del Norte', "fronteras": ['Florida', 'Las Vegas', 'Nueva York', 'Oregon', 'Terranova'], "coords": (323, 281)},
    'California': {"continente": 'America del Norte', "fronteras": ['Florida', 'Las Vegas', 'Mexico', 'Tonga'], "coords": (162, 376)},
    'Florida': {"continente": 'America del Norte', "fronteras": ['California', 'Chicago', 'Cuba', 'Las Vegas'], "coords": (280, 345)},
    'Mexico': {"continente": 'America Central', "fronteras": ['California', 'Cuba', 'Honduras'], "coords": (228, 418)},
    'Cuba': {"continente": 'America Central', "fronteras": ['Florida', 'Honduras', 'Jamaica', 'Mexico'], "coords": (355, 413)},
    'Honduras': {"continente": 'America Central', "fronteras": ['Cuba', 'El Salvador', 'Mexico'], "coords": (259, 473)},
    'Jamaica': {"continente": 'America Central', "fronteras": ['Cuba', 'Nicaragua'], "coords": (385, 505)},
    'El Salvador': {"continente": 'America Central', "fronteras": ['Honduras', 'Nicaragua'], "coords": (300, 488)},
    'Nicaragua': {"continente": 'America Central', "fronteras": ['Colombia', 'El Salvador', 'Jamaica'], "coords": (287, 536)},
    'Colombia': {"continente": 'America del Sur', "fronteras": ['Brasil', 'Chile', 'Nicaragua', 'Venezuela'], "coords": (254, 610)},
    'Venezuela': {"continente": 'America del Sur', "fronteras": ['Brasil', 'Colombia'], "coords": (340, 610)},
    'Brasil': {"continente": 'America del Sur', "fronteras": ['Argentina', 'Bolivia', 'Chile', 'Colombia', 'Paraguay', 'Sahara', 'Uruguay', 'Venezuela'], "coords": (375, 693)},
    'Bolivia': {"continente": 'America del Sur', "fronteras": ['Argentina', 'Brasil', 'Chile', 'Paraguay'], "coords": (284, 723)},
    'Paraguay': {"continente": 'America del Sur', "fronteras": ['Argentina', 'Bolivia', 'Brasil'], "coords": (330, 730)},
    'Chile': {"continente": 'America del Sur', "fronteras": ['Argentina', 'Australia', 'Bolivia', 'Brasil', 'Colombia'], "coords": (245, 752)},
    'Uruguay': {"continente": 'America del Sur', "fronteras": ['Argentina', 'Brasil', 'Nigeria'], "coords": (358, 785)},
    'Argentina': {"continente": 'America del Sur', "fronteras": ['Bolivia', 'Brasil', 'Chile', 'Paraguay', 'Uruguay'], "coords": (300, 805)},
    'Islandia': {"continente": 'Europa', "fronteras": ['Groenlandia', 'Irlanda', 'Noruega'], "coords": (594, 193)},
    'Gran Bretana': {"continente": 'Europa', "fronteras": ['Alemania', 'Irlanda', 'Portugal'], "coords": (645, 290)},
    'Irlanda': {"continente": 'Europa', "fronteras": ['Gran Bretana', 'Islandia'], "coords": (565, 293)},
    'Noruega': {"continente": 'Europa', "fronteras": ['Finlandia', 'Islandia'], "coords": (700, 199)},
    'Finlandia': {"continente": 'Europa', "fronteras": ['Bielorrusia', 'Noruega'], "coords": (766, 199)},
    'Bielorrusia': {"continente": 'Europa', "fronteras": ['Finlandia', 'Polonia', 'Ucrania'], "coords": (826, 189)},
    'Portugal': {"continente": 'Europa', "fronteras": ['Espana', 'Gran Bretana'], "coords": (555, 461)},
    'Espana': {"continente": 'Europa', "fronteras": ['Francia', 'Portugal', 'Sahara'], "coords": (615, 471)},
    'Francia': {"continente": 'Europa', "fronteras": ['Alemania', 'Espana', 'Italia'], "coords": (670, 403)},
    'Alemania': {"continente": 'Europa', "fronteras": ['Croacia', 'Francia', 'Gran Bretana', 'Italia', 'Polonia', 'Serbia'], "coords": (720, 343)},
    'Polonia': {"continente": 'Europa', "fronteras": ['Albania', 'Alemania', 'Bielorrusia', 'Croacia', 'Egipto', 'Serbia', 'Ucrania'], "coords": (796, 314)},
    'Ucrania': {"continente": 'Europa', "fronteras": ['Albania', 'Bielorrusia', 'Iran', 'Polonia', 'Rusia'], "coords": (875, 210)},
    'Italia': {"continente": 'Europa', "fronteras": ['Alemania', 'Croacia', 'Francia'], "coords": (713, 450)},
    'Serbia': {"continente": 'Europa', "fronteras": ['Alemania', 'Croacia', 'Polonia'], "coords": (770, 363)},
    'Croacia': {"continente": 'Europa', "fronteras": ['Alemania', 'Italia', 'Polonia', 'Serbia'], "coords": (763, 435)},
    'Albania': {"continente": 'Europa', "fronteras": ['Irak', 'Iran', 'Polonia', 'Ucrania'], "coords": (860, 390)},
    'Siberia': {"continente": 'Asia', "fronteras": ['Chechenia', 'China', 'Chukchi', 'Rusia'], "coords": (962, 95)},
    'Kamchatka': {"continente": 'Asia', "fronteras": ['Alaska', 'China', 'Chukchi', 'Corea', 'Japon'], "coords": (1065, 180)},
    'Chechenia': {"continente": 'Asia', "fronteras": ['China', 'Chukchi', 'Rusia', 'Siberia'], "coords": (964, 163)},
    'Rusia': {"continente": 'Asia', "fronteras": ['Chechenia', 'China', 'Iran', 'Siberia', 'Turquia', 'Ucrania'], "coords": (935, 233)},
    'Japon': {"continente": 'Asia', "fronteras": ['Corea', 'Kamchatka'], "coords": (1160, 279)},
    'Corea': {"continente": 'Asia', "fronteras": ['China', 'Japon', 'Kamchatka', 'Malasia', 'Vietnam'], "coords": (1095, 330)},
    'Iran': {"continente": 'Asia', "fronteras": ['Albania', 'Irak', 'Rusia', 'Turquia', 'Ucrania'], "coords": (905, 331)},
    'Turquia': {"continente": 'Asia', "fronteras": ['China', 'India', 'Irak', 'Iran', 'Israel', 'Rusia'], "coords": (970, 450)},
    'China': {"continente": 'Asia', "fronteras": ['Chechenia', 'Chukchi', 'Corea', 'India', 'Kamchatka', 'Malasia', 'Rusia', 'Siberia', 'Turquia'], "coords": (1005, 302)},
    'Israel': {"continente": 'Asia', "fronteras": ['Arabia', 'Egipto', 'Irak', 'Turquia'], "coords": (918, 475)},
    'Irak': {"continente": 'Asia', "fronteras": ['Albania', 'Egipto', 'Iran', 'Israel', 'Turquia'], "coords": (895, 435)},
    'Arabia': {"continente": 'Asia', "fronteras": ['Israel'], "coords": (935, 545)},
    'India': {"continente": 'Asia', "fronteras": ['China', 'Malasia', 'Sumatra', 'Turquia', 'Vietnam'], "coords": (1024, 495)},
    'Malasia': {"continente": 'Asia', "fronteras": ['China', 'Corea', 'India', 'Vietnam'], "coords": (1040, 412)},
    'Vietnam': {"continente": 'Asia', "fronteras": ['Corea', 'Filipinas', 'India', 'Malasia'], "coords": (1090, 468)},
    'Sahara': {"continente": 'Africa', "fronteras": ['Brasil', 'Egipto', 'Espana', 'Etiopia', 'Nigeria'], "coords": (615, 655)},
    'Egipto': {"continente": 'Africa', "fronteras": ['Etiopia', 'Irak', 'Israel', 'Madagascar', 'Polonia', 'Sahara'], "coords": (746, 625)},
    'Nigeria': {"continente": 'Africa', "fronteras": ['Angola', 'Etiopia', 'Mauritania', 'Sahara', 'Sudafrica', 'Uruguay'], "coords": (691, 735)},
    'Etiopia': {"continente": 'Africa', "fronteras": ['Angola', 'Egipto', 'Nigeria', 'Sahara'], "coords": (736, 680)},
    'Angola': {"continente": 'Africa', "fronteras": ['Etiopia', 'Mauritania', 'Nigeria'], "coords": (825, 715)},
    'Mauritania': {"continente": 'Africa', "fronteras": ['Angola', 'Madagascar', 'Nigeria', 'Sudafrica'], "coords": (800, 760)},
    'Sudafrica': {"continente": 'Africa', "fronteras": ['Madagascar', 'Mauritania', 'Nigeria'], "coords": (770, 810)},
    'Madagascar': {"continente": 'Africa', "fronteras": ['Egipto', 'Mauritania', 'Sudafrica'], "coords": (861, 805)},
    'Filipinas': {"continente": 'Oceania', "fronteras": ['Australia', 'Tonga', 'Vietnam'], "coords": (1080, 620)},
    'Sumatra': {"continente": 'Oceania', "fronteras": ['Australia', 'India'], "coords": (1000, 660)},
    'Tonga': {"continente": 'Oceania', "fronteras": ['Australia', 'California', 'Filipinas'], "coords": (1170, 660)},
    'Australia': {"continente": 'Oceania', "fronteras": ['Chile', 'Filipinas', 'Sumatra', 'Tasmania', 'Tonga'], "coords": (1060, 748)},
    'Tasmania': {"continente": 'Oceania', "fronteras": ['Australia', 'Nueva Zelanda'], "coords": (1080, 848)},
    'Nueva Zelanda': {"continente": 'Oceania', "fronteras": ['Tasmania'], "coords": (1020, 888)},
    'Chukchi': {"continente": 'Asia', "fronteras": ['Alaska', 'Chechenia', 'China', 'Kamchatka', 'Siberia'], "coords": (1062, 100)},
}

# ─────────────────────────────────────────────
# Valores del REGLAMENTO OFICIAL (paginas 16 y 24-26), no del README anterior.
FIGURAS_TARJETA = ["Soldado", "Avion", "Tanque", "Granada", "Barco"]
CANJE_INICIAL = 6
CANJE_STEP_PRIMEROS = 5  # Tras el segundo canje: incrementos de cinco
CANJE_AFTER_5 = 5
MISIL_COSTO_EJERCITOS = 6
MISIL_EFECTO_EJERCITOS = 3  # A una frontera; a 2: 2, a 3: 1
# El reglamento NO contempla comprar misiles con tarjetas.
MISIL_COSTO_TARJETAS = 0

# Seis colores oficiales: blanco, negro, rojo, azul, amarillo, verde.
PLAYER_COLORS = [
    (232, 235, 239), (45, 47, 54), (225, 58, 60),
    (55, 124, 225), (234, 190, 38), (65, 178, 85),
]
PLAYER_NAMES_DEFAULT = [
    "Jugador Blanco", "Bot Negro", "Bot Rojo",
    "Bot Azul", "Bot Amarillo", "Bot Verde",
]
COLORES_OFICIALES = ["Blanco", "Negro", "Rojo", "Azul", "Amarillo", "Verde"]

# Correspondencia exacta de las 72 cartas de país, transcripta de
# "Tarjetas países.pdf" (páginas 1-5). Las cartas continentales son aparte.
FIGURAS_POR_PAIS = {
    **dict.fromkeys(('Angola','Alemania','Albania','Alaska'), 'Soldado'),
    **dict.fromkeys(('Argentina','Chechenia','Las Vegas','Mauritania','Ucrania'), 'Granada'),
    **dict.fromkeys((
        'Nueva York','Nigeria','Noruega','Nueva Zelanda','Oregon','Paraguay','Polonia',
        'Portugal','Rusia','Sahara','Serbia','Siberia','Sudafrica','Sumatra','Tasmania',
        'Terranova','Tonga','Turquia','Uruguay','Venezuela','Vietnam'), 'Tanque'),
    **dict.fromkeys((
        'Arabia','Australia','Bielorrusia','Bolivia','Brasil','California',
        'Canada','Chicago','Chile','China','Chukchi','Colombia','Corea','Croacia',
        'Cuba','Egipto','El Salvador','Espana','Etiopia',
        'Filipinas','Irlanda'), 'Avion'),
    **dict.fromkeys((
        'Finlandia','Florida','Francia','Gran Bretana','Groenlandia','Honduras','India','Iran','Irak',
        'Isla Victoria','Islandia','Israel','Italia','Jamaica','Kamchatka','Japon',
        'Labrador','Madagascar','Mexico','Malasia','Nicaragua'), 'Barco'),
}
# Según el reglamento (pág. 26). Las cartas de continente están separadas
# del mazo de países y equivalen a 1, 2 o 3 símbolos para canjes.
SIMBOLOS_CONTINENTES = {
    'America del Norte': ('CANJE',), 'Europa': ('CANJE',), 'Asia': ('CANJE',),
    'America del Sur': ('Avion','Tanque'), 'Africa': ('Avion','Barco'),
    'America Central': ('Tanque',), 'Oceania': ('Barco',),
}
assert set(FIGURAS_POR_PAIS) == set(PAISES_DATA), (set(PAISES_DATA)-set(FIGURAS_POR_PAIS),set(FIGURAS_POR_PAIS)-set(PAISES_DATA))
assert len(FIGURAS_POR_PAIS) == 72

# Lista de islas del tablero (regla de objetivo, pagina 38).
ISLAS = {
    "Isla Victoria", "Groenlandia", "Terranova", "Islandia", "Gran Bretana",
    "Irlanda", "Cuba", "Jamaica", "Japon", "Filipinas", "Sumatra",
    "Tonga", "Tasmania", "Nueva Zelanda", "Madagascar",
}

def ejercitos_por_paises(n_paises: int) -> int:
    """Mitad de paises redondeada hacia abajo; siempre con un minimo de 4 (incluso para 6 y 7)."""
    return max(4, n_paises // 2)

def construir_tablero() -> dict:
    """Retorna el estado inicial del tablero con todos los paises."""
    tablero = {}
    for nombre, datos in PAISES_DATA.items():
        tablero[nombre] = {
            "continente": datos["continente"],
            "fronteras":  list(datos["fronteras"]),
            "coords":     datos["coords"],
            "propietario": None,
            "ejercitos":   1,
            "misiles":     0,
        }
    return tablero
