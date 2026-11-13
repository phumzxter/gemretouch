from collections import Counter
from pathlib import Path
import base64
import bisect
import colorsys
import hashlib
import json
import os
import shutil
import tempfile
import time
import uuid
import zipfile
import cv2
import streamlit as st
import streamlit.components.v1 as components
import gem_core as gc
import sysutil

st.set_page_config(page_title="GemRetouch", page_icon="💎", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown("""<style>
:root {--bar:#0e121b; --bar2:#141a27; --bg:#0e1117; --panel:#151a24; --line:#262d3d; --soft:#1c2230; --acc:#7aa2ff; --mut:#8f98ad; --txt:#e6e9ef;}
#MainMenu, footer {visibility: hidden;}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"] {display: none !important;}
[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {display: none !important;}
.block-container, [data-testid="stMainBlockContainer"] {
    padding-top: 1rem !important; padding-bottom: 1rem !important; max-width: 100%;}
div.stButton > button {width: 100%; border-radius: 10px; border: 1px solid var(--line);
    background: var(--soft); transition: all .12s;}
div.stButton > button:hover {border-color: var(--acc); color: #fff;}
[data-testid="stImage"] img {border-radius: 8px; height: 72px !important; width: 100% !important; object-fit: cover;}
/* ---- tabs + panel: one seamless block ---- */
.st-key-rightcol {gap: 0 !important;}
.st-key-toolbar {margin-bottom: 0; position: relative; z-index: 2;}
.st-key-toolbar [data-testid="stHorizontalBlock"] {gap: 3px !important; border-bottom: 1px solid var(--line); flex-wrap: nowrap !important;}
.st-key-toolbar [data-testid="stColumn"] {min-width: 0 !important; flex: 1 1 0 !important;}
.st-key-toolbar .stButton, .st-key-toolbar .stButton > div, .st-key-toolbar .stTooltipIcon,
.st-key-toolbar .stTooltipHoverTarget, .st-key-toolbar .stElementContainer {width: 100% !important;}
.st-key-toolbar .stTooltipHoverTarget {display: flex;}
.st-key-toolbar [data-testid^="stBaseButton"] {width: 100% !important;}
.st-key-toolbar button {height: 3rem; font-size: 1.3rem; padding: 0; width: 100%;
    border-radius: 12px 12px 0 0; border: 1px solid transparent; border-bottom: none;
    background: transparent; color: var(--mut); filter: grayscale(.6) opacity(.75);}
.st-key-toolbar button:hover {background: var(--soft); filter: none; border-color: var(--line);
    border-bottom: none; color: #fff;}
.st-key-toolbar button[kind="primary"],
.st-key-toolbar button[data-testid="stBaseButton-primary"] {
    background: var(--panel) !important; border: 1px solid var(--line) !important; border-bottom: none !important;
    box-shadow: inset 0 3px 0 var(--acc); margin-bottom: -1px; height: calc(3rem + 1px); filter: none; color: #fff;}
[data-testid="stColumn"]:has(.st-key-rightcol) > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(.st-key-rightcol) {flex: 1 1 auto; display: flex; flex-direction: column;}
.st-key-rightcol {flex: 1 1 auto;}
.st-key-rightcol > [data-testid="stLayoutWrapper"]:has(> .st-key-optpanel) {flex: 1 1 0; min-height: 360px; display: flex; flex-direction: column; margin-bottom: 1rem;}
.st-key-optpanel {flex: 1 1 0 !important; height: auto !important; min-height: 0; overflow-y: auto !important;
    background: var(--panel) !important; border: 1px solid var(--line) !important; border-top: none !important;
    border-radius: 0 0 14px 14px !important; padding: .6rem .9rem !important;}
.st-key-optpanel [data-testid="stHorizontalBlock"] {flex-wrap: wrap; gap: .6rem;}
.st-key-optpanel [data-testid="stColumn"] {min-width: 120px !important; flex: 1 1 120px !important;}
/* ---- panel content ---- */
.sec {font-size: .72rem; letter-spacing: .12em; text-transform: uppercase; color: var(--acc); font-weight: 700;
    margin: 1.1rem 0 .35rem; padding-bottom: .3rem; border-bottom: 1px solid var(--line);}
.sec:first-child {margin-top: .2rem;}
.sep {height: 1px; background: var(--line); margin: 1.2rem -.6rem .4rem;}
.tips {display: flex; flex-wrap: wrap; gap: .4rem; margin: .3rem 0 .2rem;}
.tips span {background: var(--soft); border: 1px solid var(--line); border-radius: 999px; padding: .15rem .65rem;
    font-size: .78rem; color: var(--mut);}
.tips b {color: var(--txt);}
.st-key-optpanel [data-testid="stWidgetLabel"] p {font-size: .8rem; color: var(--mut);}
.st-key-optpanel input, .st-key-optpanel [data-baseweb="select"] > div {border-radius: 9px !important;}
.st-key-optpanel [data-testid="stCaptionContainer"] {color: var(--mut);}
/* radio -> pill buttons */
[data-testid="stRadio"] [role="radiogroup"] {flex-direction: row !important; flex-wrap: wrap; gap: .35rem;}
[data-testid="stRadioOption"] {background: var(--soft); border: 1px solid var(--line); border-radius: 999px;
    padding: .2rem .8rem; margin: 0 !important; cursor: pointer; transition: all .12s;}
[data-testid="stRadioOption"] > div > div:first-child {display: none !important;}
[data-testid="stRadioOption"] p {font-size: .85rem;}
[data-testid="stRadioOption"]:hover {border-color: var(--acc);}
[data-testid="stRadioOption"][data-selected="true"] {background: rgba(122,162,255,.16); border-color: var(--acc); color: #fff;}
/* toggles */
[data-testid="stToggle"] {padding: .2rem 0;}
[data-testid="stToggle"] label p {font-size: .9rem; color: var(--txt);}
/* stone name bar + picture */
.st-key-namebar {position: relative; background: transparent; border: 0; height: 49px; box-sizing: border-box; padding: .3rem 0; overflow: visible;}
.st-key-namebar [data-testid="stHorizontalBlock"] {gap: .3rem !important; align-items: center !important; flex-wrap: nowrap !important; height: 100%;}
.st-key-namebar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {min-width: 0 !important; width: auto !important;}
.st-key-namebar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) {flex: 0 1 11rem !important; position: relative;}
.st-key-namebar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {position: absolute !important; left: 50%; top: 0; transform: translateX(-50%); flex: none !important; width: auto !important; height: 100%; pointer-events: none;}
.st-key-namebar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {flex: 0 0 7.2rem !important; margin-left: auto;}
.st-key-namebar [data-testid="stVerticalBlock"] {gap: 0 !important;}
.st-key-namebar .stElementContainer, .st-key-namebar .stButton, .st-key-namebar .stTooltipHoverTarget {width: 100% !important; margin: 0 !important;}
.st-key-namebar .stTooltipHoverTarget {display: flex;}
.st-key-namebar button {height: 2.4rem !important; min-height: 0 !important; width: 100% !important; padding: 0 .2rem !important; background: var(--bar2); border: 1px solid var(--line); border-radius: 10px; color: var(--txt); font-weight: 700;}
.st-key-namebar .st-key-prevstone, .st-key-namebar .st-key-nextstone {position: absolute !important; right: 6px; width: 24px !important; z-index: 4;}
.st-key-namebar .st-key-prevstone {top: 4px;} .st-key-namebar .st-key-nextstone {top: 19px;}
.st-key-namebar .st-key-prevstone button, .st-key-namebar .st-key-nextstone button {height: 15px !important; width: 24px !important; padding: 0 !important; font-size: .5rem !important; line-height: 1; background: transparent !important; border: 0 !important; color: var(--mut); border-radius: 6px;}
.st-key-namebar .st-key-prevstone button:hover:not(:disabled), .st-key-namebar .st-key-nextstone button:hover:not(:disabled) {background: var(--soft) !important; color: var(--acc);}
.st-key-namebar button:disabled {opacity: .35;}
.st-key-namebar .st-key-mk_new button, .st-key-namebar .st-key-mk_join button, .st-key-namebar .st-key-mk_none button {background: var(--bar2); border: 1px solid var(--line); color: var(--txt); border-radius: 10px; font-size: .86rem; font-weight: 600; white-space: nowrap; box-shadow: none; gap: .35rem;}
.st-key-namebar .st-key-mk_new button:hover:not(:disabled), .st-key-namebar .st-key-mk_join button:hover:not(:disabled) {background: var(--soft); border-color: var(--acc); color: var(--txt);}
.st-key-namebar .st-key-mk_new button span[data-testid="stIconMaterial"], .st-key-namebar .st-key-mk_join button span[data-testid="stIconMaterial"], .st-key-namebar .st-key-mk_none button span[data-testid="stIconMaterial"] {font-size: 1.05rem; color: var(--acc);}
[class*="st-key-nm_"] [data-testid="stTextInputRootElement"], [class*="st-key-nm_"] [data-baseweb="base-input"], [class*="st-key-nm_"] [data-baseweb="input"] {height: 2.4rem !important; min-height: 0 !important; background: var(--bar2) !important; border-color: var(--line) !important; border-radius: 10px !important; box-sizing: border-box;}
[class*="st-key-nm_"] [data-testid="stTextInputRootElement"]:hover, [class*="st-key-nm_"] [data-testid="stTextInputRootElement"]:focus-within {border-color: var(--acc) !important; background: var(--panel) !important;}
[class*="st-key-nm_"] input {height: 100% !important; font-weight: 700; font-size: 1.05rem; text-align: left; letter-spacing: .02em; padding: 0 2.2rem 0 .8rem;}
.st-key-namebar [data-testid="stMarkdownContainer"] p {margin: 0 !important;}
.sdots {display: flex; gap: .55rem; justify-content: center; align-items: center; height: 2.4rem; position: relative; top: 5px;}
.sdots i {display: block; width: .5rem; height: .5rem; border-radius: 50%; background: var(--line); transition: all .2s;}
.sdots i.on {background: var(--acc); box-shadow: 0 0 0 3px rgba(91,140,255,.2), 0 0 10px 2px var(--acc);}
[data-testid="stElementContainer"]:has(iframe[title*="gem_viewer"]) {margin-top: -15px;}
.st-key-prev button, .st-key-next button {font-weight: 700; height: 2.2rem !important; width: 100% !important; font-size: 1.1rem; line-height: 1; background: var(--bar2); border: 1px solid var(--line); border-radius: 10px;}
.st-key-prev .stButton, .st-key-next .stButton, .st-key-prev .stTooltipHoverTarget, .st-key-next .stTooltipHoverTarget {width: 100% !important; display: flex;}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > * > .st-key-prev) > [data-testid="stColumn"]:nth-child(2), [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > * > .st-key-prev) > [data-testid="stColumn"]:last-child {flex: 0 0 2rem !important; width: 2rem !important;}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > * > .st-key-prev) > [data-testid="stColumn"]:first-child {flex: 0 0 2.8rem !important; width: 2.8rem !important; border-right: 1px solid var(--line); padding-right: .4rem;}
[data-testid="stColumn"]:has(> [data-testid="stVerticalBlock"] > .st-key-sprev) > [data-testid="stVerticalBlock"] {gap: 0 !important;}
.st-key-sprev, .st-key-snext, .st-key-sprev .stButton, .st-key-snext .stButton, .st-key-sprev .stTooltipHoverTarget, .st-key-snext .stTooltipHoverTarget {width: 100% !important;}
.st-key-sprev .stTooltipHoverTarget, .st-key-snext .stTooltipHoverTarget {display: flex;}
.st-key-sprev button, .st-key-snext button {height: 17px !important; min-height: 0 !important; width: 100% !important; padding: 0 !important; font-size: .55rem !important; line-height: 1; background: var(--bar2); border: 1px solid var(--line); border-radius: 7px; color: var(--mut);}
.st-key-sprev button:hover:not(:disabled), .st-key-snext button:hover:not(:disabled) {color: var(--acc); border-color: var(--acc);}
[data-testid="stElementContainer"]:has(.stnum) {height: 22px !important; display: flex !important; align-items: center; justify-content: center;}
[data-testid="stElementContainer"]:has(.stnum) [data-testid="stMarkdown"], [data-testid="stElementContainer"]:has(.stnum) [data-testid="stMarkdownContainer"] {height: auto !important; margin: 0 !important; width: 100%;}
.stnum {text-align: center; line-height: 1.05; padding: .1rem 0; color: var(--mut); font-size: .68rem; white-space: nowrap;}
.stnum b {display: inline; font-size: 1.05rem; margin-right: 1px; color: var(--txt); font-weight: 700;}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > * > .st-key-prev) [data-testid="stVerticalBlock"] {justify-content: center;}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > * > .st-key-prev) {background: var(--bar); border: 1px solid var(--line); border-radius: 12px; padding: .5rem; box-sizing: border-box; height: 90px; align-items: center; overflow: hidden;}
[data-testid="stColumn"]:has([class*="st-key-thb_"]) img {border-radius: 8px; border: 1px solid var(--line);}
[data-testid="stElementContainer"]:has(.adbox) {height: 90px !important; display: block !important; margin: 0 !important;}
[data-testid="stElementContainer"]:has(.adbox) [data-testid="stMarkdown"], [data-testid="stElementContainer"]:has(.adbox) [data-testid="stMarkdownContainer"] {height: 100% !important; margin: 0 !important;}
.adbox {height: 90px !important; box-sizing: border-box; margin: 0; display: flex; align-items: center; justify-content: center; border: 1px dashed var(--line); border-radius: 12px; background: var(--bar); color: var(--mut); font-size: .9rem; letter-spacing: .02em;}
.adbox b {color: var(--txt); font-weight: 600; margin-left: .4rem;}
iframe[title*="gem_viewer"] {display: block; border-radius: 12px; border: 1px solid var(--line);}
[data-testid="stColumn"]:has([class*="st-key-thb_"]) > [data-testid="stVerticalBlock"] {position: relative;}
[class*="st-key-thb_"] {position: absolute !important; top: 5px; left: 5px; width: auto !important; z-index: 3;}
[class*="st-key-thb_"] .stButton {width: auto !important;}
[class*="st-key-thb_"] button {min-height: 0; height: 1.4rem; width: 1.4rem; padding: 0; border-radius: 50%; font-size: .72rem; font-weight: 700; background: rgba(14,17,23,.75); color: #e6e9ef; border: 1px solid rgba(255,255,255,.28);}
[class*="st-key-thb_"] button[data-testid="stBaseButton-primary"] {background: var(--acc); color: #fff; border-color: transparent; box-shadow: 0 0 10px var(--acc);}
.dust-note {text-align: right; color: var(--mut); font-size: .85rem; margin: .1rem .3rem .4rem;}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > * > .st-key-prev),
.st-key-topbar [data-testid="stHorizontalBlock"] {flex-wrap: nowrap !important;}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] > * > .st-key-prev) > [data-testid="stColumn"],
.st-key-topbar [data-testid="stColumn"] {min-width: 0 !important;}
@media (max-width: 900px) {
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-rightcol) {flex-wrap: wrap !important;}
[data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-rightcol) > [data-testid="stColumn"] {min-width: 100% !important; flex: 1 1 100% !important;}
.st-key-optpanel {height: auto !important; min-height: 0 !important; flex: 0 0 auto !important; overflow-y: visible !important;}
.st-key-rightcol > [data-testid="stLayoutWrapper"]:has(> .st-key-optpanel) {flex: 0 0 auto; min-height: 0;}
.block-container, [data-testid="stMainBlockContainer"] {padding-left: .6rem !important; padding-right: .6rem !important;}
.st-key-topbar {padding: .3rem .5rem;}
.brand {font-size: 1.1rem; gap: .45rem;}
.brand .logo {width: 2rem; height: 2rem;}
.st-key-topbar .stButton button {padding: 0 .55rem; font-size: .8rem; height: 2.1rem;}
.st-key-toolbar button {height: 2.6rem; font-size: 1.1rem;}
}
.st-key-prev button, .st-key-next button {padding: 0 .2rem !important;}
@media (max-width: 640px) {
.st-key-topbar [data-testid="stHorizontalBlock"] {flex-wrap: wrap !important; row-gap: .3rem;}
.st-key-topbar [data-testid="stColumn"] {flex: 1 1 22% !important; min-width: 22% !important;}
.st-key-topbar .stButton button {padding: 0 .1rem !important; font-size: .74rem !important;}
.st-key-topbar [data-testid="stColumn"]:first-child {flex: 1 1 100% !important; min-width: 100% !important;}
.st-key-namebar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) {flex: 0 0 5.6rem !important;}
.st-key-namebar .st-key-mk_new button, .st-key-namebar .st-key-mk_join button, .st-key-namebar .st-key-mk_none button {font-size: .76rem !important;}
.sdots {gap: .35rem;}
.st-key-namebar [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) {flex: 0 1 7.5rem !important;}
}
/* top bar */
.st-key-topbar {background: linear-gradient(90deg, var(--bar), var(--bar2)); border: 1px solid var(--line); border-radius: 16px;
    padding: .45rem 1rem; margin-bottom: .7rem; box-shadow: 0 6px 22px rgba(0,0,0,.18);}
.brand {display: flex; align-items: center; gap: .65rem; font-size: 1.3rem; line-height: 1; margin: 0 0 1rem; color: var(--txt);}
.st-key-topbar [data-testid="stHorizontalBlock"] {align-items: center !important;}
.st-key-topbar [data-testid="stMarkdownContainer"] p {margin: 0 !important;}
.brand .logo {display: inline-flex; flex: none; width: 2.4rem; height: 2.4rem; border-radius: 12px; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #5b8cff, #8e6bff); box-shadow: 0 4px 14px rgba(91,140,255,.45);}
.brand .bname {font-weight: 300;}
.brand .bname b {font-weight: 800; background: linear-gradient(90deg, #7aa2ff, #b18cff); -webkit-background-clip: text;
    background-clip: text; color: transparent;}
.st-key-topbar .stButton button {height: 2.5rem; border-radius: 999px; background: transparent; border: 1px solid transparent;
    color: var(--mut); font-weight: 600; padding: 0 1rem;}
.st-key-topbar .stButton button:hover {color: var(--txt); background: var(--soft); border-color: var(--line);}
.st-key-topbar .stButton button[data-testid="stBaseButton-primary"] {background: linear-gradient(135deg, #5b8cff, #8e6bff); color: #fff;
    border: none; box-shadow: 0 4px 14px rgba(91,140,255,.4);}
.st-key-topbar button[data-testid="stBaseButton-primary"]:hover {filter: brightness(1.1); color: #fff;}
</style>""", unsafe_allow_html=True)

ss = st.session_state
VIEWER = components.declare_component("gem_viewer", path=str(Path(__file__).parent / "gem_viewer"))
# Web mode: running on a server (Streamlit Community Cloud, or GEM_WEB=1) instead of on your own computer.
WEB = bool(os.environ.get("GEM_WEB")) or Path("/mount/src").exists() or st.query_params.get("web") == "1"
if WEB:
    ss.setdefault("sid", uuid.uuid4().hex[:12])
    _root = Path(tempfile.gettempdir()) / "gemretouch"
    _root.mkdir(exist_ok=True)
    for _d in _root.iterdir():          # forget other visitors' photos after 3 hours
        try:
            if time.time() - _d.stat().st_mtime > 3 * 3600 and _d.name != ss["sid"]:
                shutil.rmtree(_d, ignore_errors=True)
        except Exception:
            pass
    INBOX = _root / ss["sid"] / "photos"
    INBOX.mkdir(parents=True, exist_ok=True)
else:
    INBOX = Path(__file__).parent / "inbox"
SETTINGS = Path(os.environ.get("GEM_SETTINGS", Path(__file__).parent / "settings.json"))
EMOJI = {"Red": "🔴", "Orange": "🟠", "Yellow": "🟡", "Green": "🟢",
         "Aqua": "🩵", "Blue": "🔵", "Purple": "🟣", "Magenta": "🩷"}
TOOLS = [("crop", "✂️", "Crop"), ("dust", "✨", "Dust"), ("heal", "🩹", "Heal"), ("color", "🎨", "Color"),
         ("stones", "💎", "Stones"), ("export", "💾", "Export"), ("settings", "⚙️", "Settings")]
SPACE_TAP, SPACE_HOLD = "Tap to flip Original / Edited", "Hold to peek at the Original"
MODE_COUNT, MODE_PAUSE = "Every N photos", "By pause between shots (automatic)"
SCOPE_ALL, SCOPE_ONE = "All stones", "Only the current stone"
HEAL_SMART, HEAL_SMOOTH = "Smart (matches the texture)", "Smooth fill"

# default value of every setting (settings survive while their panel is closed)
UI = dict(src="Drop photos here" if WEB else "Folder on my computer", folder="", view_h=520, auto_fit=True,
          space_mode=SPACE_TAP, start_view="Edited", keep_view=False, light_mode=False, show_tag=True,
          group_mode=MODE_PAUSE, per_stone=5, gap=45, order="Time taken",
          prefix="stone_", start=1, digits=3, sep="_", labels="", subfolders=False,
          crop=True, padding=15, dx=0, dy=0, out_size=2000,
          dust=True, dust_mode="Both", dust_thr=18, dust_area=250,
          gem_only=True, gem_margin=3, show_mask=False, show_gem=False,
          brush=16, heal_method=HEAL_SMART, sat=100, band="Red",
          outdir="", fmt=".jpg", quality=95, scope=SCOPE_ALL, overwrite=False)

# remembered between sessions
if "settings_loaded" not in ss:
    ss["settings_loaded"] = True
    try:
        if WEB:
            raise RuntimeError("settings are per visit on the web")
        for k, v in json.loads(SETTINGS.read_text()).items():
            if k.startswith("p_") and k not in ss:
                ss[k] = v
    except Exception:
        pass


# ------------------------------------------------------------------ helpers
def keep(kind, label, key, default, *args, **kw):
    """A widget whose value is remembered even while its panel is closed."""
    wk, pk = "w_" + key, "p_" + key
    if wk not in ss:
        ss[wk] = ss.get(pk, default)
    v = getattr(st, kind)(label, *args, key=wk, **kw)
    ss[pk] = v
    return v


def U(key):
    return ss.get("p_" + key, UI[key])


def show(rgb, caption=None):
    try:
        st.image(rgb, caption=caption, width="stretch")
    except Exception:  # older Streamlit versions
        st.image(rgb, caption=caption, use_container_width=True)


@st.cache_resource(show_spinner=False, max_entries=3)
def cached_load(path, mtime):
    return gc.load_image(path)


@st.cache_resource(show_spinner=False)
def cached_thumb(path, mtime):
    return cv2.cvtColor(gc.load_thumb(path), cv2.COLOR_BGR2RGB)


@st.cache_data(show_spinner=False)
def times_for(keys):
    """keys = ((path, modified time), ...) -> {path: time the photo was taken}"""
    return {p: gc.capture_time(p) for p, _ in keys}


def to_b64(img, max_side=2000, quality=90):
    img = gc.fit(img, max_side)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buf.tobytes()).decode()


