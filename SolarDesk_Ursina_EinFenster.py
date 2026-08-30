import json
from math import sin, cos, pi
from pathlib import Path

from ursina import *
from ursina.prefabs.editor_camera import EditorCamera

app = Ursina()

# ============================================================
# EINSTELLUNGEN
# ============================================================

KM_TO_UNITS = 1 / 6371
LIST_PAGE_SIZE = 30
SELECTION_SCALE = 0.08
MOON_DISTANCE = 60
MOON_ORBIT_DAYS = 27.321661

window.title = "SolarDesk"
window.color = color.black

# ============================================================
# ERDE
# ============================================================

Erde = Entity(
    model="sphere",
    position=(0, 0, 0),
    color=color.hex("#113A15"),
    scale=2,
)
Erde.wireframe = True

# ============================================================
# GRID
# ============================================================

grid_x_plus = Entity(
    position=(65, 0, 0), model=Grid(40, 40), scale=130,
    rotation=(0, 90, 0), color=color.hex("#525553")
)
grid_x_minus = Entity(
    position=(-65, 0, 0), model=Grid(40, 40), scale=130,
    rotation=(0, 90, 0), color=color.hex("#525553")
)
grid_y_plus = Entity(
    position=(0, 65, 0), model=Grid(40, 40), scale=130,
    rotation=(90, 0, 0), color=color.hex("#525553")
)
grid_y_minus = Entity(
    position=(0, -65, 0), model=Grid(40, 40), scale=130,
    rotation=(90, 0, 0), color=color.hex("#525553")
)
grid_z_plus = Entity(
    position=(0, 0, 65), model=Grid(40, 40), scale=130,
    rotation=(0, 0, 0), color=color.hex("#525553")
)
grid_z_minus = Entity(
    position=(0, 0, -65), model=Grid(40, 40), scale=130,
    rotation=(0, 0, 0), color=color.hex("#525553")
)

# ============================================================
# JSON LADEN
# ============================================================

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent.parent
JSON_FILE = PROJECT_DIR / "earth_objects.json"

if not JSON_FILE.exists():
    JSON_FILE = Path("earth_objects.json")

if not JSON_FILE.exists():
    raise FileNotFoundError(
        f"earth_objects.json wurde nicht gefunden: {JSON_FILE}"
    )

print("Lade:", JSON_FILE)

with open(JSON_FILE, "r", encoding="utf-8") as file:
    data = json.load(file)

objects = data["objects"]
print("Objekte geladen:", len(objects))

# ============================================================
# SATELLITENDATEN
# ============================================================

satellite_data = []
satellite_positions = []

for obj in objects:
    p = obj.get("position_km")
    if not p:
        continue

    try:
        pos = Vec3(
            float(p["x"]) * KM_TO_UNITS,
            float(p["y"]) * KM_TO_UNITS,
            float(p["z"]) * KM_TO_UNITS,
        )
    except (KeyError, TypeError, ValueError):
        continue

    satellite_data.append(obj)
    satellite_positions.append(pos)

print("Gültige Satelliten:", len(satellite_data))

# ============================================================
# SATELLITEN-MESH
# ============================================================

satellite_mesh = Mesh(
    vertices=list(satellite_positions),
    mode="point",
)

satellites = Entity(
    model=satellite_mesh,
    color=color.hex("#EB3F0A"),
)

# ============================================================
# AUSWAHL-MARKER
# ============================================================

selection_marker = Entity(
    model="sphere",
    color=color.red,
    scale=SELECTION_SCALE,
    enabled=False,
)
selection_marker.wireframe = True

# ============================================================
# MOND
# ============================================================

def get_moon_position(days):
    angle = (days / MOON_ORBIT_DAYS) * 2 * pi
    return Vec3(
        cos(angle) * MOON_DISTANCE,
        0,
        sin(angle) * MOON_DISTANCE,
    )

moon = Entity(
    model="sphere",
    position=get_moon_position(0),
    scale=2,
    color=color.hex("#11EED1"),
)
moon.wireframe = True

# ============================================================
# UI - LINKES PANEL
# ============================================================

sidebar = Entity(
    parent=camera.ui,
    model="quad",
    color=color.rgba(10, 12, 15, 235),
    scale=(0.31, 0.92),
    x=-0.84,
    y=0,
)

Text(
    parent=camera.ui,
    text="SOLARDESK",
    origin=(0, 0),
    scale=1.25,
    x=-0.84,
    y=0.42,
)

Text(
    parent=camera.ui,
    text="SATELLITEN",
    origin=(0, 0),
    scale=0.75,
    x=-0.84,
    y=0.365,
)

page_text = Text(
    parent=camera.ui,
    text="",
    origin=(0, 0),
    scale=0.65,
    x=-0.84,
    y=-0.405,
)

list_container = Entity(
    parent=camera.ui,
    x=-0.84,
    y=-0.02,
)

list_buttons = []

# ============================================================
# UI - DETAILPANEL
# ============================================================

detail_panel = Entity(
    parent=camera.ui,
    model="quad",
    color=color.rgba(10, 12, 15, 235),
    scale=(0.42, 0.40),
    x=0.25,
    y=-0.25,
)

detail_title = Text(
    parent=detail_panel,
    text="KEIN SATELLIT AUSGEWÄHLT",
    origin=(-0.5, 0.5),
    x=-0.44,
    y=0.40,
    scale=0.9,
)

