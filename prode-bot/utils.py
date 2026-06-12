BANDERAS = {
    "Mexico": "🇲🇽", "South Africa": "🇿🇦", "Korea Republic": "🇰🇷", "Czechia": "🇨🇿",
    "Canada": "🇨🇦", "Bosnia and Herzegovina": "🇧🇦", "USA": "🇺🇸", "Paraguay": "🇵🇾",
    "Qatar": "🇶🇦", "Switzerland": "🇨🇭", "Brazil": "🇧🇷", "Morocco": "🇲🇦",
    "Haiti": "🇭🇹", "Scotland": "🏴", "Australia": "🇦🇺", "Türkiye": "🇹🇷",
    "Germany": "🇩🇪", "Curaçao": "🇨🇼", "Netherlands": "🇳🇱", "Japan": "🇯🇵",
    "Côte d'Ivoire": "🇨🇮", "Ecuador": "🇪🇨", "Sweden": "🇸🇪", "Tunisia": "🇹🇳",
    "Spain": "🇪🇸", "Cabo Verde": "🇨🇻", "Belgium": "🇧🇪", "Egypt": "🇪🇬",
    "Saudi Arabia": "🇸🇦", "Uruguay": "🇺🇾", "IR Iran": "🇮🇷", "New Zealand": "🇳🇿",
    "France": "🇫🇷", "Senegal": "🇸🇳", "Iraq": "🇮🇶", "Norway": "🇳🇴",
    "Argentina": "🇦🇷", "Algeria": "🇩🇿", "Austria": "🇦🇹", "Jordan": "🇯🇴",
    "Portugal": "🇵🇹", "Congo DR": "🇨🇩", "England": "🏴", "Croatia": "🇭🇷",
    "Ghana": "🇬🇭", "Panama": "🇵🇦", "Uzbekistan": "🇺🇿", "Colombia": "🇨🇴",
}

def bandera(equipo: str) -> str:
    return BANDERAS.get(equipo, "🏳️")