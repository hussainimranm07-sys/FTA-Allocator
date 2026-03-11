import streamlit as st
import pandas as pd
import math
import io
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="FTA Risk Allocator", page_icon="🌳", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
.stApp { background: #0d1117; color: #e6edf3; }
section[data-testid="stSidebar"] { background: #161b22 !important; border-right: 1px solid #30363d; }
section[data-testid="stSidebar"] * { color: #e6edf3 !important; }
.fta-header { background: linear-gradient(135deg,#1a2332,#0d1117); border:1px solid #30363d; border-left:4px solid #f97316; border-radius:8px; padding:20px 28px; margin-bottom:20px; }
.fta-header h1 { font-family:'IBM Plex Mono',monospace; font-size:1.5rem; color:#f97316; margin:0 0 4px 0; }
.fta-header p { color:#8b949e; margin:0; font-size:0.83rem; }
.metric-card { background:#161b22; border:1px solid #30363d; border-radius:8px; padding:14px 18px; height:80px; }
.metric-card .mlabel { font-size:0.68rem; color:#8b949e; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }
.metric-card .mvalue { font-family:'IBM Plex Mono',monospace; font-size:1.2rem; font-weight:700; }
.tree-table { width:100%; border-collapse:collapse; margin-top:6px; font-size:0.84rem; }
.tree-table th { background:#1c2128; color:#8b949e; font-size:0.68rem; text-transform:uppercase; letter-spacing:1px; padding:10px 12px; text-align:left; border-bottom:1px solid #30363d; font-family:'IBM Plex Mono',monospace; }
.tree-table td { padding:8px 12px; border-bottom:1px solid #21262d; vertical-align:middle; }
.tree-table tr:hover td { background:#1c2128; }
.badge { display:inline-block; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:700; font-family:'IBM Plex Mono',monospace; }
.b-HZ{background:#3d1a00;color:#f97316;border:1px solid #f97316}
.b-SF{background:#0d2136;color:#58a6ff;border:1px solid #58a6ff}
.b-FF{background:#0d2b14;color:#3fb950;border:1px solid #3fb950}
.b-IF{background:#1e0d36;color:#d2a8ff;border:1px solid #d2a8ff}
.b-AND{background:#2d1a3d;color:#e040fb;border:1px solid #e040fb}
.g-or{color:#58a6ff;font-weight:700;font-family:'IBM Plex Mono';font-size:0.78rem}
.g-and{color:#e040fb;font-weight:700;font-family:'IBM Plex Mono';font-size:0.78rem}
.g-top{color:#8b949e;font-size:0.78rem}
.vm{font-family:'IBM Plex Mono',monospace;font-size:0.83rem;font-weight:600}
.c-hz{color:#f97316}.c-sf{color:#58a6ff}.c-ff{color:#3fb950}.c-if{color:#d2a8ff}.c-and{color:#e040fb}
div[data-testid="stExpander"]{background:#161b22;border:1px solid #30363d;border-radius:8px}
.stButton button{background:#1c2128 !important;border:1px solid #30363d !important;color:#e6edf3 !important;border-radius:6px !important;transition:all 0.15s}
.stButton button:hover{border-color:#58a6ff !important;color:#58a6ff !important}
.stTabs [data-baseweb="tab"]{color:#8b949e}
.stTabs [aria-selected="true"]{color:#f97316 !important;border-bottom-color:#f97316 !important}
.edit-card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-bottom:12px}
.edit-card h4{color:#f97316;font-family:'IBM Plex Mono',monospace;margin:0 0 12px 0;font-size:0.9rem}
.rule-box{background:#161b22;border:1px solid #30363d;border-left:3px solid #f97316;border-radius:6px;padding:12px 16px;margin:6px 0;font-size:0.82rem}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# VALID PARENT RULES  ← core of the new feature
# SF  can live under: HZ, SF, AND
# FF  can live under: SF, FF, AND
# IF  can live under: FF
# AND can live under: HZ, SF, FF
# ═══════════════════════════════════════════════════════════════
VALID_PARENTS = {
    "SF":  ["HZ", "SF", "AND"],
    "FF":  ["SF", "FF", "AND"],
    "IF":  ["FF"],
    "AND": ["HZ", "SF", "FF"],
}

TYPE_COLOR_SVG = {
    "HZ":  {"box":"#3d1a00","text":"#f97316","border":"#f97316"},
    "SF":  {"box":"#0d2136","text":"#58a6ff","border":"#58a6ff"},
    "FF":  {"box":"#0d2b14","text":"#3fb950","border":"#3fb950"},
    "IF":  {"box":"#1e0d36","text":"#d2a8ff","border":"#d2a8ff"},
    "AND": {"box":"#2d1a3d","text":"#e040fb","border":"#e040fb"},
}

VC_MAP = {"HZ":"hz","SF":"sf","FF":"ff","IF":"if","AND":"and"}

# ── Default tree (includes nested SF→SF and FF→FF examples) ───────────────────
def default_tree():
    return {
        "HZ01":  {"id":"HZ01", "label":"HZxx",      "name":"Pressurized Fluid Hazard",  "type":"HZ",  "parent":None,   "gate":"–",   "desc":"Top-level Hazard Event"},
        # SF level 1
        "SF01":  {"id":"SF01", "label":"SF01",       "name":"System Failure 01",          "type":"SF",  "parent":"HZ01", "gate":"OR",  "desc":"System Failure – direct child of Hazard"},
        "SF02":  {"id":"SF02", "label":"SF02",       "name":"System Failure 02",          "type":"SF",  "parent":"HZ01", "gate":"OR",  "desc":"System Failure – direct child of Hazard"},
        "SF03":  {"id":"SF03", "label":"SF03",       "name":"System Failure 03",          "type":"SF",  "parent":"HZ01", "gate":"OR",  "desc":"System Failure with nested SF children"},
        # SF nested under SF03  ← NEW
        "SF03a": {"id":"SF03a","label":"SF03a",      "name":"Sub System Failure 03a",     "type":"SF",  "parent":"SF03", "gate":"OR",  "desc":"Nested SF – child of SF03"},
        "SF03b": {"id":"SF03b","label":"SF03b",      "name":"Sub System Failure 03b",     "type":"SF",  "parent":"SF03", "gate":"OR",  "desc":"Nested SF – child of SF03"},
        # AND under SF02
        "AND01": {"id":"AND01","label":"CombFaults",  "name":"Combined Faults",            "type":"AND", "parent":"SF02", "gate":"AND", "desc":"Combined Faults (AND gate)"},
        # FF under SF01
        "FF01":  {"id":"FF01", "label":"FF01",       "name":"Following Failure 01",        "type":"FF",  "parent":"SF01", "gate":"OR",  "desc":"FF child of SF01"},
        "FF02":  {"id":"FF02", "label":"FF02",       "name":"Following Failure 02",        "type":"FF",  "parent":"SF01", "gate":"OR",  "desc":"FF child of SF01 – has nested FF"},
        # FF nested under FF02  ← NEW
        "FF02a": {"id":"FF02a","label":"FF02a",      "name":"Sub Following Failure 02a",   "type":"FF",  "parent":"FF02", "gate":"OR",  "desc":"Nested FF – child of FF02"},
        "FF02b": {"id":"FF02b","label":"FF02b",      "name":"Sub Following Failure 02b",   "type":"FF",  "parent":"FF02", "gate":"OR",  "desc":"Nested FF – child of FF02"},
        # FF under SF03a
        "FF03":  {"id":"FF03", "label":"FF03",       "name":"Following Failure 03",        "type":"FF",  "parent":"SF03a","gate":"OR",  "desc":"FF child of nested SF03a"},
        # FF under AND01
        "FF04":  {"id":"FF04", "label":"FF04",       "name":"Following Failure 04",        "type":"FF",  "parent":"AND01","gate":"AND", "desc":"FF child of AND gate"},
        "FF05":  {"id":"FF05", "label":"FF05",       "name":"Following Failure 05",        "type":"FF",  "parent":"AND01","gate":"AND", "desc":"FF child of AND gate"},
        # IFs
        "IF01":  {"id":"IF01", "label":"IF01","name":"Initiating Failure 01","type":"IF","parent":"FF01", "gate":"OR","desc":"IF01"},
        "IF02":  {"id":"IF02", "label":"IF02","name":"Initiating Failure 02","type":"IF","parent":"FF01", "gate":"OR","desc":"IF02"},
        "IF03":  {"id":"IF03", "label":"IF03","name":"Initiating Failure 03","type":"IF","parent":"FF02a","gate":"OR","desc":"IF03"},
        "IF04":  {"id":"IF04", "label":"IF04","name":"Initiating Failure 04","type":"IF","parent":"FF02a","gate":"OR","desc":"IF04"},
        "IF05":  {"id":"IF05", "label":"IF05","name":"Initiating Failure 05","type":"IF","parent":"FF02b","gate":"OR","desc":"IF05"},
        "IF06":  {"id":"IF06", "label":"IF06","name":"Initiating Failure 06","type":"IF","parent":"FF03", "gate":"OR","desc":"IF06"},
        "IF07":  {"id":"IF07", "label":"IF07","name":"Initiating Failure 07","type":"IF","parent":"FF04", "gate":"OR","desc":"IF07"},
        "IF08":  {"id":"IF08", "label":"IF08","name":"Initiating Failure 08","type":"IF","parent":"FF04", "gate":"OR","desc":"IF08"},
        "IF09":  {"id":"IF09", "label":"IF09","name":"Initiating Failure 09","type":"IF","parent":"FF05", "gate":"OR","desc":"IF09"},
        "IF10":  {"id":"IF10", "label":"IF10","name":"Initiating Failure 10","type":"IF","parent":"FF05", "gate":"OR","desc":"IF10"},
    }

if "tree"      not in st.session_state: st.session_state.tree      = default_tree()
if "hz_target" not in st.session_state: st.session_state.hz_target = 1e-8
if "next_id"   not in st.session_state: st.session_state.next_id   = 100

# ── Core engine (unchanged – already fully recursive, works for any depth) ────
def get_children(tree, pid):
    return [n for n in tree.values() if n["parent"] == pid]

def allocate_tree(tree, hz_target):
    """Recursive top-down allocation. Works for any nesting depth."""
    alloc = {}
    def recurse(nid, budget):
        alloc[nid] = budget
        children = get_children(tree, nid)
        if not children: return
        n = len(children)
        for child in children:
            cb = budget ** (1.0 / n) if child["gate"] == "AND" else budget / n
            recurse(child["id"], cb)
    hz_id = next(k for k, v in tree.items() if v["type"] == "HZ")
    recurse(hz_id, hz_target)
    return alloc

def get_ordered(tree):
    hz_id = next(k for k, v in tree.items() if v["type"] == "HZ")
    visited, order, queue = set(), [], [hz_id]
    while queue:
        nid = queue.pop(0)
        if nid in visited: continue
        visited.add(nid); order.append(nid)
        queue.extend(c["id"] for c in get_children(tree, nid))
    return order

def get_level(tree, nid):
    lvl = 0
    while tree[nid]["parent"]:
        nid = tree[nid]["parent"]; lvl += 1
    return lvl

def descendants(tree, tid):
    d = []
    for k, n in tree.items():
        if n["parent"] == tid:
            d.append(k); d.extend(descendants(tree, k))
    return d

def fmt(v): return f"{v:.3E}" if v is not None else "–"

def would_create_cycle(tree, new_node_id, parent_id):
    """Check if assigning parent_id as parent of new_node_id creates a cycle."""
    nid = parent_id
    visited = set()
    while nid:
        if nid == new_node_id: return True
        if nid in visited: break
        visited.add(nid)
        nid = tree.get(nid, {}).get("parent")
    return False

# ── SVG Visualizer ────────────────────────────────────────────────────────────
def build_svg(tree, alloc):
    BOX_W, BOX_H = 138, 56
    H_GAP, V_GAP = 16, 80
    GATE_R = 14

    order = get_ordered(tree)

    # Group by level for initial x layout
    levels = {}
    for nid in order:
        lvl = get_level(tree, nid)
        levels.setdefault(lvl, []).append(nid)

    # Assign positions: spread each level evenly
    pos = {}
    max_lvl = max(levels.keys()) if levels else 0
    for lvl, nodes in levels.items():
        total_w = len(nodes) * BOX_W + (len(nodes) - 1) * H_GAP
        start_x = -total_w / 2
        for i, nid in enumerate(nodes):
            cx = start_x + i * (BOX_W + H_GAP) + BOX_W / 2
            cy = lvl * (BOX_H + V_GAP + GATE_R * 2) + BOX_H / 2 + 40
            pos[nid] = (cx, cy)

    all_x = [p[0] for p in pos.values()]
    all_y = [p[1] for p in pos.values()]
    min_x = min(all_x) - BOX_W / 2 - 30
    max_x = max(all_x) + BOX_W / 2 + 30
    min_y = min(all_y) - BOX_H / 2 - 30
    max_y = max(all_y) + BOX_H / 2 + 40
    W = max_x - min_x
    H = max_y - min_y
    ox, oy = -min_x, -min_y

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(W)}" height="{int(H)}" '
        f'style="background:#0d1117;border-radius:12px;font-family:\'IBM Plex Sans\',sans-serif">',
        '<defs>',
        '<marker id="arr" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">'
        '<path d="M0,0 L0,6 L7,3 z" fill="#444"/></marker>',
        # OR gate symbol (oval)
        '<symbol id="g-or" viewBox="0 0 30 30">'
        '<ellipse cx="15" cy="15" rx="13" ry="13" fill="#0d2136" stroke="#58a6ff" stroke-width="2"/>'
        '<text x="15" y="19" text-anchor="middle" font-size="8" fill="#58a6ff" font-weight="bold" font-family="monospace">OR</text>'
        '</symbol>',
        # AND gate symbol (rounded rect)
        '<symbol id="g-and" viewBox="0 0 30 30">'
        '<rect x="2" y="2" width="26" height="26" rx="7" fill="#2d1a3d" stroke="#e040fb" stroke-width="2"/>'
        '<text x="15" y="19" text-anchor="middle" font-size="7" fill="#e040fb" font-weight="bold" font-family="monospace">AND</text>'
        '</symbol>',
        '</defs>',
    ]

    # Draw connectors + gate icons
    for nid in order:
        node = tree[nid]
        if not node["parent"] or node["parent"] not in pos: continue
        px, py = pos[node["parent"]]
        cx, cy = pos[nid]

        # Gate position – midway vertically between parent bottom and child top
        gate_x = (px + cx) / 2
        gate_y = (py + BOX_H / 2 + cy - BOX_H / 2) / 2

        # Connector: parent bottom → gate top
        lines.append(
            f'<line x1="{px+ox:.1f}" y1="{py+oy+BOX_H/2:.1f}" '
            f'x2="{gate_x+ox:.1f}" y2="{gate_y+oy-GATE_R:.1f}" '
            f'stroke="#2d333b" stroke-width="1.5"/>'
        )
        # Connector: gate bottom → child top (with arrow)
        lines.append(
            f'<line x1="{gate_x+ox:.1f}" y1="{gate_y+oy+GATE_R:.1f}" '
            f'x2="{cx+ox:.1f}" y2="{cy+oy-BOX_H/2:.1f}" '
            f'stroke="#2d333b" stroke-width="1.5" marker-end="url(#arr)"/>'
        )
        # Gate symbol
        g_sym = "g-and" if node["gate"] == "AND" else "g-or"
        gx = gate_x + ox - GATE_R
        gy = gate_y + oy - GATE_R
        lines.append(f'<use href="#{g_sym}" x="{gx:.1f}" y="{gy:.1f}" width="{GATE_R*2}" height="{GATE_R*2}"/>')

    # Draw node boxes
    for nid in order:
        node = tree[nid]
        if nid not in pos: continue
        cx, cy = pos[nid]
        x = cx + ox - BOX_W / 2
        y = cy + oy - BOX_H / 2
        t = node["type"]
        col = TYPE_COLOR_SVG.get(t, TYPE_COLOR_SVG["SF"])
        val = alloc.get(nid, 0)

        # Shadow
        lines.append(f'<rect x="{x+3:.1f}" y="{y+3:.1f}" width="{BOX_W}" height="{BOX_H}" rx="8" fill="#000" opacity="0.35"/>')
        # Box
        lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{BOX_W}" height="{BOX_H}" rx="8" fill="{col["box"]}" stroke="{col["border"]}" stroke-width="1.8"/>')

        # Type badge background strip
        lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{BOX_W}" height="14" rx="8" fill="{col["border"]}" opacity="0.25"/>')
        lines.append(f'<rect x="{x:.1f}" y="{y+6:.1f}" width="{BOX_W}" height="8" fill="{col["border"]}" opacity="0.25"/>')

        # Type label
        lines.append(f'<text x="{cx+ox:.1f}" y="{y+11:.1f}" text-anchor="middle" font-size="8" fill="{col["text"]}" font-weight="bold" font-family="monospace" opacity="0.9">{t}</text>')

        # Node label (bold)
        lbl = node.get("label", nid)[:16]
        lines.append(f'<text x="{cx+ox:.1f}" y="{y+26:.1f}" text-anchor="middle" font-size="11" font-weight="bold" fill="{col["text"]}" font-family="monospace">{lbl}</text>')

        # Node name (truncated)
        name = node.get("name", "")[:20]
        lines.append(f'<text x="{cx+ox:.1f}" y="{y+38:.1f}" text-anchor="middle" font-size="7.5" fill="{col["text"]}" opacity="0.75" font-family="sans-serif">{name}</text>')

        # Allocated value
        val_str = f"{val:.2E}"
        lines.append(f'<text x="{cx+ox:.1f}" y="{y+51:.1f}" text-anchor="middle" font-size="8" fill="{col["text"]}" opacity="0.6" font-family="monospace">{val_str}</text>')

    lines.append('</svg>')
    return "\n".join(lines), int(W), int(H)

# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ FTA Controls")
    st.markdown("---")

    # Hazard target
    st.markdown("**🎯 Hazard Target**")
    hz_exp  = st.number_input("Exponent (10ˣ)", value=-8, min_value=-20, max_value=-1, step=1)
    hz_mant = st.number_input("Mantissa", value=1.0, min_value=0.1, max_value=9.9, step=0.1, format="%.1f")
    st.session_state.hz_target = hz_mant * (10 ** hz_exp)
    st.success(f"**{st.session_state.hz_target:.2E}** /yr")

    st.markdown("---")
    st.markdown("**➕ Add Node**")
    tree = st.session_state.tree

    node_type = st.selectbox("Node Type", ["SF","FF","IF","AND"],
        help="SF & FF can now be nested under same type. Rules:\n"
             "• SF → under HZ, SF, or AND\n"
             "• FF → under SF, FF, or AND\n"
             "• IF → under FF only\n"
             "• AND → under HZ, SF, or FF")

    gate_choice = st.selectbox("Gate Type (this node → parent)", ["OR","AND"],
        help="OR: this node alone can cause the parent\nAND: all siblings must fail together")

    # ── Dynamic parent filter using VALID_PARENTS ──────────────────────────────
    allowed_parent_types = VALID_PARENTS.get(node_type, [])
    parents = {
        k: f"{v.get('label',k)}  [{v['type']}]"
        for k, v in tree.items()
        if v["type"] in allowed_parent_types
    }

    if parents:
        par_key   = st.selectbox("Parent Node", list(parents.keys()),
                                 format_func=lambda k: parents[k])
        new_label = st.text_input("Label (short ID)", value=f"{node_type}{st.session_state.next_id:02d}")
        new_name  = st.text_input("Name", value=f"New {node_type} name")
        new_desc  = st.text_input("Description", value=f"Describe this {node_type}")
        gate_val  = "AND" if node_type == "AND" else gate_choice

        if st.button("➕ Add Node", use_container_width=True):
            nid = f"N{st.session_state.next_id}"
            # Cycle guard
            if would_create_cycle(tree, nid, par_key):
                st.error("⚠️ This would create a cycle in the tree!")
            else:
                st.session_state.tree[nid] = {
                    "id": nid, "label": new_label, "name": new_name,
                    "type": node_type, "parent": par_key,
                    "gate": gate_val, "desc": new_desc
                }
                st.session_state.next_id += 1
                st.rerun()
    else:
        st.info(f"No valid parents for {node_type}.\nAllowed parent types: {allowed_parent_types}")

    # ── Allowed parent rules quick reference ──────────────────────────────────
    with st.expander("📐 Parent rules"):
        st.markdown("""
| Node | Can live under |
|------|---------------|
| SF | HZ · SF · AND |
| FF | SF · FF · AND |
| IF | FF |
| AND | HZ · SF · FF |
        """)

    st.markdown("---")
    st.markdown("**🗑️ Delete Node**")
    deletable = {k: f"{v.get('label',k)} ({v['type']})" for k, v in tree.items() if v["type"] != "HZ"}
    if deletable:
        del_k = st.selectbox("Node to delete", list(deletable.keys()),
                             format_func=lambda k: deletable[k])
        n_desc = len(descendants(tree, del_k))
        if n_desc:
            st.warning(f"⚠️ Also deletes {n_desc} child node(s).")
        if st.button("🗑️ Delete", use_container_width=True):
            for d in [del_k] + descendants(tree, del_k):
                st.session_state.tree.pop(d, None)
            st.rerun()

    st.markdown("---")
    if st.button("🔄 Reset to Default", use_container_width=True):
        for k in ["tree","hz_target","next_id"]:
            st.session_state.pop(k, None)
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
tree  = st.session_state.tree
alloc = allocate_tree(tree, st.session_state.hz_target)
order = get_ordered(tree)
hz_id = next(k for k, v in tree.items() if v["type"] == "HZ")

n_sf  = sum(1 for v in tree.values() if v["type"] == "SF")
n_ff  = sum(1 for v in tree.values() if v["type"] in ("FF","AND"))
n_if  = sum(1 for v in tree.values() if v["type"] == "IF")
depth = max((get_level(tree, k) for k in tree), default=0)

st.markdown("""
<div class="fta-header">
  <h1>🌳 FTA Risk Allocator v3</h1>
  <p>Nested SF→SF · Nested FF→FF · Dynamic gates · Live reallocation · Visualize · Export</p>
</div>""", unsafe_allow_html=True)

c1,c2,c3,c4,c5 = st.columns(5)
with c1: st.markdown(f'<div class="metric-card"><div class="mlabel">Hazard Target</div><div class="mvalue c-hz">{st.session_state.hz_target:.2E}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card"><div class="mlabel">System Failures</div><div class="mvalue c-sf">{n_sf}</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-card"><div class="mlabel">Following Failures</div><div class="mvalue c-ff">{n_ff}</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="metric-card"><div class="mlabel">Initiating Failures</div><div class="mvalue c-if">{n_if}</div></div>', unsafe_allow_html=True)
with c5: st.markdown(f'<div class="metric-card"><div class="mlabel">Tree Depth</div><div class="mvalue" style="color:#8b949e">{depth}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tab_viz, tab_table, tab_edit, tab_export = st.tabs([
    "🌳 Tree Visualization", "📋 Allocation Table", "✏️ Edit Nodes", "📥 Export"
])

# ═══════════════════════════════════════════════════════════════
# TAB 1 – VISUALIZATION
# ═══════════════════════════════════════════════════════════════
with tab_viz:
    st.markdown("#### Fault Tree Diagram")
    st.caption("Shows full tree at any nesting depth. Each box: Label · Name · Allocated Target.")

    col_viz, col_leg = st.columns([5, 1])

    with col_leg:
        st.markdown("""
**Node Types**

🟠 `HZ` Hazard
🔵 `SF` System Failure
🟢 `FF` Following Failure
🟣 `IF` Initiating Failure
🟤 `AND` Combined Faults

---
**Gates**

🔵 Oval = OR
🟣 Rect = AND

---
**Nesting**

SF can be child of SF
FF can be child of FF
        """)

    with col_viz:
        try:
            svg_str, svg_w, svg_h = build_svg(tree, alloc)
            st.markdown(
                f'<div style="overflow:auto;border:1px solid #30363d;border-radius:12px;padding:8px;max-height:680px">'
                f'{svg_str}</div>',
                unsafe_allow_html=True
            )
        except Exception as e:
            st.error(f"Visualization error: {e}")
            import traceback; st.code(traceback.format_exc())

# ═══════════════════════════════════════════════════════════════
# TAB 2 – ALLOCATION TABLE
# ═══════════════════════════════════════════════════════════════
with tab_table:
    st.markdown("#### Full Allocation Table")
    st.caption("Indented to show nesting depth. SF→SF and FF→FF nesting visible here.")

    rows_html = ""
    for nid in order:
        node  = tree[nid]
        lvl   = get_level(tree, nid)
        val   = alloc.get(nid, 0)
        t     = node["type"]
        vc    = VC_MAP.get(t, "sf")
        par   = tree[node["parent"]]["label"] if node["parent"] else "–"
        gc    = "g-and" if node["gate"]=="AND" else ("g-or" if node["gate"]=="OR" else "g-top")
        indent = lvl * 22
        par_type = tree[node["parent"]]["type"] if node["parent"] else "–"
        # Flag nested same-type
        nested_flag = ""
        if node["parent"] and par_type == t:
            nested_flag = f' <span style="font-size:0.65rem;color:#f97316;border:1px solid #f97316;border-radius:4px;padding:1px 5px">nested</span>'

        rows_html += f"""<tr>
          <td style="padding-left:{indent+10}px"><span class="badge b-{t}">{t}</span>{nested_flag}</td>
          <td style="padding-left:{indent+10}px"><span class="vm c-{vc}">{node.get('label',nid)}</span></td>
          <td style="color:#c9d1d9;font-size:0.82rem">{node.get('name','')}</td>
          <td style="color:#8b949e;font-size:0.78rem;max-width:200px">{node.get('desc','')}</td>
          <td style="color:#8b949e;font-size:0.78rem;font-family:monospace">{par}</td>
          <td><span class="{gc}">{node['gate']}</span></td>
          <td><span class="vm c-{vc}">{fmt(val)}</span></td>
        </tr>"""

    st.markdown(f"""
    <table class="tree-table">
    <thead><tr>
      <th>Type</th><th>Label</th><th>Name</th><th>Description</th>
      <th>Parent</th><th>Gate</th><th>Allocated (/yr)</th>
    </tr></thead>
    <tbody>{rows_html}</tbody>
    </table>""", unsafe_allow_html=True)

    # Summary by type
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📊 Summary by Type", expanded=False):
        rows_sum = []
        for nid in order:
            n = tree[nid]
            par = tree[n["parent"]] if n["parent"] else None
            rows_sum.append({
                "Label": n.get("label",""),
                "Type": n["type"],
                "Parent Label": par["label"] if par else "–",
                "Parent Type": par["type"] if par else "–",
                "Gate": n["gate"],
                "Depth": get_level(tree, nid),
                "Allocated (/yr)": fmt(alloc.get(nid,0)),
                "# Children": len(get_children(tree, nid)),
            })
        df = pd.DataFrame(rows_sum)
        st.dataframe(df, use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════
# TAB 3 – EDIT NODES
# ═══════════════════════════════════════════════════════════════
with tab_edit:
    st.markdown("#### ✏️ Edit Node Properties")
    st.caption("Edit label, name, description, gate and — for non-root nodes — reparent to any valid parent.")

    col_sel, col_form = st.columns([1, 2])

    with col_sel:
        st.markdown("**Select Node**")
        edit_options = {k: f"{v.get('label',k)}  ({v['type']})" for k, v in tree.items()}
        edit_key = st.selectbox("Node", list(edit_options.keys()),
                                format_func=lambda k: edit_options[k], key="edit_sel")

    with col_form:
        if edit_key:
            node = tree[edit_key]
            t    = node["type"]
            st.markdown(f'<div class="edit-card"><h4>Editing: {node.get("label",edit_key)} ({t})</h4>', unsafe_allow_html=True)

            e_label = st.text_input("Label",       value=node.get("label",""), key="el")
            e_name  = st.text_input("Name",         value=node.get("name",""),  key="en")
            e_desc  = st.text_area("Description",   value=node.get("desc",""),  key="ed", height=70)

            # Gate editor
            if t not in ("HZ", "IF"):
                gate_opts   = ["OR","AND"]
                current_g   = node.get("gate","OR")
                e_gate = st.selectbox("Gate Type", gate_opts,
                                      index=gate_opts.index(current_g) if current_g in gate_opts else 0,
                                      key="eg",
                                      help="Changing the gate updates how this node's budget is allocated to its children.")
            else:
                e_gate = node.get("gate","–")
                st.info(f"Gate `{e_gate}` is fixed for {t} nodes.")

            # Re-parent editor (not for HZ)
            if t != "HZ":
                allowed = VALID_PARENTS.get(t, [])
                valid_parents = {
                    k: f"{v.get('label',k)}  [{v['type']}]"
                    for k, v in tree.items()
                    if v["type"] in allowed and k != edit_key and k not in descendants(tree, edit_key)
                }
                cur_par = node.get("parent","")
                par_keys = list(valid_parents.keys())
                cur_idx  = par_keys.index(cur_par) if cur_par in par_keys else 0
                e_parent = st.selectbox("Parent Node", par_keys,
                                        index=cur_idx,
                                        format_func=lambda k: valid_parents[k],
                                        key="ep",
                                        help=f"Valid parent types for {t}: {allowed}")
            else:
                e_parent = None

            st.markdown("</div>", unsafe_allow_html=True)

            if st.button("💾 Save Changes", use_container_width=True, key="save_btn"):
                st.session_state.tree[edit_key]["label"] = e_label
                st.session_state.tree[edit_key]["name"]  = e_name
                st.session_state.tree[edit_key]["desc"]  = e_desc
                st.session_state.tree[edit_key]["gate"]  = e_gate
                if e_parent and not would_create_cycle(tree, edit_key, e_parent):
                    st.session_state.tree[edit_key]["parent"] = e_parent
                elif e_parent:
                    st.error("⚠️ Cannot reparent — would create a cycle.")
                st.success(f"✅ '{e_label}' saved!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### 📋 Full Node List")
    all_rows = []
    for nid in order:
        n   = tree[nid]
        par = tree[n["parent"]] if n["parent"] else None
        all_rows.append({
            "Label": n.get("label",""), "Name": n.get("name",""),
            "Type": n["type"], "Gate": n["gate"],
            "Parent": par["label"] if par else "–",
            "Parent Type": par["type"] if par else "–",
            "Depth": get_level(tree, nid),
            "Allocated (/yr)": fmt(alloc.get(nid,0)),
            "Description": n.get("desc","")
        })
    st.dataframe(pd.DataFrame(all_rows), use_container_width=True, hide_index=True)

# ═══════════════════════════════════════════════════════════════
# TAB 4 – EXPORT
# ═══════════════════════════════════════════════════════════════
with tab_export:
    st.markdown("#### 📥 Export Options")

    col_xl, col_json = st.columns(2)

    with col_xl:
        st.markdown("**Excel (.xlsx)**")
        st.caption("Full tree with all levels, names, gates, nesting depth and allocated targets.")

        def build_excel(tree, alloc, order):
            wb = Workbook(); ws = wb.active; ws.title = "FTA_Allocation"
            def fl(h): return PatternFill("solid",start_color=h,fgColor=h)
            def af(bold=False,color="000000",sz=10): return Font(name="Arial",bold=bold,color=color,size=sz)
            def tb():
                s=Side(style="thin",color="BFBFBF"); return Border(left=s,right=s,top=s,bottom=s)

            for i,w in enumerate([6,10,12,22,32,14,14,10,18,18],1):
                ws.column_dimensions[get_column_letter(i)].width = w

            ws.merge_cells("A1:J1")
            ws["A1"]="FAULT TREE ANALYSIS – RISK ALLOCATION (v3 – Nested SF/FF supported)"
            ws["A1"].font=af(bold=True,sz=13,color="FFFFFF"); ws["A1"].fill=fl("1F3864")
            ws["A1"].alignment=Alignment(horizontal="center",vertical="center"); ws.row_dimensions[1].height=26

            ws.merge_cells("A2:J2")
            ws["A2"]=f"Hazard Target: {st.session_state.hz_target:.2E} /yr  |  OR=÷n  |  AND=^(1/n)  |  SF→SF and FF→FF nesting supported"
            ws["A2"].font=af(sz=9,color="595959"); ws["A2"].fill=fl("F2F2F2"); ws.row_dimensions[2].height=14

            hdrs=["Depth","Type","Label","Name","Description","Parent Label","Parent Type","Gate","Allocated (/yr)","Calc Method"]
            for c,h in enumerate(hdrs,1):
                cell=ws.cell(row=3,column=c,value=h)
                cell.font=af(bold=True,sz=10,color="FFFFFF"); cell.fill=fl("2E75B6")
                cell.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); cell.border=tb()
            ws.row_dimensions[3].height=28

            BG={"HZ":"C00000","SF":"1F4E79","FF":"375623","IF":"833C00","AND":"4A148C"}
            LT={"HZ":"FFE7E7","SF":"DEEAF1","FF":"E2EFDA","IF":"FCE4D6","AND":"EAD1DC"}

            for i,nid in enumerate(order):
                n   = tree[nid]; lvl=get_level(tree,nid); val=alloc.get(nid,0); t=n["type"]
                par = tree[n["parent"]] if n["parent"] else None
                par_lbl  = par["label"] if par else "–"
                par_type = par["type"]  if par else "–"
                method   = "AND:^(1/n)" if n["gate"]=="AND" else ("OR:÷n" if n["gate"]=="OR" else "Given")
                r = i + 4
                vals = [lvl, t, "  "*lvl+n.get("label",nid), n.get("name",""), n.get("desc",""),
                        par_lbl, par_type, n["gate"], val, method]
                for c,v in enumerate(vals,1):
                    cell=ws.cell(row=r,column=c,value=v); cell.border=tb()
                    cell.alignment=Alignment(horizontal="left" if c in(3,4,5,10) else "center",
                                            vertical="center",wrap_text=(c in(4,5)))
                    if c==2:
                        cell.fill=fl(BG.get(t,"1F3864")); cell.font=af(bold=True,sz=9,color="FFFFFF")
                        cell.alignment=Alignment(horizontal="center",vertical="center")
                    elif c==9:
                        cell.number_format="0.00E+00"; cell.font=af(bold=True,sz=10,color=BG.get(t,"000000"))
                    else:
                        cell.fill=fl(LT.get(t,"F2F2F2") if c in(3,8) else "FFFFFF"); cell.font=af(sz=9)
                ws.row_dimensions[r].height=18

            out=io.BytesIO(); wb.save(out); out.seek(0)
            return out.getvalue()

        xl = build_excel(tree, alloc, order)
        st.download_button("⬇️ Download Excel", data=xl, file_name="FTA_Allocation_v3.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)

    with col_json:
        st.markdown("**JSON – Save & Reload Tree**")
        st.caption("Save your full tree to reload it later or share with colleagues.")

        tree_json = json.dumps({"hz_target": st.session_state.hz_target, "tree": st.session_state.tree}, indent=2)
        st.download_button("⬇️ Download JSON", data=tree_json, file_name="fta_tree_v3.json",
                           mime="application/json", use_container_width=True)

        st.markdown("**Load saved tree**")
        uploaded = st.file_uploader("Upload JSON", type="json", key="json_up")
        if uploaded:
            try:
                loaded = json.load(uploaded)
                if "tree" in loaded and "hz_target" in loaded:
                    st.session_state.tree      = loaded["tree"]
                    st.session_state.hz_target = loaded["hz_target"]
                    st.success("✅ Tree loaded!"); st.rerun()
                else:
                    st.error("Invalid format.")
            except Exception as e:
                st.error(f"Error: {e}")

    st.markdown("---")
    st.markdown("#### 📐 Allocation & Nesting Rules")
    st.markdown("""
| Gate | Formula | Use when |
|------|---------|----------|
| **OR** | `Child = Parent ÷ n` | Any single child causes the parent |
| **AND** | `Child = Parent ^ (1/n)` | All children must fail simultaneously |

**Supported nesting:**

| Node | Valid parent types |
|------|-------------------|
| SF | HZ · **SF** · AND |
| FF | SF · **FF** · AND |
| IF | FF |
| AND | HZ · SF · FF |

When an SF is nested under another SF, it receives its allocated target from the parent SF — the full cascade works recursively at any depth.
    """)
