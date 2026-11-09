"""Locale data: timezones and browser languages per country.

DATA PROVENANCE (read this before trusting the numbers)
-------------------------------------------------------
* ``COUNTRY_TIMEZONES``  REAL DATA. Generated from the IANA tz database
  (``zone.tab``, public domain): every zone of every country, in tzdata order.
  tzdata lists the main zone of a country first; this was checked by hand for
  every multi-zone country and the exceptions are fixed in TIMEZONE_WEIGHTS.
* ``TIMEZONE_WEIGHTS``   APPROXIMATE. Rough population shares for the big
  multi-zone countries, written from general knowledge. Not a dataset.
* ``COUNTRY_LANGUAGES``  CURATED. The usual browser UI language list per
  country, written from general knowledge. Not a dataset: Apify's data does
  not contain language information. Edit freely; PRs welcome.
* ``ENGLISH_FALLBACK_PROBABILITY``  HEURISTIC. Share of non-English-locale
  profiles that also list English as a fallback language.

These are the ONLY pieces of the generator that are not sampled from real
browser data, which is why they are isolated in this module.
"""
from __future__ import annotations

import random
from typing import Dict, List, Sequence, Tuple

# --- real data: generated from the IANA tz database (zone.tab) -------------------
COUNTRY_TIMEZONES: Dict[str, List[str]] = {
    "AD": ['Europe/Andorra'],
    "AE": ['Asia/Dubai'],
    "AF": ['Asia/Kabul'],
    "AG": ['America/Antigua'],
    "AI": ['America/Anguilla'],
    "AL": ['Europe/Tirane'],
    "AM": ['Asia/Yerevan'],
    "AO": ['Africa/Luanda'],
    "AQ": ['Antarctica/McMurdo', 'Antarctica/Casey', 'Antarctica/Davis', 'Antarctica/DumontDUrville', 'Antarctica/Mawson', 'Antarctica/Palmer', 'Antarctica/Rothera', 'Antarctica/Syowa', 'Antarctica/Troll', 'Antarctica/Vostok'],
    "AR": ['America/Argentina/Buenos_Aires', 'America/Argentina/Cordoba', 'America/Argentina/Salta', 'America/Argentina/Jujuy', 'America/Argentina/Tucuman', 'America/Argentina/Catamarca', 'America/Argentina/La_Rioja', 'America/Argentina/San_Juan', 'America/Argentina/Mendoza', 'America/Argentina/San_Luis', 'America/Argentina/Rio_Gallegos', 'America/Argentina/Ushuaia'],
    "AS": ['Pacific/Pago_Pago'],
    "AT": ['Europe/Vienna'],
    "AU": ['Australia/Lord_Howe', 'Antarctica/Macquarie', 'Australia/Hobart', 'Australia/Melbourne', 'Australia/Sydney', 'Australia/Broken_Hill', 'Australia/Brisbane', 'Australia/Lindeman', 'Australia/Adelaide', 'Australia/Darwin', 'Australia/Perth', 'Australia/Eucla'],
    "AW": ['America/Aruba'],
    "AX": ['Europe/Mariehamn'],
    "AZ": ['Asia/Baku'],
    "BA": ['Europe/Sarajevo'],
    "BB": ['America/Barbados'],
    "BD": ['Asia/Dhaka'],
    "BE": ['Europe/Brussels'],
    "BF": ['Africa/Ouagadougou'],
    "BG": ['Europe/Sofia'],
    "BH": ['Asia/Bahrain'],
    "BI": ['Africa/Bujumbura'],
    "BJ": ['Africa/Porto-Novo'],
    "BL": ['America/St_Barthelemy'],
    "BM": ['Atlantic/Bermuda'],
    "BN": ['Asia/Brunei'],
    "BO": ['America/La_Paz'],
    "BQ": ['America/Kralendijk'],
    "BR": ['America/Noronha', 'America/Belem', 'America/Fortaleza', 'America/Recife', 'America/Araguaina', 'America/Maceio', 'America/Bahia', 'America/Sao_Paulo', 'America/Campo_Grande', 'America/Cuiaba', 'America/Santarem', 'America/Porto_Velho', 'America/Boa_Vista', 'America/Manaus', 'America/Eirunepe', 'America/Rio_Branco'],
    "BS": ['America/Nassau'],
    "BT": ['Asia/Thimphu'],
    "BW": ['Africa/Gaborone'],
    "BY": ['Europe/Minsk'],
    "BZ": ['America/Belize'],
    "CA": ['America/St_Johns', 'America/Halifax', 'America/Glace_Bay', 'America/Moncton', 'America/Goose_Bay', 'America/Blanc-Sablon', 'America/Toronto', 'America/Iqaluit', 'America/Atikokan', 'America/Winnipeg', 'America/Resolute', 'America/Rankin_Inlet', 'America/Regina', 'America/Swift_Current', 'America/Edmonton', 'America/Cambridge_Bay', 'America/Inuvik', 'America/Vancouver', 'America/Creston', 'America/Dawson_Creek', 'America/Fort_Nelson', 'America/Whitehorse', 'America/Dawson'],
    "CC": ['Indian/Cocos'],
    "CD": ['Africa/Kinshasa', 'Africa/Lubumbashi'],
    "CF": ['Africa/Bangui'],
    "CG": ['Africa/Brazzaville'],
    "CH": ['Europe/Zurich'],
    "CI": ['Africa/Abidjan'],
    "CK": ['Pacific/Rarotonga'],
    "CL": ['America/Santiago', 'America/Coyhaique', 'America/Punta_Arenas', 'Pacific/Easter'],
    "CM": ['Africa/Douala'],
    "CN": ['Asia/Shanghai', 'Asia/Urumqi'],
    "CO": ['America/Bogota'],
    "CR": ['America/Costa_Rica'],
    "CU": ['America/Havana'],
    "CV": ['Atlantic/Cape_Verde'],
    "CW": ['America/Curacao'],
    "CX": ['Indian/Christmas'],
    "CY": ['Asia/Nicosia', 'Asia/Famagusta'],
    "CZ": ['Europe/Prague'],
    "DE": ['Europe/Berlin', 'Europe/Busingen'],
    "DJ": ['Africa/Djibouti'],
    "DK": ['Europe/Copenhagen'],
    "DM": ['America/Dominica'],
    "DO": ['America/Santo_Domingo'],
    "DZ": ['Africa/Algiers'],
    "EC": ['America/Guayaquil', 'Pacific/Galapagos'],
    "EE": ['Europe/Tallinn'],
    "EG": ['Africa/Cairo'],
    "EH": ['Africa/El_Aaiun'],
    "ER": ['Africa/Asmara'],
    "ES": ['Europe/Madrid', 'Africa/Ceuta', 'Atlantic/Canary'],
    "ET": ['Africa/Addis_Ababa'],
    "FI": ['Europe/Helsinki'],
    "FJ": ['Pacific/Fiji'],
    "FK": ['Atlantic/Stanley'],
    "FM": ['Pacific/Chuuk', 'Pacific/Pohnpei', 'Pacific/Kosrae'],
    "FO": ['Atlantic/Faroe'],
    "FR": ['Europe/Paris'],
    "GA": ['Africa/Libreville'],
    "GB": ['Europe/London'],
    "GD": ['America/Grenada'],
    "GE": ['Asia/Tbilisi'],
    "GF": ['America/Cayenne'],
    "GG": ['Europe/Guernsey'],
    "GH": ['Africa/Accra'],
    "GI": ['Europe/Gibraltar'],
    "GL": ['America/Nuuk', 'America/Danmarkshavn', 'America/Scoresbysund', 'America/Thule'],
    "GM": ['Africa/Banjul'],
    "GN": ['Africa/Conakry'],
    "GP": ['America/Guadeloupe'],
    "GQ": ['Africa/Malabo'],
    "GR": ['Europe/Athens'],
    "GS": ['Atlantic/South_Georgia'],
    "GT": ['America/Guatemala'],
    "GU": ['Pacific/Guam'],
    "GW": ['Africa/Bissau'],
    "GY": ['America/Guyana'],
    "HK": ['Asia/Hong_Kong'],
    "HN": ['America/Tegucigalpa'],
    "HR": ['Europe/Zagreb'],
    "HT": ['America/Port-au-Prince'],
    "HU": ['Europe/Budapest'],
    "ID": ['Asia/Jakarta', 'Asia/Pontianak', 'Asia/Makassar', 'Asia/Jayapura'],
    "IE": ['Europe/Dublin'],
    "IL": ['Asia/Jerusalem'],
    "IM": ['Europe/Isle_of_Man'],
    "IN": ['Asia/Kolkata'],
    "IO": ['Indian/Chagos'],
    "IQ": ['Asia/Baghdad'],
    "IR": ['Asia/Tehran'],
    "IS": ['Atlantic/Reykjavik'],
    "IT": ['Europe/Rome'],
    "JE": ['Europe/Jersey'],
    "JM": ['America/Jamaica'],
    "JO": ['Asia/Amman'],
    "JP": ['Asia/Tokyo'],
    "KE": ['Africa/Nairobi'],
    "KG": ['Asia/Bishkek'],
    "KH": ['Asia/Phnom_Penh'],
    "KI": ['Pacific/Tarawa', 'Pacific/Kanton', 'Pacific/Kiritimati'],
    "KM": ['Indian/Comoro'],
    "KN": ['America/St_Kitts'],
    "KP": ['Asia/Pyongyang'],
    "KR": ['Asia/Seoul'],
    "KW": ['Asia/Kuwait'],
    "KY": ['America/Cayman'],
    "KZ": ['Asia/Almaty', 'Asia/Qyzylorda', 'Asia/Qostanay', 'Asia/Aqtobe', 'Asia/Aqtau', 'Asia/Atyrau', 'Asia/Oral'],
    "LA": ['Asia/Vientiane'],
    "LB": ['Asia/Beirut'],
    "LC": ['America/St_Lucia'],
    "LI": ['Europe/Vaduz'],
    "LK": ['Asia/Colombo'],
    "LR": ['Africa/Monrovia'],
    "LS": ['Africa/Maseru'],
    "LT": ['Europe/Vilnius'],
    "LU": ['Europe/Luxembourg'],
    "LV": ['Europe/Riga'],
    "LY": ['Africa/Tripoli'],
    "MA": ['Africa/Casablanca'],
    "MC": ['Europe/Monaco'],
    "MD": ['Europe/Chisinau'],
    "ME": ['Europe/Podgorica'],
    "MF": ['America/Marigot'],
    "MG": ['Indian/Antananarivo'],
    "MH": ['Pacific/Majuro', 'Pacific/Kwajalein'],
    "MK": ['Europe/Skopje'],
    "ML": ['Africa/Bamako'],
    "MM": ['Asia/Yangon'],
    "MN": ['Asia/Ulaanbaatar', 'Asia/Hovd'],
    "MO": ['Asia/Macau'],
    "MP": ['Pacific/Saipan'],
    "MQ": ['America/Martinique'],
    "MR": ['Africa/Nouakchott'],
    "MS": ['America/Montserrat'],
    "MT": ['Europe/Malta'],
    "MU": ['Indian/Mauritius'],
    "MV": ['Indian/Maldives'],
    "MW": ['Africa/Blantyre'],
    "MX": ['America/Mexico_City', 'America/Cancun', 'America/Merida', 'America/Monterrey', 'America/Matamoros', 'America/Chihuahua', 'America/Ciudad_Juarez', 'America/Ojinaga', 'America/Mazatlan', 'America/Bahia_Banderas', 'America/Hermosillo', 'America/Tijuana'],
    "MY": ['Asia/Kuala_Lumpur', 'Asia/Kuching'],
    "MZ": ['Africa/Maputo'],
    "NA": ['Africa/Windhoek'],
    "NC": ['Pacific/Noumea'],
    "NE": ['Africa/Niamey'],
    "NF": ['Pacific/Norfolk'],
    "NG": ['Africa/Lagos'],
    "NI": ['America/Managua'],
    "NL": ['Europe/Amsterdam'],
    "NO": ['Europe/Oslo'],
    "NP": ['Asia/Kathmandu'],
    "NR": ['Pacific/Nauru'],
    "NU": ['Pacific/Niue'],
    "NZ": ['Pacific/Auckland', 'Pacific/Chatham'],
    "OM": ['Asia/Muscat'],
    "PA": ['America/Panama'],
    "PE": ['America/Lima'],
    "PF": ['Pacific/Tahiti', 'Pacific/Marquesas', 'Pacific/Gambier'],
    "PG": ['Pacific/Port_Moresby', 'Pacific/Bougainville'],
    "PH": ['Asia/Manila'],
    "PK": ['Asia/Karachi'],
    "PL": ['Europe/Warsaw'],
    "PM": ['America/Miquelon'],
    "PN": ['Pacific/Pitcairn'],
    "PR": ['America/Puerto_Rico'],
    "PS": ['Asia/Gaza', 'Asia/Hebron'],
    "PT": ['Europe/Lisbon', 'Atlantic/Madeira', 'Atlantic/Azores'],
    "PW": ['Pacific/Palau'],
    "PY": ['America/Asuncion'],
    "QA": ['Asia/Qatar'],
    "RE": ['Indian/Reunion'],
    "RO": ['Europe/Bucharest'],
    "RS": ['Europe/Belgrade'],
    "RU": ['Europe/Kaliningrad', 'Europe/Moscow', 'Europe/Kirov', 'Europe/Volgograd', 'Europe/Astrakhan', 'Europe/Saratov', 'Europe/Ulyanovsk', 'Europe/Samara', 'Asia/Yekaterinburg', 'Asia/Omsk', 'Asia/Novosibirsk', 'Asia/Barnaul', 'Asia/Tomsk', 'Asia/Novokuznetsk', 'Asia/Krasnoyarsk', 'Asia/Irkutsk', 'Asia/Chita', 'Asia/Yakutsk', 'Asia/Khandyga', 'Asia/Vladivostok', 'Asia/Ust-Nera', 'Asia/Magadan', 'Asia/Sakhalin', 'Asia/Srednekolymsk', 'Asia/Kamchatka', 'Asia/Anadyr'],
    "RW": ['Africa/Kigali'],
    "SA": ['Asia/Riyadh'],
    "SB": ['Pacific/Guadalcanal'],
    "SC": ['Indian/Mahe'],
    "SD": ['Africa/Khartoum'],
    "SE": ['Europe/Stockholm'],
    "SG": ['Asia/Singapore'],
    "SH": ['Atlantic/St_Helena'],
    "SI": ['Europe/Ljubljana'],
    "SJ": ['Arctic/Longyearbyen'],
    "SK": ['Europe/Bratislava'],
    "SL": ['Africa/Freetown'],
    "SM": ['Europe/San_Marino'],
    "SN": ['Africa/Dakar'],
    "SO": ['Africa/Mogadishu'],
    "SR": ['America/Paramaribo'],
    "SS": ['Africa/Juba'],
    "ST": ['Africa/Sao_Tome'],
    "SV": ['America/El_Salvador'],
    "SX": ['America/Lower_Princes'],
    "SY": ['Asia/Damascus'],
    "SZ": ['Africa/Mbabane'],
    "TC": ['America/Grand_Turk'],
    "TD": ['Africa/Ndjamena'],
    "TF": ['Indian/Kerguelen'],
    "TG": ['Africa/Lome'],
    "TH": ['Asia/Bangkok'],
    "TJ": ['Asia/Dushanbe'],
    "TK": ['Pacific/Fakaofo'],
    "TL": ['Asia/Dili'],
    "TM": ['Asia/Ashgabat'],
    "TN": ['Africa/Tunis'],
    "TO": ['Pacific/Tongatapu'],
    "TR": ['Europe/Istanbul'],
    "TT": ['America/Port_of_Spain'],
    "TV": ['Pacific/Funafuti'],
    "TW": ['Asia/Taipei'],
    "TZ": ['Africa/Dar_es_Salaam'],
    "UA": ['Europe/Simferopol', 'Europe/Kyiv'],
    "UG": ['Africa/Kampala'],
    "UM": ['Pacific/Midway', 'Pacific/Wake'],
    "US": ['America/New_York', 'America/Detroit', 'America/Kentucky/Louisville', 'America/Kentucky/Monticello', 'America/Indiana/Indianapolis', 'America/Indiana/Vincennes', 'America/Indiana/Winamac', 'America/Indiana/Marengo', 'America/Indiana/Petersburg', 'America/Indiana/Vevay', 'America/Chicago', 'America/Indiana/Tell_City', 'America/Indiana/Knox', 'America/Menominee', 'America/North_Dakota/Center', 'America/North_Dakota/New_Salem', 'America/North_Dakota/Beulah', 'America/Denver', 'America/Boise', 'America/Phoenix', 'America/Los_Angeles', 'America/Anchorage', 'America/Juneau', 'America/Sitka', 'America/Metlakatla', 'America/Yakutat', 'America/Nome', 'America/Adak', 'Pacific/Honolulu'],
    "UY": ['America/Montevideo'],
    "UZ": ['Asia/Samarkand', 'Asia/Tashkent'],
    "VA": ['Europe/Vatican'],
    "VC": ['America/St_Vincent'],
    "VE": ['America/Caracas'],
    "VG": ['America/Tortola'],
    "VI": ['America/St_Thomas'],
    "VN": ['Asia/Ho_Chi_Minh'],
    "VU": ['Pacific/Efate'],
    "WF": ['Pacific/Wallis'],
    "WS": ['Pacific/Apia'],
    "YE": ['Asia/Aden'],
    "YT": ['Indian/Mayotte'],
    "ZA": ['Africa/Johannesburg'],
    "ZM": ['Africa/Lusaka'],
    "ZW": ['Africa/Harare'],
}