def swatch(center, h, s, l):
    def hx(hue, sat, lum):
        r, g, b = colorsys.hls_to_rgb((hue % 360) / 360, min(max(lum, 0), 1), min(max(sat, 0), 1))
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
    box = "width:36px;height:36px;border-radius:8px;background:"
    return (f"<div style='display:flex;gap:10px;align-items:center;padding-top:1.6rem'>"
            f"<div style='{box}{hx(center, .8, .5)}'></div>➜"
            f"<div style='{box}{hx(center + h, .8 * (1 + s / 100), .5 * (1 + l / 100))}'></div></div>")


def toggle_tool(k):
    ss.tool = k


def go(delta, n):
    ss.pos = min(max(ss.pos + delta, 1), n)


def jump(pos):
    ss.pos = pos


def go_stone(delta):
    starts = ss.get("_stone_starts") or [0]
    cur = max(0, bisect.bisect_right(starts, ss.pos - 1) - 1)
    ss.pos = starts[min(max(cur + delta, 0), len(starts) - 1)] + 1


def on_stone_slider():
    starts = ss.get("_stone_starts") or [0]
    ss.pos = starts[min(max(int(ss.stone_sl) - 1, 0), len(starts) - 1)] + 1


def set_name(first, wk):
    ss.names[first] = str(ss.get(wk, "")).strip()