detail_text = Text(
    parent=detail_panel,
    text="Klicke links auf einen Satelliten.",
    origin=(-0.5, 0.5),
    x=-0.44,
    y=0.22,
    scale=0.65,
)

def close_details():
    selection_marker.enabled = False
    detail_title.text = "KEIN SATELLIT AUSGEWÄHLT"
    detail_text.text = "Klicke links auf einen Satelliten."

Button(
    parent=detail_panel,
    text="X",
    model="quad",
    scale=(0.10, 0.12),
    x=0.40,
    y=0.40,
    color=color.rgba(180, 40, 40, 230),
    on_click=close_details,
)

# ============================================================
# SATELLIT AUSWÄHLEN
# ============================================================

selected_index = None

def select_satellite(index):
    global selected_index

    if index < 0 or index >= len(satellite_data):
        return

    selected_index = index

    satellite = satellite_data[index]
    position = satellite_positions[index]

    # Roter Marker
    selection_marker.position = position
    selection_marker.enabled = True

    # Daten
    name = satellite.get("name", "Unbekannt")
    norad_id = satellite.get("norad_id", "Keine Angabe")

    p = satellite.get("position_km", {})

    x = p.get("x", 0)
    y = p.get("y", 0)
    z = p.get("z", 0)

    velocity = satellite.get("velocity_km_s")

    if velocity:
        vx = velocity.get("x", 0)
        vy = velocity.get("y", 0)
        vz = velocity.get("z", 0)

        velocity_text = (
            f"Geschwindigkeit:\n"
            f"X: {vx:.3f} km/s\n"
            f"Y: {vy:.3f} km/s\n"
            f"Z: {vz:.3f} km/s\n"
        )
    else:
        velocity_text = ""

    # Detailanzeige
    detail_title.text = str(name)

    detail_text.text = (
        f"NORAD ID: {norad_id}\n"
        f"\n"
        f"Position:\n"
        f"X: {x:.2f} km\n"
        f"Y: {y:.2f} km\n"
        f"Z: {z:.2f} km\n"
        f"\n"
        f"{velocity_text}"
        f"\n"
        f"Ursina Position:\n"
        f"X: {position.x:.4f}\n"
        f"Y: {position.y:.4f}\n"
        f"Z: {position.z:.4f}"
    )

# ============================================================
# PAGINIERTE SATELLITENLISTE
# ============================================================

current_page = 0

def clear_satellite_buttons():
    for button in list_buttons:
        destroy(button)
    list_buttons.clear()

def build_satellite_list():
    clear_satellite_buttons()

    total = len(satellite_data)

    if total == 0:
        page_text.text = "Keine Satelliten"
        return

    start = current_page * LIST_PAGE_SIZE
    end = min(start + LIST_PAGE_SIZE, total)

    for local_index in range(start, end):
        satellite = satellite_data[local_index]
        name = satellite.get("name", f"Objekt {local_index}")

        if len(name) > 27:
            name = name[:24] + "..."

        row = local_index - start

        button = Button(
            parent=list_container,
            text=name,
            model="quad",
            color=color.rgba(35, 40, 45, 230),
            highlight_color=color.rgba(65, 75, 85, 240),
            pressed_color=color.rgba(100, 50, 30, 240),
            scale=(0.28, 0.025),
            y=0.29 - row * 0.0205,
        )

        button.on_click = lambda i=local_index: select_satellite(i)
        list_buttons.append(button)

    total_pages = max(
        1,
        (total + LIST_PAGE_SIZE - 1) // LIST_PAGE_SIZE
    )

    page_text.text = (
        f"Seite {current_page + 1}/{total_pages}   "
        f"({total} Objekte)"
    )

def next_page():
    global current_page

    total_pages = max(
        1,
        (len(satellite_data) + LIST_PAGE_SIZE - 1)
        // LIST_PAGE_SIZE
    )

    if current_page < total_pages - 1:
        current_page += 1
        build_satellite_list()

def previous_page():
    global current_page

    if current_page > 0:
        current_page -= 1
        build_satellite_list()

Button(
    parent=camera.ui,
    text="←",  # Alternativ: "<-"
    model="quad",
    scale=(0.055, 0.045),
    x=-0.93,
    y=-0.445,
    color=color.rgba(40, 45, 50, 240),
    on_click=previous_page,
)

Button(
    parent=camera.ui,
    text="→",  # Alternativ: "->"
    model="quad",
    scale=(0.055, 0.045),
    x=-0.75,
    y=-0.445,
    color=color.rgba(40, 45, 50, 240),
    on_click=next_page,
)

build_satellite_list()

# ============================================================
# UPDATE
# ============================================================

def update():
    # Später hier deine echte Simulationszeit einsetzen.
    days = 0
    moon.position = get_moon_position(days)

    direction = camera.forward

    grid_x_plus.enabled = direction.x > 0
    grid_x_minus.enabled = not grid_x_plus.enabled

    grid_y_plus.enabled = direction.y > 0
    grid_y_minus.enabled = not grid_y_plus.enabled

    grid_z_plus.enabled = direction.z > 0
    grid_z_minus.enabled = not grid_z_plus.enabled

# ============================================================
# INPUT
# ============================================================

def input(key):
    if key == "escape":
        application.quit()

# ============================================================
# KAMERA
# ============================================================

editor_camera = EditorCamera()

# ============================================================
# START
# ============================================================

print("Mondposition:", get_moon_position(0))
print("SolarDesk gestartet.")

app.run()