# --- approximate: population weights for multi-zone countries where 'first zone' is not enough ---
TIMEZONE_WEIGHTS: Dict[str, Dict[str, float]] = {
    "US": {"America/New_York": 45, "America/Chicago": 28, "America/Los_Angeles": 16,
           "America/Denver": 5, "America/Phoenix": 3, "America/Anchorage": 0.5,
           "Pacific/Honolulu": 0.5},
    "CA": {"America/Toronto": 55, "America/Vancouver": 18, "America/Edmonton": 12,
           "America/Winnipeg": 4, "America/Halifax": 6, "America/Regina": 3},
    "AU": {"Australia/Sydney": 32, "Australia/Melbourne": 26, "Australia/Brisbane": 20,
           "Australia/Perth": 11, "Australia/Adelaide": 7, "Australia/Hobart": 2,
           "Australia/Darwin": 1},
    "BR": {"America/Sao_Paulo": 78, "America/Bahia": 7, "America/Fortaleza": 6,
           "America/Manaus": 3, "America/Recife": 4, "America/Belem": 2},
    "RU": {"Europe/Moscow": 60, "Asia/Yekaterinburg": 10, "Asia/Novosibirsk": 8,
           "Asia/Krasnoyarsk": 5, "Europe/Samara": 6, "Asia/Vladivostok": 4,
           "Asia/Irkutsk": 4, "Europe/Kaliningrad": 3},
    "MX": {"America/Mexico_City": 80, "America/Monterrey": 8, "America/Tijuana": 6,
           "America/Cancun": 4, "America/Chihuahua": 2},
    "ID": {"Asia/Jakarta": 80, "Asia/Makassar": 12, "Asia/Jayapura": 3,
           "Asia/Pontianak": 5},
    # tzdata lists the wrong zone first for these two
    "UA": {"Europe/Kyiv": 100},
    "UZ": {"Asia/Tashkent": 70, "Asia/Samarkand": 30},
}