def mark_new(path):
    ss.force_new.add(path)
    ss.force_join.discard(path)


def mark_join(path):
    ss.force_join.add(path)
    ss.force_new.discard(path)


def browse(key):
    p = sysutil.pick_folder()
    if p:
        ss["w_" + key] = p


def undo_heal():
    h = ss.setdefault("heals", {}).get(ss.get("cur_path"))
    if h:
        h.pop()


def clear_heal():
    ss.setdefault("heals", {})[ss.get("cur_path")] = []


# ------------------------------------------------------------------- state
ss.setdefault("tool", "stones")
if ss.tool not in [t[0] for t in TOOLS]:
    ss.tool = "stones"
ss.setdefault("pos", 1)
ss.setdefault("heals", {})
ss.setdefault("seen_sids", set())
ss.setdefault("names", {})
ss.setdefault("force_new", set())
ss.setdefault("force_join", set())
if "_goto" in ss:
    ss.pos = ss.pop("_goto")


# ------------------------------------------------------------------ photos / stones
def get_files():
    if not WEB and U("src").startswith("Folder"):
        t = U("folder").strip().strip('"').strip("'")
        folder = Path(t).expanduser() if t else None
    else:
        folder = INBOX
    files = gc.list_images(folder) if folder and folder.is_dir() else []
    return folder, files


