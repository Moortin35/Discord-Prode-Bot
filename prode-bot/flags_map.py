FLAG_CODES = {
    "Mexico": "mx", "South Africa": "za", "Korea Republic": "kr", "Czechia": "cz",
    "Canada": "ca", "Bosnia and Herzegovina": "ba", "USA": "us", "Paraguay": "py",
    "Qatar": "qa", "Switzerland": "ch", "Brazil": "br", "Morocco": "ma",
    "Haiti": "ht", "Scotland": "gb-sct", "Australia": "au", "Türkiye": "tr",
    "Germany": "de", "Curaçao": "cw", "Netherlands": "nl", "Japan": "jp",
    "Côte d'Ivoire": "ci", "Ecuador": "ec", "Sweden": "se", "Tunisia": "tn",
    "Spain": "es", "Cabo Verde": "cv", "Belgium": "be", "Egypt": "eg",
    "Saudi Arabia": "sa", "Uruguay": "uy", "IR Iran": "ir", "New Zealand": "nz",
    "France": "fr", "Senegal": "sn", "Iraq": "iq", "Norway": "no",
    "Argentina": "ar", "Algeria": "dz", "Austria": "at", "Jordan": "jo",
    "Portugal": "pt", "Congo DR": "cd", "England": "gb-eng", "Croatia": "hr",
    "Ghana": "gh", "Panama": "pa", "Uzbekistan": "uz", "Colombia": "co",
}

def codigo_pais(equipo):
    return FLAG_CODES.get(equipo)