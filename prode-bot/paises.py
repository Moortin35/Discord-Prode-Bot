"""Banderas de los países de la UEFA.

El país de cada club se deriva del estadio de sus partidos de local, que ESPN
informa en el fixture. Este módulo solo traduce ese nombre de país a un emoji.
"""

# Nombre de país como lo devuelve ESPN → código ISO 3166-1 alfa-2.
# Están los 55 miembros de la UEFA, no solo los que juegan esta temporada, para
# que un club de un país nuevo no quede sin bandera el año que viene.
ISO_POR_PAIS = {
    "Albania": "al", "Andorra": "ad", "Armenia": "am", "Austria": "at",
    "Azerbaijan": "az", "Belarus": "by", "Belgium": "be",
    "Bosnia and Herzegovina": "ba", "Bulgaria": "bg", "Croatia": "hr",
    "Cyprus": "cy", "Czechia": "cz", "Denmark": "dk", "England": "gb-eng",
    "Estonia": "ee", "Faroe Islands": "fo", "Finland": "fi", "France": "fr",
    "Georgia": "ge", "Germany": "de", "Gibraltar": "gi", "Greece": "gr",
    "Hungary": "hu", "Iceland": "is", "Israel": "il", "Italy": "it",
    "Kazakhstan": "kz", "Kosovo": "xk", "Latvia": "lv", "Liechtenstein": "li",
    "Lithuania": "lt", "Luxembourg": "lu", "Malta": "mt", "Moldova": "md",
    "Monaco": "mc", "Montenegro": "me", "Netherlands": "nl",
    "North Macedonia": "mk", "Northern Ireland": "gb-nir", "Norway": "no",
    "Poland": "pl", "Portugal": "pt", "Republic of Ireland": "ie",
    "Romania": "ro", "Russia": "ru", "San Marino": "sm", "Scotland": "gb-sct",
    "Serbia": "rs", "Slovakia": "sk", "Slovenia": "si", "Spain": "es",
    "Sweden": "se", "Switzerland": "ch", "Türkiye": "tr", "Ukraine": "ua",
    "Wales": "gb-wls",
}

# ESPN no siempre usa el mismo nombre para el mismo país
ALIAS = {
    "Turkey": "Türkiye",
    "Turkiye": "Türkiye",
    "Czech Republic": "Czechia",
    "Ireland": "Republic of Ireland",
    "Bosnia": "Bosnia and Herzegovina",
    "Holland": "Netherlands",
    "Macedonia": "North Macedonia",
    "United Kingdom": "England",
}

# Clubes cuyo país no se puede deducir del estadio donde juegan de local.
PAIS_FORZADO = {
    # Juega de local en Londres por la guerra, pero es ucraniano
    "Shakhtar Donetsk": "Ukraine",
    # ESPN no informa el país de su estadio
    "Sabah FK": "Azerbaijan",
}

# Inglaterra, Escocia, Gales e Irlanda del Norte no son países ISO: su bandera
# es una secuencia de etiquetas de subdivisión, no dos indicadores regionales.
_SUBDIVISIONES = {
    "gb-eng": "\U0001F3F4\U000E0067\U000E0062\U000E0065\U000E006E\U000E0067\U000E007F",
    "gb-sct": "\U0001F3F4\U000E0067\U000E0062\U000E0073\U000E0063\U000E0074\U000E007F",
    "gb-wls": "\U0001F3F4\U000E0067\U000E0062\U000E0077\U000E006C\U000E0073\U000E007F",
    "gb-nir": "\U0001F1EC\U0001F1E7",  # no tiene emoji propio: se usa el del Reino Unido
}

BANDERA_DESCONOCIDA = "\U0001F3F3️"  # 🏳️


def normalizar(pais):
    """Devuelve el nombre canónico del país, resolviendo alias de ESPN."""
    if not pais:
        return None
    pais = pais.strip()
    return ALIAS.get(pais, pais)


def bandera_pais(pais):
    """Emoji de la bandera del país, o 🏳️ si no lo reconocemos."""
    iso = ISO_POR_PAIS.get(normalizar(pais) or "")
    if not iso:
        return BANDERA_DESCONOCIDA
    if iso in _SUBDIVISIONES:
        return _SUBDIVISIONES[iso]
    # Dos letras ASCII → dos indicadores regionales, que es como se arma la
    # bandera: "es" → 🇪 + 🇸 → 🇪🇸
    return "".join(chr(0x1F1E6 + ord(c) - ord("a")) for c in iso)