def plan():
    """Photos in shooting order, grouped into stones, with the names they will be saved under."""
    folder, files = get_files()
    if not files:
        return None
    times = times_for(tuple((str(f), f.stat().st_mtime) for f in files))
    if U("order").startswith("Time"):
        files = sorted(files, key=lambda f: (times[str(f)], f.name))
    mode = "count" if U("group_mode") == MODE_COUNT else "pause"
    groups = gc.group_photos(files, times, mode, int(U("per_stone")), float(U("gap")),
                             ss.force_new, ss.force_join)
    names = gc.stone_names(groups, U("prefix"), int(U("start")), int(U("digits")), ss.names)
    outs = gc.output_names(groups, names, U("sep"), U("labels"), U("subfolders"))
    return dict(folder=folder, files=files, groups=groups, names=names, outs=outs, mode=mode)


# ------------------------------------------------------------------ layout
LIGHT_CSS = """<style>
:root {--bar:#f8f9fb; --bar2:#eef0f4; --bg:#e9ebf0; --panel:#f6f7f9; --line:#d3d7e0; --soft:#e2e5ec; --acc:#4668d6; --mut:#667085; --txt:#222733;}
.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {background: var(--bg) !important; color: var(--txt) !important;}
.stApp p, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, .stApp label,
.stApp [data-testid="stMarkdownContainer"], .stApp [data-testid="stWidgetLabel"] p {color: var(--txt);}
.stApp [data-testid="stCaptionContainer"], .st-key-optpanel [data-testid="stWidgetLabel"] p {color: var(--mut) !important;}
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="select"] > div,
.stApp input, .stApp textarea {background: #fff !important; color: var(--txt) !important; border-color: var(--line) !important;}
.stApp [data-testid="stNumberInputStepDown"], .stApp [data-testid="stNumberInputStepUp"] {background: var(--soft) !important; color: var(--txt) !important;}
.stApp .stButton button {color: var(--txt); background: var(--soft); border-color: var(--line);}
.stApp .st-key-toolbar button, .stApp .st-key-topbar button {background: transparent; border-color: transparent;}
.stApp .st-key-toolbar button {filter: none; opacity: .7;}
.stApp .st-key-toolbar button:hover, .stApp .st-key-toolbar button[data-testid="stBaseButton-primary"] {opacity: 1;}
.stApp .st-key-toolbar button[data-testid="stBaseButton-primary"] {background: var(--panel) !important; border-color: var(--line) !important;}
.stApp .st-key-topbar button:hover {background: var(--soft);}
.stApp .st-key-topbar button[data-testid="stBaseButton-primary"] {background: var(--acc); color: #fff; border-color: var(--acc);}
.stApp [data-baseweb="select"] *, .stApp [data-testid="stSelectbox"] div {background-color: #fff !important; color: var(--txt) !important;}
.stApp [data-testid="stSelectbox"] svg, .stApp [data-baseweb="select"] svg {fill: var(--txt) !important; color: var(--txt) !important;}
[data-baseweb="popover"] *, [data-baseweb="menu"] {background-color: #fff !important; color: #1a2030 !important;}
.stApp input, .stApp textarea {-webkit-text-fill-color: var(--txt) !important;}
.st-key-topbar {box-shadow: 0 4px 16px rgba(30,40,70,.08) !important;}
.st-key-optpanel {box-shadow: 0 4px 16px rgba(30,40,70,.06);}
.stApp [data-baseweb="input"], .stApp [data-baseweb="base-input"], .stApp [data-baseweb="select"] > div, .stApp input, .stApp textarea {background: #fbfbfc !important;}
.stApp [data-baseweb="select"] *, .stApp [data-testid="stSelectbox"] div {background-color: #fbfbfc !important;}
[data-baseweb="popover"] *, [data-baseweb="menu"] {background-color: #fbfbfc !important;}
.stApp [data-testid="stRadioOption"] {background: #fbfbfc;}
.stApp [data-testid="stRadioOption"][data-selected="true"] {background: rgba(70,104,214,.13);}
.stApp [data-testid="stExpander"], .stApp [data-testid="stFileUploaderDropzone"] {background: #fbfbfc !important; border-color: var(--line) !important;}
.stApp [data-testid="stFileUploaderDropzone"] * {color: var(--txt) !important;}
.stApp [data-testid="stFileUploaderDropzone"] button {background: var(--soft) !important; color: var(--txt) !important; border-color: var(--line) !important;}
.stApp [data-testid="stToggle"] [data-baseweb="checkbox"]:not(:has(input:checked)) > div:first-child {background-color: #c3c9d6 !important;}
.stApp [data-testid="stNumberInput"] button {background: var(--soft) !important; color: var(--txt) !important;}
.stApp [data-testid="stCode"] pre, .stApp pre {background: #eef0f4 !important;}
.stApp input::placeholder {-webkit-text-fill-color: var(--mut) !important;}
.stApp .stButton button[data-testid="stBaseButton-primary"] {color: #fff;}
.st-key-toolbar button[data-testid="stBaseButton-primary"] {color: var(--txt) !important;}
.stApp code {background: var(--soft); color: #b3366b;}
.stApp [data-testid="stAlert"] {color: var(--txt);}
.stApp table, .stApp th, .stApp td {color: var(--txt); border-color: var(--line);}
.stApp [data-testid="stExpander"] {background: #fff;}
.stApp [data-testid="stToggle"] label p {color: var(--txt);}
</style>"""
if ss.get("w_light_mode", ss.get("p_light_mode", UI["light_mode"])):
    st.markdown(LIGHT_CSS.replace("\n\n", "\n"), unsafe_allow_html=True)