# --- curated: usual navigator.languages per country ------------------------------
COUNTRY_LANGUAGES: Dict[str, List[str]] = {
    "US": ["en-US", "en"], "GB": ["en-GB", "en"], "CA": ["en-CA", "en"],
    "AU": ["en-AU", "en"], "IE": ["en-IE", "en"], "NZ": ["en-NZ", "en"],
    "DE": ["de-DE", "de"], "AT": ["de-AT", "de"], "CH": ["de-CH", "de"],
    "FR": ["fr-FR", "fr"], "BE": ["nl-BE", "nl"], "NL": ["nl-NL", "nl"],
    "ES": ["es-ES", "es"], "MX": ["es-MX", "es"], "AR": ["es-AR", "es"],
    "CO": ["es-CO", "es"], "CL": ["es-CL", "es"], "PT": ["pt-PT", "pt"],
    "BR": ["pt-BR", "pt"], "IT": ["it-IT", "it"], "PL": ["pl-PL", "pl"],
    "CZ": ["cs-CZ", "cs"], "RO": ["ro-RO", "ro"], "SE": ["sv-SE", "sv"],
    "NO": ["nb-NO", "nb"], "DK": ["da-DK", "da"], "FI": ["fi-FI", "fi"],
    "GR": ["el-GR", "el"], "TR": ["tr-TR", "tr"], "RU": ["ru-RU", "ru"],
    "UA": ["uk-UA", "uk"], "JP": ["ja-JP", "ja"], "KR": ["ko-KR", "ko"],
    "CN": ["zh-CN", "zh"], "TW": ["zh-TW", "zh"], "HK": ["zh-HK", "zh"],
    "ID": ["id-ID", "id"], "TH": ["th-TH", "th"], "VN": ["vi-VN", "vi"],
    "SA": ["ar-SA", "ar"], "AE": ["ar-AE", "ar"], "EG": ["ar-EG", "ar"],
    "IL": ["he-IL", "he"],
    # English is the usual browser UI language in these markets
    "PK": ["en-US", "en"], "IN": ["en-US", "en"], "BD": ["en-US", "en"],
    "NG": ["en-US", "en"], "PH": ["en-US", "en"], "ZA": ["en-ZA", "en"],
    "SG": ["en-SG", "en"], "MY": ["en-US", "en"],
}
DEFAULT_LANGUAGES: List[str] = ["en-US", "en"]

