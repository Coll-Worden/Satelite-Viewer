import json
import os
import requests

from datetime import datetime, timezone, timedelta

from skyfield.api import load, EarthSatellite


# ============================================================
# EINSTELLUNGEN
# ============================================================

CELESTRAK_URL = (
    "https://celestrak.org/NORAD/elements/gp.php"
    "?GROUP=active&FORMAT=JSON"
)

# Lokaler Cache mit den CelesTrak-Daten
CACHE_FILE = "satellite_cache.json"

# Ergebnis für SolarDesk
OUTPUT_FILE = "earth_objects.json"

# Nach dieser Zeit darf der Cache erneuert werden.
#
# 2 Tage = 48 Stunden
#
# Dadurch wird CelesTrak nicht ständig abgefragt.
CACHE_MAX_AGE_HOURS = 48

# Mittlerer Erdradius
EARTH_RADIUS_KM = 6371.0


# ============================================================
# CELESTRAK DATEN LADEN
# ============================================================

def download_satellites():

    print("Lade Satellitendaten von CelesTrak...")

    try:

        response = requests.get(
            CELESTRAK_URL,
            timeout=30,
            headers={
                "User-Agent":
                    "SolarDesk/0.1"
            }
        )

        # ----------------------------------------------------
        # 403
        # ----------------------------------------------------

        if response.status_code == 403:

            print()
            print(
                "FEHLER 403: "
                "CelesTrak verweigert die Anfrage."
            )

            print(
                "Versuche vorhandenen Cache zu verwenden."
            )

            return None

        # ----------------------------------------------------
        # Andere HTTP-Fehler
        # ----------------------------------------------------

        response.raise_for_status()

        # ----------------------------------------------------
        # JSON lesen
        # ----------------------------------------------------

        data = response.json()

        print(
            f"{len(data)} Objekte von "
            f"CelesTrak erhalten."
        )

        return data

    except requests.RequestException as e:

        print()
        print(
            "Fehler beim Abrufen von CelesTrak:"
        )

        print(e)

        print()
        print(
            "Versuche vorhandenen Cache zu verwenden."
        )

        return None


# ============================================================
# CACHE SPEICHERN
# ============================================================