PAGES = {"howto": "How to", "blog": "Blog", "signin": "Sign in", "signup": "Sign up"}


def open_page(p):
    ss.page = None if ss.get("page") == p else p


ss.setdefault("page", None)
with st.container(key="topbar"):
    tb = st.columns([5, 1, 1, 1, 1.1], gap="small", vertical_alignment="center")
    with tb[0]:
        st.markdown("<div class='brand'><span class='logo'><svg viewBox='0 0 24 24' width='22' height='22' fill='none' stroke='white' "
                    "stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'><path d='M6 3h12l4 6-10 13L2 9Z'/>"
                    "<path d='M11 3 8 9l4 13 4-13-3-6'/><path d='M2 9h20'/></svg></span>"
                    "<span class='bname'>Gem<b>Retouch</b></span></div>", unsafe_allow_html=True)
    for col, (p_, label_) in zip(tb[1:], PAGES.items()):
        with col:
            st.button(label_, key=f"nav_{p_}", on_click=open_page, args=(p_,),
                      type="primary" if p_ == "signup" else "secondary")


def render_page(p):
    st.button("← Back to retouching", key="page_back", on_click=open_page, args=(p,))
    if p == "howto":
        st.markdown("""
## How to use GemRetouch
**1. Load a batch.** On the first screen drop in your photos (on your own computer you can also pick a folder with **Browse…**).

**2. Check the stones.** Photos are grouped into stones by the time they were taken. Open **Stones & Export** to set
the name pattern (for example `ruby_001`), photo labels and sub folders. If a stone is grouped wrong, use
**New stone here** / **Join previous** above the picture. You can type a different name for any stone in the name bar.

**3. Retouch.** **Crop** centers the gem in a square. **Dust** removes specks only on the stone. **Heal** is for single
spots and scratches: paint over them. **Color** has saturation and a per-color hue / saturation / brightness editor.

**4. Compare.** Press **Space** to flip between Original and Edited. (In Settings you can choose tap-to-flip or hold-to-peek.)

**5. Export.** Open **Export** and press **Process and save** (on the web you get one zip to download). Your originals are never changed.
""")
        st.markdown("""
### Keyboard
| Key | Does |
|---|---|
| ← / → | previous / next photo |
| ↑ / ↓ | previous / next stone |
| Space | flip Original / Edited (or hold to peek) |
| Shift + click (Heal) | straight line from the last stroke |
| [ and ] (Heal) | smaller / bigger brush |
| Right-drag (Heal) | move the picture |
""")
    elif p == "blog":
        st.markdown("## Blog")
        st.info("Tips, updates and examples will be posted here. Nothing yet.")
    else:
        st.markdown("## " + PAGES[p])
        st.info("You don't need an account: this version runs on your own computer and your photos never leave it. "
                "Sign in and sign up will arrive with the online version.")


if ss.page:
    render_page(ss.page)
    st.stop()