# --- heuristic -----------------------------------------------------------------
ENGLISH_FALLBACK_PROBABILITY = 0.5

# Small pool used when no country is given.
FALLBACK_LOCALES: Dict[str, Tuple[List[str], List[str]]] = {
    "en-US": (["en-US", "en"], ["America/New_York", "America/Chicago", "America/Los_Angeles"]),
    "en-GB": (["en-GB", "en"], ["Europe/London"]),
    "de-DE": (["de-DE", "de", "en-US", "en"], ["Europe/Berlin"]),
    "fr-FR": (["fr-FR", "fr", "en-US", "en"], ["Europe/Paris"]),
    "es-ES": (["es-ES", "es", "en-US", "en"], ["Europe/Madrid"]),
}


def build_accept_language(languages: Sequence[str]) -> str:
    """Chrome-style Accept-Language: ``de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7``."""
    parts = [languages[0]]
    for i, lang in enumerate(languages[1:], start=1):
        parts.append("%s;q=%.1f" % (lang, max(1.0 - 0.1 * i, 0.1)))
    return ",".join(parts)


def pick_timezone(country: str, rng: random.Random) -> str:
    zones = COUNTRY_TIMEZONES[country]
    weights = TIMEZONE_WEIGHTS.get(country)
    if weights:
        names = [z for z in zones if z in weights] or zones
        return rng.choices(names, weights=[weights.get(z, 1) for z in names])[0]
    return zones[0]  # tzdata lists the main zone of a country first


def locale_for(country: str, rng: random.Random) -> Tuple[List[str], str, str]:
    """(languages, timezone, accept_language) for a proxy exit country (ISO alpha-2)."""
    country = country.upper()
    if country not in COUNTRY_TIMEZONES:
        raise ValueError("unknown country code: %r" % country)
    languages = list(COUNTRY_LANGUAGES.get(country, DEFAULT_LANGUAGES))
    if "en" not in languages and rng.random() < ENGLISH_FALLBACK_PROBABILITY:
        languages += ["en-US", "en"]
    return languages, pick_timezone(country, rng), build_accept_language(languages)


def fallback_locale(rng: random.Random) -> Tuple[List[str], str, str]:
    languages, zones = FALLBACK_LOCALES[rng.choice(sorted(FALLBACK_LOCALES))]
    return list(languages), rng.choice(zones), build_accept_language(languages)