def save_cache(data):

    cache = {

        "saved_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "source":
            "CelesTrak",

        "url":
            CELESTRAK_URL,

        "objects":
            data
    }

    with open(
        CACHE_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            cache,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print(
        f"Cache gespeichert: "
        f"{CACHE_FILE}"
    )


# ============================================================
# CACHE LADEN
# ============================================================

def load_cache():

    if not os.path.exists(
        CACHE_FILE
    ):

        print(
            "Kein Cache vorhanden."
        )

        return None

    try:

        with open(
            CACHE_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            cache = json.load(f)

        saved_at = datetime.fromisoformat(
            cache["saved_at"]
        )

        age = (
            datetime.now(timezone.utc)
            - saved_at
        )

        age_hours = (
            age.total_seconds()
            / 3600
        )

        print()
        print(
            f"Cache gefunden."
        )

        print(
            f"Alter: "
            f"{age_hours:.1f} Stunden"
        )

        # ----------------------------------------------------
        # Cache noch gültig?
        # ----------------------------------------------------

        if (
            age_hours
            <= CACHE_MAX_AGE_HOURS
        ):

            print(
                "Cache ist noch gültig."
            )

            return cache["objects"]

        print(
            "Cache ist veraltet."
        )

        return None

    except Exception as e:

        print(
            "Fehler beim Lesen "
            "des Cache:"
        )

        print(e)

        return None


# ============================================================
# DATEN BESCHAFFEN
# ============================================================

def get_satellite_data():

    # --------------------------------------------------------
    # 1. Erst Cache versuchen
    # --------------------------------------------------------

    cached_data = load_cache()

    if cached_data is not None:

        print(
            f"{len(cached_data)} Objekte "
            f"aus Cache geladen."
        )

        return cached_data

    # --------------------------------------------------------
    # 2. CelesTrak versuchen
    # --------------------------------------------------------

    data = download_satellites()

    if data is not None:

        save_cache(data)

        return data

    # --------------------------------------------------------
    # 3. Alter Cache als Notlösung
    # --------------------------------------------------------

    if os.path.exists(
        CACHE_FILE
    ):

        print()
        print(
            "WARNUNG:"
        )

        print(
            "Verwende alten Cache."
        )

        try:

            with open(
                CACHE_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                cache = json.load(f)

            return cache["objects"]

        except Exception as e:

            print(
                "Cache konnte nicht "
                "geladen werden:"
            )

            print(e)

    # --------------------------------------------------------
    # 4. Gar keine Daten
    # --------------------------------------------------------

    print()
    print(
        "Keine Satellitendaten verfügbar."
    )

    return None


# ============================================================
# SKYFIELD OBJEKTE ERZEUGEN
# ============================================================

def create_satellites(data):

    ts = load.timescale()

    satellites = []

    for item in data:

        try:

            satellite = EarthSatellite.from_omm(
                ts,
                item
            )

            satellites.append({

                "satellite":
                    satellite,

                "name":
                    item.get(
                        "OBJECT_NAME",
                        "UNKNOWN"
                    ),

                "norad_id":
                    int(
                        item["NORAD_CAT_ID"]
                    ),

                "international_designator":
                    item.get(
                        "OBJECT_ID"
                    )
            })

        except Exception as e:

            print(
                f"Überspringe "
                f"{item.get('OBJECT_NAME')}: "
                f"{e}"
            )

    print()
    print(
        f"{len(satellites)} Satelliten "
        f"erfolgreich verarbeitet."
    )

    return satellites, ts


# ============================================================
# ORBIT-TYP
# ============================================================

def get_orbit_type(
    altitude_km
):

    if altitude_km < 2000:

        return "LEO"

    elif altitude_km < 35786:

        return "MEO"

    elif altitude_km < 40000:

        return "GEO"

    else:

        return "HEO"


# ============================================================
# POSITIONEN BERECHNEN
# ============================================================

def calculate_positions(
    satellites,
    ts
):

    now = datetime.now(
        timezone.utc
    )

    t = ts.from_datetime(
        now
    )

    objects = []

    for obj in satellites:

        satellite = obj[
            "satellite"
        ]

        try:

            # ------------------------------------------------
            # Position
            # ------------------------------------------------

            geocentric = satellite.at(
                t
            )

            position = (
                geocentric
                .position
                .km
            )

            x, y, z = position

            # ------------------------------------------------
            # Geschwindigkeit
            # ------------------------------------------------

            velocity = (
                geocentric
                .velocity
                .km_per_s
            )

            vx, vy, vz = velocity

            # ------------------------------------------------
            # Entfernung
            # ------------------------------------------------

            distance = (

                x * x
                + y * y
                + z * z

            ) ** 0.5

            # ------------------------------------------------
            # Höhe
            # ------------------------------------------------

            altitude = (
                distance
                - EARTH_RADIUS_KM
            )

            # ------------------------------------------------
            # Orbit
            # ------------------------------------------------

            orbit_type = get_orbit_type(
                altitude
            )

            # ------------------------------------------------
            # Objekt
            # ------------------------------------------------

            objects.append({

                "name":
                    obj["name"],

                "norad_id":
                    obj["norad_id"],

                "international_designator":
                    obj[
                        "international_designator"
                    ],

                "timestamp":
                    now.isoformat(),

                # --------------------------------------------
                # 3D POSITION
                # --------------------------------------------

                "position_km": {

                    "x": float(x),
                    "y": float(y),
                    "z": float(z)

                },

                # --------------------------------------------
                # GESCHWINDIGKEIT
                # --------------------------------------------

                "velocity_km_s": {

                    "x": float(vx),
                    "y": float(vy),
                    "z": float(vz)

                },

                # --------------------------------------------
                # ENTFERNUNG
                # --------------------------------------------

                "distance_from_earth_km":
                    float(distance),

                # --------------------------------------------
                # HÖHE
                # --------------------------------------------

                "altitude_km":
                    float(altitude),

                # --------------------------------------------
                # ORBIT
                # --------------------------------------------

                "orbit_type":
                    orbit_type
            })

        except Exception as e:

            print(
                f"Fehler bei "
                f"{obj['name']}: {e}"
            )

    return objects


# ============================================================
# JSON SPEICHERN
# ============================================================

def save_json(
    objects
):

    output = {

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "reference":
            "Earth center",

        "coordinate_system":
            "Skyfield Earth-centered",

        "coordinate_unit":
            "km",

        "velocity_unit":
            "km/s",

        "earth_radius_km":
            EARTH_RADIUS_KM,

        "object_count":
            len(objects),

        "objects":
            objects
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            output,
            f,
            indent=2,
            ensure_ascii=False
        )

    print()
    print(
        "=" * 60
    )

    print(
        f"{len(objects)} Objekte gespeichert."
    )

    print(
        f"Datei: {OUTPUT_FILE}"
    )

    print(
        "=" * 60
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print()
    print(
        "=" * 60
    )

    print(
        "SOLARDESK - EARTH OBJECT DATABASE"
    )

    print(
        "=" * 60
    )

    # --------------------------------------------------------
    # Daten laden
    # --------------------------------------------------------

    data = get_satellite_data()

    if data is None:

        print()
        print(
            "Programm beendet."
        )

        return

    # --------------------------------------------------------
    # Skyfield
    # --------------------------------------------------------

    satellites, ts = create_satellites(
        data
    )

    # --------------------------------------------------------
    # Positionen
    # --------------------------------------------------------

    objects = calculate_positions(
        satellites,
        ts
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    save_json(
        objects
    )

    print()
    print(
        "Fertig."
    )


# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    main()