left, right = st.columns([11, 9], gap="medium")   # picture on the left, features on the right
with right:
    with st.container(key="rightcol"):
        with st.container(key="toolbar"):
            cols = st.columns(len(TOOLS), gap="small")
            for col, (k, icon, label) in zip(cols, TOOLS):
                with col:
                    st.button(icon, key=f"tool_{k}", on_click=toggle_tool, args=(k,), help=label,
                              type="primary" if ss.tool == k else "secondary")
        slot = st.container(border=True, key="optpanel")
        st.markdown("<div class='adbox'>📣 <b>Contact for ads</b></div>", unsafe_allow_html=True)


# ------------------------------------------------------------------- panels
def clear_photos():
    shutil.rmtree(INBOX.parent, ignore_errors=True)
    INBOX.mkdir(parents=True, exist_ok=True)
    ss["up_n"] = ss.get("up_n", 0) + 1
    ss["heals"], ss["names"], ss["pos"] = {}, {}, 1
    ss["force_new"], ss["force_join"], ss["seen_sids"] = set(), set(), set()
    ss.pop("zip_path", None)


SAMPLES = Path(__file__).parent / "samples"


def use_samples():
    INBOX.mkdir(parents=True, exist_ok=True)
    for f_ in sorted(gc.list_images(SAMPLES)):
        shutil.copy(f_, INBOX / f_.name)


def panel_photos():
    c1, c2 = st.columns([2, 3]) if not WEB else (st.container(), st.container())
    with c1:
        src = UI["src"] if WEB else keep("radio", "Photos from", "src", UI["src"], ["Folder on my computer", "Drop photos here"])
    with c2:
        if src.startswith("Folder"):
            a, b = st.columns([4, 1])
            with a:
                keep("text_input", "Folder path", "folder", "", placeholder="/Users/you/Pictures/batch1")
            with b:
                st.markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
                st.button("📂 Browse…", on_click=browse, args=("folder",), key="browse_folder")
            st.caption("Click Browse to pick the folder in Finder. Best for big batches.")
        else:
            ups = st.file_uploader("Drop photos", type=[e.strip(".") for e in gc.IMG_EXT],
                                   accept_multiple_files=True, key=f"uploader_{ss.get('up_n', 0)}")
            INBOX.mkdir(parents=True, exist_ok=True)
            for u in ups or []:
                dest = INBOX / u.name
                if not dest.exists() or dest.stat().st_size != u.size:
                    dest.write_bytes(u.getbuffer())
            if WEB and SAMPLES.is_dir() and not any(INBOX.iterdir()):
                st.button("✨ Or try it with sample photos", on_click=use_samples, key="use_samples")
            if WEB and any(INBOX.iterdir()):
                st.button("🗑 Remove all my photos and start over", on_click=clear_photos, key="clear_photos")


def sec(title, hint=None):
    st.markdown(f"<div class='sec'>{title}</div>", unsafe_allow_html=True)
    if hint:
        st.caption(hint)


def reset_settings():
    for k_ in [k_ for k_ in ss.keys() if k_.startswith(("p_", "w_")) and k_[2:] not in ("src", "folder")]:
        del ss[k_]


def panel_settings():
    sec("Picture")
    keep("toggle", "Fit the picture to my window", "auto_fit", UI["auto_fit"])
    keep("slider", "Preview height (px) when not fitting", "view_h", UI["view_h"], 300, 1000, step=20,
         disabled=bool(U("auto_fit")))
    keep("radio", "Space bar", "space_mode", UI["space_mode"], [SPACE_TAP, SPACE_HOLD])
    keep("radio", "Show this when a photo opens", "start_view", UI["start_view"], ["Edited", "Original"])
    keep("toggle", "Keep my zoom and position on the next photo", "keep_view", UI["keep_view"])
    keep("toggle", "Show the Original / Edited label", "show_tag", UI["show_tag"])
    sec("Look")
    keep("toggle", "Light mode", "light_mode", UI["light_mode"])
    sec("Photos")
    panel_photos()
    sec("Settings")
    st.button("Reset all settings to default", on_click=reset_settings, key="reset_all")


def panel_stones():
    mode = keep("radio", "Group photos into stones", "group_mode", UI["group_mode"], [MODE_PAUSE, MODE_COUNT],
                format_func=lambda m: "Automatic (by time)" if m == MODE_PAUSE else "Every N photos")
    if mode == MODE_COUNT:
        keep("number_input", "Photos per stone", "per_stone", UI["per_stone"], 1, 50)
    else:
        keep("number_input", "A pause longer than this starts a new stone (seconds)", "gap", UI["gap"], 5, 3600)

    sec("Name")
    a = st.columns(2)
    with a[0]:
        keep("text_input", "Name starts with", "prefix", UI["prefix"])
    with a[1]:
        keep("number_input", "First number", "start", UI["start"], 0, 99999)

    with st.expander("More options"):
        b = st.columns(2)
        with b[0]:
            keep("number_input", "Digits in the number", "digits", UI["digits"], 1, 6)
        with b[1]:
            keep("text_input", "Between name and photo", "sep", UI["sep"])
        keep("text_input", "Photo labels (top, side, back…)", "labels", UI["labels"])
        keep("selectbox", "Order photos by", "order", UI["order"], ["Time taken", "File name"])
        keep("toggle", "Each stone in its own folder", "subfolders", UI["subfolders"])

    P = plan()
    if not P:
        return
    sizes = [len(g) for g in P["groups"]]
    n, S = len(P["files"]), len(sizes)
    st.markdown(f"**{n} photos → {S} stone{'s' if S != 1 else ''}**  \n"
                f"`{Path(P['files'][0]).name}` → `{P['outs'][str(P['files'][0])]}{U('fmt')}`")
    common = Counter(sizes).most_common(1)[0][0]
    odd = [f"{i + 1} ({s_})" for i, s_ in enumerate(sizes) if s_ != common]
    if odd:
        st.warning(f"Most stones have {common} photos. Check stone " + ", ".join(odd[:8]) + (" …" if len(odd) > 8 else ""))
    if P["mode"] == "pause" and S == 1 and n > 8:
        st.warning("These photos have no different shot times, so they stayed in one stone. "
                   "Choose “Every N photos”.")


def panel_crop():
    keep("toggle", "Center the gem and crop to a square", "crop", UI["crop"])
    sec("Framing")
    keep("slider", "Space around gem (%)", "padding", UI["padding"], 0, 50)
    c = st.columns(2)
    with c[0]:
        keep("slider", "Nudge left / right (%)", "dx", UI["dx"], -20, 20)
    with c[1]:
        keep("slider", "Nudge up / down (%)", "dy", UI["dy"], -20, 20)
    sec("Output")
    keep("number_input", "Size (px)", "out_size", UI["out_size"], 500, 6000, step=100)


def panel_dust():
    keep("toggle", "Remove dust specks", "dust", UI["dust"])
    keep("toggle", "Only on the gemstone (skip tweezers)", "gem_only", UI["gem_only"])
    sec("Detection")
    keep("radio", "Look for", "dust_mode", UI["dust_mode"], ["Both", "Dark specks", "Bright specks"])
    keep("slider", "Sensitivity (lower finds more)", "dust_thr", UI["dust_thr"], 5, 60)
    c = st.columns(2)
    with c[0]:
        keep("slider", "Max speck size (px)", "dust_area", UI["dust_area"], 20, 1000)
    with c[1]:
        keep("slider", "Keep away from edges (%)", "gem_margin", UI["gem_margin"], 0, 10)
    sec("Check my work")
    keep("toggle", "Show what will be fixed (red)", "show_mask", UI["show_mask"])
    keep("toggle", "Show the detected gem area (yellow line)", "show_gem", UI["show_gem"])


def panel_heal():
    st.caption("Paint over a speck or scratch in the picture. The app finds a clean spot on the stone "
               "that matches and blends it in.")
    st.markdown("<div class='tips'><span><b>Shift</b> + click = straight line</span>"
                "<span><b>[</b> <b>]</b> = brush size</span>"
                "<span><b>Right-drag</b> = move picture</span></div>", unsafe_allow_html=True)
    sec("Brush")
    keep("slider", "Brush size", "brush", UI["brush"], 4, 120)
    keep("radio", "Method", "heal_method", UI["heal_method"], [HEAL_SMART, HEAL_SMOOTH])
    n = len(ss.get("heals", {}).get(ss.get("cur_path"), []))
    sec("This photo", f"{n} stroke(s)")
    c = st.columns(2)
    with c[0]:
        st.button("↶ Undo last", on_click=undo_heal, disabled=n == 0, key="undo_heal")
    with c[1]:
        st.button("Clear all", on_click=clear_heal, disabled=n == 0, key="clear_heal")


def panel_color():
    sec("Overall")
    keep("slider", "Saturation (%)", "sat", UI["sat"], 0, 200)
    sec("Per color (HSL)")
    band = keep("radio", "Pick a color", "band", UI["band"], list(gc.BANDS),
                format_func=lambda b: f"{EMOJI[b]} {b}")
    h = keep("slider", "Hue shift", f"h_{band}", 0, -30, 30)
    s_ = keep("slider", "Saturation", f"s_{band}", 0, -100, 100)
    l = keep("slider", "Brightness", f"l_{band}", 0, -100, 100)
    st.markdown(swatch(gc.BANDS[band], h, s_, l), unsafe_allow_html=True)


def panel_export():
    sec("Save")
    if WEB:
        st.caption("Your edited photos are packed into one zip file that you download.")
    else:
        keep("text_input", "Save to (empty = an “edited” folder next to the photos)", "outdir", UI["outdir"])
        st.button("📂 Browse…", on_click=browse, args=("outdir",), key="browse_out")
    d = st.columns(2)
    with d[0]:
        keep("selectbox", "Format", "fmt", UI["fmt"], [".jpg", ".png"])
    with d[1]:
        keep("slider", "JPEG quality", "quality", UI["quality"], 70, 100)
    keep("radio", "What to save", "scope", UI["scope"], [SCOPE_ALL, SCOPE_ONE])
    if not WEB:
        keep("toggle", "Replace files that already exist", "overwrite", UI["overwrite"])
    P = plan()
    if P:
        shown = P["files"][:8]
        with st.expander(f"Preview of the new file names ({len(P['files'])} photos)"):
            lines = [f"{Path(f).name}  →  {P['outs'][str(f)]}{U('fmt')}" for f in shown]
            st.code("\n".join(lines + ([f"… and {len(P['files']) - len(shown)} more"]
                                       if len(P["files"]) > len(shown) else [])))
    go_ = st.button("Process and save" if not WEB else "Process and make zip", type="primary", key="do_export")
    if WEB and ss.get("zip_path") and Path(ss["zip_path"]).exists() and not go_:
        with open(ss["zip_path"], "rb") as fh:
            st.download_button("⬇ Download " + ss.get("zip_name", "photos.zip"), fh, file_name=ss.get("zip_name", "photos.zip"),
                               mime="application/zip", key="dl_prev", type="primary")
    return go_


do_export = False
with slot:
    if plan() is None:
        st.caption("Choose your photos on the left to start. The tools open here afterwards.")
    elif ss.tool == "stones":
        panel_stones()
    elif ss.tool == "export":
        do_export = panel_export()
    else:
        {"crop": panel_crop, "dust": panel_dust, "heal": panel_heal, "color": panel_color,
         "settings": panel_settings}[ss.tool]()

# ------------------------------------------------------------------- settings
params = dict(
    crop=U("crop"), padding=U("padding") / 100, dx=U("dx") / 100, dy=U("dy") / 100,
    out_size=int(U("out_size")),
    dust=U("dust"), dust_thr=U("dust_thr"), dust_area=U("dust_area"), dust_mode=U("dust_mode"),
    gem_only=U("gem_only"), gem_margin=U("gem_margin") / 100,
    heal_method="smart" if U("heal_method") == HEAL_SMART else "smooth",
    saturation=U("sat") / 100,
    hsl={b: dict(h=ss.get(f"p_h_{b}", 0), s=ss.get(f"p_s_{b}", 0), l=ss.get(f"p_l_{b}", 0)) for b in gc.BANDS},
)

snap = {k: v for k, v in ss.items() if k.startswith("p_") and isinstance(v, (str, int, float, bool))}
blob = json.dumps(snap, sort_keys=True)
if blob != ss.get("_saved_settings"):
    ss["_saved_settings"] = blob
    try:
        if WEB:
            raise RuntimeError
        SETTINGS.write_text(blob)
    except Exception:
        pass

# --------------------------------------------------------------------- photos
P = plan()
if P is None:
    with left:
        with st.container(border=True):
            st.markdown("### 💎 Welcome — choose your photos to start")
            panel_photos()
    P = plan()
    if P is not None:
        st.rerun()
    st.stop()
files, groups, names, outs = P["files"], P["groups"], P["names"], P["outs"]
n, S = len(files), len(groups)
ss.pos = min(max(int(ss.pos), 1), n)
idx = ss.pos - 1
path = files[idx]
starts, acc = [], 0
for g in groups:
    starts.append(acc)
    acc += len(g)
si = max(0, bisect.bisect_right(starts, idx) - 1)
group = groups[si]
k = idx - starts[si]
ss["_stone_starts"], ss["cur_stone"], ss["cur_path"] = starts, si, str(path)
strokes = ss.heals.setdefault(str(path), [])

img = cached_load(str(path), path.stat().st_mtime)
res = gc.process_full(img, params, strokes)
base = gc.process_full(img, {**params, "dust": False, "saturation": 1.0, "hsl": {}}, None)["result"]
edited = res["result"]
if (U("show_mask") and res["dust_mask"] is not None) or U("show_gem"):
    edited = edited.copy()
    if U("show_mask") and res["dust_mask"] is not None:
        edited[res["dust_mask"] > 0] = (0, 0, 255)
    if U("show_gem"):
        cnts, _ = cv2.findContours(res["gem_mask"], cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(edited, cnts, -1, (255, 255, 0), max(2, edited.shape[1] // 400))

# ------------------------------------------------------------ stone name bar (left column)
_left = left.__enter__()
if len(group) <= 10:
    window = list(range(len(group)))
else:
    lo = min(max(k - 5, 0), len(group) - 10)
    window = list(range(lo, lo + 10))
with st.container(key="namebar"):
    h = st.columns([1, 1, 1], gap="small")
    with h[0]:
        first = str(group[0])
        wk = "nm_" + hashlib.md5(first.encode()).hexdigest()[:8]
        if wk not in ss:
            ss[wk] = ss.names.get(first, "")
        st.text_input("Stone name", key=wk, placeholder=names[si], label_visibility="collapsed",
                      on_change=set_name, args=(first, wk), help=f"Type the name for this stone. Saves as {outs[str(path)]}{U('fmt')}")
        st.button("▲", key="prevstone", on_click=go_stone, args=(-1,), disabled=si == 0, help="Previous stone (↑)")
        st.button("▼", key="nextstone", on_click=go_stone, args=(1,), disabled=si == S - 1, help="Next stone (↓)")
    with h[1]:
        st.markdown("<div class='sdots'>" + "".join(f"<i class='{'on' if j == k else ''}'></i>" for j in window) + "</div>",
                    unsafe_allow_html=True)
    with h[2]:
        if k > 0:
            st.button("New stone", icon=":material/content_cut:", on_click=mark_new, args=(str(path),), key="mk_new")
        elif si > 0:
            st.button("Join previous", icon=":material/call_merge:", on_click=mark_join, args=(str(path),), key="mk_join")
        else:
            st.button("New stone", icon=":material/content_cut:", disabled=True, key="mk_none", help="This is the first photo of the first stone")
# ------------------------------------------------------------------- viewer
orig_b64, edit_b64 = to_b64(base), to_b64(edited)
evt = VIEWER(
    orig=orig_b64, edit=edit_b64,
    orig_id=hashlib.md5(orig_b64.encode()).hexdigest()[:12],
    edit_id=hashlib.md5(edit_b64.encode()).hexdigest()[:12],
    name=path.name, stone_label=f"Stone {si + 1} of {S}", note=(f"{cv2.connectedComponents(res['dust_mask'])[0] - 1} dust spots fixed" if res["dust_mask"] is not None else ""), mode="heal" if ss.tool == "heal" else "pan", brush=U("brush"),
    seen=sorted(ss.seen_sids), height=int(U("view_h")), auto_fit=bool(U("auto_fit")), fit_offset=298,
    space_mode="hold" if U("space_mode") == SPACE_HOLD else "tap", keep_view=U("keep_view"),
    start_edited=U("start_view") == "Edited", show_tag=U("show_tag"), light=bool(U("light_mode")),
    key="gemview", default=None,
)

# events coming back from the viewer: brush strokes and arrow keys
if evt and evt.get("id") != ss.get("last_evt"):
    ss["last_evt"] = evt.get("id")
    changed = False
    if evt.get("nav"):
        ss["_goto"] = min(max(idx + 1 + int(evt["nav"]), 1), n)
        changed = True
    if evt.get("stone"):
        ss["_goto"] = starts[min(max(si + int(evt["stone"]), 0), S - 1)] + 1
        changed = True
    if evt.get("name") == path.name:
        for s in evt.get("strokes") or []:
            sid = str(s.get("sid"))
            if sid in ss.seen_sids:
                continue
            ss.seen_sids.add(sid)
            conv = gc.stroke_to_original(s, res["rect"])
            if conv:
                strokes.append(conv)
            changed = True
    if changed:
        st.rerun()

# ---------------------------------------------------- photo strip of this stone
cols = st.columns([0.6, 0.55] + [1] * len(window) + [0.55], gap="small")
with cols[0]:
    st.button("▲", key="sprev", on_click=go_stone, args=(-1,), disabled=si == 0, help="Previous stone")
    st.markdown(f"<div class='stnum' title='Stone {si + 1} of {S}'><b>{si + 1}</b><span>/{S}</span></div>", unsafe_allow_html=True)
    st.button("▼", key="snext", on_click=go_stone, args=(1,), disabled=si == S - 1, help="Next stone")
with cols[1]:
    st.button("‹", key="prev", on_click=go, args=(-1, n), disabled=idx == 0, help="Previous photo (←)")
for col, j in zip(cols[2:-1], window):
    f = group[j]
    with col:
        show(cached_thumb(str(f), f.stat().st_mtime))
        st.button(str(j + 1), key=f"thb_{starts[si] + j}", on_click=jump, args=(starts[si] + j + 1,),
                  type="primary" if starts[si] + j == idx else "secondary")
with cols[-1]:
    st.button("›", key="next", on_click=go, args=(1, n), disabled=idx == n - 1, help="Next photo (→)")
left.__exit__(None, None, None)

# --------------------------------------------------------------------- export
if do_export:
    if WEB:
        out = INBOX.parent / "edited"
        shutil.rmtree(out, ignore_errors=True)
    else:
        out = Path(U("outdir").strip()).expanduser() if U("outdir").strip() else (P["folder"] / "edited")
    chosen = group if U("scope") == SCOPE_ONE else files
    items = [(f, outs[str(f)]) for f in chosen]
    dups = gc.find_duplicates({str(f): outs[str(f)] for f in chosen})
    with slot:
        if dups:
            st.error("Two photos would get the same name: " + ", ".join(dups[:6]) +
                     ". Give those stones different names (Stones tool).")
        else:
            bar = st.progress(0.0)
            t0 = time.time()
            r = gc.export_batch(items, out, params, U("fmt"), int(U("quality")),
                                progress=lambda i, n_: bar.progress(i / n_),
                                heals=ss.heals, overwrite=U("overwrite") or WEB, workers=2 if WEB else None)
            if r["errors"]:
                st.warning("Some photos failed: " + "; ".join(f"{nm}: {e}" for nm, e in r["errors"][:5]))
            if WEB:
                zp = INBOX.parent / "gemretouch_edited.zip"
                with zipfile.ZipFile(zp, "w", zipfile.ZIP_STORED) as z:
                    for f_ in sorted(out.rglob("*")):
                        if f_.is_file():
                            z.write(f_, f_.relative_to(out).as_posix())
                shutil.rmtree(out, ignore_errors=True)
                ss["zip_path"], ss["zip_name"] = str(zp), "gemretouch_edited.zip"
                st.success(f"Done: {r['done']} photos in {time.time() - t0:.0f} s.")
                with open(zp, "rb") as fh:
                    st.download_button("⬇ Download gemretouch_edited.zip", fh, file_name="gemretouch_edited.zip",
                                       mime="application/zip", key="dl_now", type="primary")
            else:
                msg = f"Saved {r['done']} photos in {time.time() - t0:.0f} s to {out}"
                if r["skipped"]:
                    msg += f"  ({r['skipped']} skipped because they already exist)"
                st.success(msg)
                st.button("📂 Open the folder", on_click=sysutil.open_folder, args=(str(out),), key="open_out")
