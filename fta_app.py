import streamlit as st
import pandas as pd
import math
import io
import json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="FTA Risk Allocator", page_icon="🌳", layout="wide")

# ── CSS ───────────────────────────────────────────────────────────────────────
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
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
def default_tree():
    return {
        "HZ01": {"id":"HZ01","label":"HZxx","name":"Pressurized Fluid Hazard","type":"HZ","parent":None,"gate":"–","desc":"Top-level Hazard Event"},
        "SF01": {"id":"SF01","label":"SF01","name":"System Failure 01","type":"SF","parent":"HZ01","gate":"OR","desc":"System Failure 01"},
        "SF02": {"id":"SF02","label":"SF02","name":"System Failure 02","type":"SF","parent":"HZ01","gate":"OR","desc":"System Failure 02"},
        "SF03": {"id":"SF03","label":"SF03","name":"System Failure 03","type":"SF","parent":"HZ01","gate":"OR","desc":"System Failure 03"},
        "AND01":{"id":"AND01","label":"CombFaults","name":"Combined Faults","type":"AND","parent":"SF03","gate":"AND","desc":"Combined Faults (AND gate)"},
        "FF01": {"id":"FF01","label":"FF01","name":"Following Failure 01","type":"FF","parent":"SF01","gate":"OR","desc":"Following Failure 01"},
        "FF02": {"id":"FF02","label":"FF02","name":"Following Failure 02","type":"FF","parent":"SF01","gate":"OR","desc":"Following Failure 02"},
        "FF03": {"id":"FF03","label":"FF03","name":"Following Failure 03","type":"FF","parent":"SF02","gate":"OR","desc":"Following Failure 03"},
        "FF04": {"id":"FF04","label":"FF04","name":"Following Failure 04","type":"FF","parent":"SF02","gate":"OR","desc":"Following Failure 04"},
        "FF05": {"id":"FF05","label":"FF05","name":"Following Failure 05","type":"FF","parent":"AND01","gate":"AND","desc":"Following Failure 05"},
        "FF06": {"id":"FF06","label":"FF06","name":"Following Failure 06","type":"FF","parent":"AND01","gate":"AND","desc":"Following Failure 06"},
        "IF01": {"id":"IF01","label":"IF01","name":"Initiating Failure 01","type":"IF","parent":"FF01","gate":"OR","desc":"Initiating Failure 01"},
        "IF02": {"id":"IF02","label":"IF02","name":"Initiating Failure 02","type":"IF","parent":"FF01","gate":"OR","desc":"Initiating Failure 02"},
        "IF03": {"id":"IF03","label":"IF03","name":"Initiating Failure 03","type":"IF","parent":"FF02","gate":"OR","desc":"Initiating Failure 03"},
        "IF04": {"id":"IF04","label":"IF04","name":"Initiating Failure 04","type":"IF","parent":"FF02","gate":"OR","desc":"Initiating Failure 04"},
        "IF05": {"id":"IF05","label":"IF05","name":"Initiating Failure 05","type":"IF","parent":"FF03","gate":"OR","desc":"Initiating Failure 05"},
        "IF06": {"id":"IF06","label":"IF06","name":"Initiating Failure 06","type":"IF","parent":"FF03","gate":"OR","desc":"Initiating Failure 06"},
        "IF07": {"id":"IF07","label":"IF07","name":"Initiating Failure 07","type":"IF","parent":"FF04","gate":"OR","desc":"Initiating Failure 07"},
        "IF08": {"id":"IF08","label":"IF08","name":"Initiating Failure 08","type":"IF","parent":"FF04","gate":"OR","desc":"Initiating Failure 08"},
        "IF09": {"id":"IF09","label":"IF09","name":"Initiating Failure 09","type":"IF","parent":"FF05","gate":"OR","desc":"Initiating Failure 09"},
        "IF10": {"id":"IF10","label":"IF10","name":"Initiating Failure 10","type":"IF","parent":"FF05","gate":"OR","desc":"Initiating Failure 10"},
        "IF11": {"id":"IF11","label":"IF11","name":"Initiating Failure 11","type":"IF","parent":"FF06","gate":"OR","desc":"Initiating Failure 11"},
        "IF12": {"id":"IF12","label":"IF12","name":"Initiating Failure 12","type":"IF","parent":"FF06","gate":"OR","desc":"Initiating Failure 12"},
    }

if "tree"       not in st.session_state: st.session_state.tree      = default_tree()
if "hz_target"  not in st.session_state: st.session_state.hz_target = 1e-8
if "next_id"    not in st.session_state: st.session_state.next_id   = 100

# ── Engine ────────────────────────────────────────────────────────────────────
def get_children(tree, pid):
    return [n for n in tree.values() if n["parent"] == pid]

def allocate_tree(tree, hz_target):
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

def fmt(v): return f"{v:.3E}" if v is not None else "–"

def descendants(tree, tid):
    d = []
    for k, n in tree.items():
        if n["parent"] == tid:
            d.append(k); d.extend(descendants(tree, k))
    return d

# ── Tree SVG visualizer ───────────────────────────────────────────────────────
def build_svg(tree, alloc):
    """Build a full top-down SVG fault tree."""
    TYPE_COLOR = {
        "HZ":  {"box":"#f97316","text":"#ffffff","border":"#f97316"},
        "SF":  {"box":"#1a3a5c","text":"#58a6ff","border":"#58a6ff"},
        "FF":  {"box":"#1a3d1a","text":"#3fb950","border":"#3fb950"},
        "IF":  {"box":"#2a1a3d","text":"#d2a8ff","border":"#d2a8ff"},
        "AND": {"box":"#2d1a3d","text":"#e040fb","border":"#e040fb"},
    }
    GATE_COLOR = {"OR":"#58a6ff","AND":"#e040fb","–":"#8b949e"}

    BOX_W, BOX_H = 130, 52
    H_GAP, V_GAP = 20, 90
    GATE_R = 14

    # BFS to assign positions
    order = get_ordered(tree)
    hz_id = order[0]

    # Group nodes by level
    levels = {}
    for nid in order:
        lvl = get_level(tree, nid)
        levels.setdefault(lvl, []).append(nid)

    max_lvl = max(levels.keys())

    # Assign x positions within each level
    pos = {}
    for lvl, nodes in levels.items():
        total_w = len(nodes) * BOX_W + (len(nodes)-1) * H_GAP
        start_x = -total_w / 2
        for i, nid in enumerate(nodes):
            cx = start_x + i * (BOX_W + H_GAP) + BOX_W/2
            cy = lvl * (BOX_H + V_GAP + GATE_R*2) + BOX_H/2
            pos[nid] = (cx, cy)

    # Canvas size
    all_x = [p[0] for p in pos.values()]
    all_y = [p[1] for p in pos.values()]
    min_x, max_x = min(all_x) - BOX_W, max(all_x) + BOX_W
    min_y, max_y = min(all_y) - BOX_H, max(all_y) + BOX_H + 20
    W = max_x - min_x + 60
    H = max_y - min_y + 60
    ox, oy = -min_x + 30, -min_y + 30  # offset

    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{int(W)}" height="{int(H)}" style="background:#0d1117;border-radius:12px">']
    lines.append('<defs>')
    lines.append('<marker id="arr" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#30363d"/></marker>')
    # Gate symbols
    lines.append('<symbol id="gate-or" viewBox="0 0 28 28"><ellipse cx="14" cy="14" rx="12" ry="12" fill="#0d2136" stroke="#58a6ff" stroke-width="2"/><text x="14" y="19" text-anchor="middle" font-size="9" fill="#58a6ff" font-family="monospace" font-weight="bold">OR</text></symbol>')
    lines.append('<symbol id="gate-and" viewBox="0 0 28 28"><rect x="2" y="2" width="24" height="24" rx="6" fill="#2d1a3d" stroke="#e040fb" stroke-width="2"/><text x="14" y="18" text-anchor="middle" font-size="8" fill="#e040fb" font-family="monospace" font-weight="bold">AND</text></symbol>')
    lines.append('</defs>')

    # Draw connections + gates
    for nid in order:
        node = tree[nid]
        if not node["parent"]: continue
        px, py = pos[node["parent"]]
        cx, cy = pos[nid]

        # Gate position (midpoint between parent bottom and child top)
        gate_y = py + BOX_H/2 + GATE_R + 4
        gate_x = (px + cx) / 2

        # Line: parent bottom → gate
        lines.append(f'<line x1="{px+ox:.1f}" y1="{py+oy+BOX_H/2:.1f}" x2="{gate_x+ox:.1f}" y2="{gate_y+oy:.1f}" stroke="#30363d" stroke-width="1.5"/>')
        # Line: gate → child top
        lines.append(f'<line x1="{gate_x+ox:.1f}" y1="{gate_y+oy+GATE_R:.1f}" x2="{cx+ox:.1f}" y2="{cy+oy-BOX_H/2:.1f}" stroke="#30363d" stroke-width="1.5" marker-end="url(#arr)"/>')

        # Gate symbol
        g_sym = "gate-and" if node["gate"] == "AND" else "gate-or"
        lines.append(f'<use href="#{g_sym}" x="{gate_x+ox-GATE_R:.1f}" y="{gate_y+oy-GATE_R:.1f}" width="{GATE_R*2}" height="{GATE_R*2}"/>')

    # Draw boxes
    for nid in order:
        node = tree[nid]
        cx, cy = pos[nid]
        x, y = cx + ox - BOX_W/2, cy + oy - BOX_H/2
        t = node["type"]
        col = TYPE_COLOR.get(t, TYPE_COLOR["SF"])
        val = alloc.get(nid, 0)

        # Box shadow
        lines.append(f'<rect x="{x+2:.1f}" y="{y+2:.1f}" width="{BOX_W}" height="{BOX_H}" rx="7" fill="#000000" opacity="0.4"/>')
        # Box fill
        lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{BOX_W}" height="{BOX_H}" rx="7" fill="{col["box"]}" stroke="{col["border"]}" stroke-width="1.5"/>')

        # Label (top)
        lbl = node.get("label", nid)[:14]
        lines.append(f'<text x="{cx+ox:.1f}" y="{y+16:.1f}" text-anchor="middle" font-size="10" font-weight="bold" fill="{col["text"]}" font-family="IBM Plex Mono,monospace">{lbl}</text>')

        # Name (middle, truncated)
        name = node.get("name", node.get("desc",""))[:18]
        lines.append(f'<text x="{cx+ox:.1f}" y="{y+28:.1f}" text-anchor="middle" font-size="7.5" fill="{col["text"]}" opacity="0.85" font-family="IBM Plex Sans,sans-serif">{name}</text>')

        # Allocated value (bottom)
        val_str = f"{val:.2E}"
        lines.append(f'<text x="{cx+ox:.1f}" y="{y+42:.1f}" text-anchor="middle" font-size="8" fill="{col["text"]}" opacity="0.7" font-family="IBM Plex Mono,monospace">{val_str}</text>')

    lines.append('</svg>')
    return "\n".join(lines), int(W), int(H)

# ── Sidebar ───────────────────────────────────────────────────────────────────
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
                              help="SF=System Failure, FF=Following Failure, IF=Initiating Failure, AND=Combined Faults gate")

    gate_choice = st.selectbox("Gate Type", ["OR","AND"],
                                help="OR: any child causes parent | AND: all children must fail together")

    if node_type == "SF":
        parents = {k: v["label"] for k, v in tree.items() if v["type"]=="HZ"}
    elif node_type == "AND":
        parents = {k: v["label"] for k, v in tree.items() if v["type"]=="SF"}
    elif node_type == "FF":
        parents = {k: v["label"] for k, v in tree.items() if v["type"] in ("SF","AND")}
    else:
        parents = {k: v["label"] for k, v in tree.items() if v["type"]=="FF"}

    if parents:
        par_key = st.selectbox("Parent", list(parents.keys()),
                               format_func=lambda k: f"{tree[k]['label']} ({tree[k]['type']})")
        new_label = st.text_input("Label (short ID)", value=f"{node_type}{st.session_state.next_id:02d}")
        new_name  = st.text_input("Name (full name)", value=f"New {node_type} name")
        new_desc  = st.text_input("Description", value=f"Describe this {node_type}")
        gate_val  = "AND" if node_type == "AND" else gate_choice

        if st.button("➕ Add Node", use_container_width=True):
            nid = f"N{st.session_state.next_id}"
            st.session_state.tree[nid] = {
                "id": nid, "label": new_label, "name": new_name,
                "type": node_type, "parent": par_key,
                "gate": gate_val, "desc": new_desc
            }
            st.session_state.next_id += 1
            st.rerun()
    else:
        st.info(f"No valid parents for {node_type}. Add a parent first.")

    st.markdown("---")
    st.markdown("**🗑️ Delete Node**")
    deletable = {k: f"{v['label']} ({v['type']})" for k, v in tree.items() if v["type"] != "HZ"}
    if deletable:
        del_k = st.selectbox("Node to delete", list(deletable.keys()),
                             format_func=lambda k: deletable[k])
        if st.button("🗑️ Delete (+ children)", use_container_width=True):
            for d in [del_k] + descendants(tree, del_k):
                st.session_state.tree.pop(d, None)
            st.rerun()

    st.markdown("---")
    if st.button("🔄 Reset to Default", use_container_width=True):
        for k in ["tree","hz_target","next_id"]: st.session_state.pop(k, None)
        st.rerun()

# ── Compute ───────────────────────────────────────────────────────────────────
tree  = st.session_state.tree
alloc = allocate_tree(tree, st.session_state.hz_target)
order = get_ordered(tree)
hz_id = next(k for k, v in tree.items() if v["type"]=="HZ")

n_sf = sum(1 for v in tree.values() if v["type"]=="SF")
n_ff = sum(1 for v in tree.values() if v["type"] in ("FF","AND"))
n_if = sum(1 for v in tree.values() if v["type"]=="IF")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="fta-header">
  <h1>🌳 FTA Risk Allocator v2</h1>
  <p>Dynamic fault tree · Visualize · Edit nodes · Change gates · Auto-reallocate on any change</p>
</div>""", unsafe_allow_html=True)

# Metrics
c1,c2,c3,c4 = st.columns(4)
with c1: st.markdown(f'<div class="metric-card"><div class="mlabel">Hazard Target</div><div class="mvalue c-hz">{st.session_state.hz_target:.2E}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card"><div class="mlabel">System Failures</div><div class="mvalue c-sf">{n_sf}</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-card"><div class="mlabel">Following Failures</div><div class="mvalue c-ff">{n_ff}</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="metric-card"><div class="mlabel">Initiating Failures</div><div class="mvalue c-if">{n_if}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Main tabs ─────────────────────────────────────────────────────────────────
tab_viz, tab_table, tab_edit, tab_export = st.tabs([
    "🌳 Tree Visualization",
    "📋 Allocation Table",
    "✏️ Edit Nodes",
    "📥 Export"
])

# ═════════════════════════════════════════════════════════════
# TAB 1 – VISUALIZATION
# ═════════════════════════════════════════════════════════════
with tab_viz:
    st.markdown("#### Fault Tree Diagram")
    st.caption("Boxes show: Label · Name · Allocated Target. Gate symbols shown on connections.")

    col_viz, col_legend = st.columns([4,1])

    with col_legend:
        st.markdown("""
**Legend**

🟠 **Hazard**
Top-level event

🔵 **SF**
System Failure

🟢 **FF**
Following Failure

🟣 **IF**
Initiating Failure

🟤 **AND**
Combined Faults

---
**Gates**

🔵 `OR` oval
Any child → parent

🟣 `AND` rect
All children → parent
        """)

    with col_viz:
        try:
            svg_str, svg_w, svg_h = build_svg(tree, alloc)
            # Wrap in scrollable div
            st.markdown(
                f'<div style="overflow:auto;border:1px solid #30363d;border-radius:12px;padding:8px">'
                f'{svg_str}</div>',
                unsafe_allow_html=True
            )
        except Exception as e:
            st.error(f"Visualization error: {e}")

# ═════════════════════════════════════════════════════════════
# TAB 2 – ALLOCATION TABLE
# ═════════════════════════════════════════════════════════════
with tab_table:
    st.markdown("#### Full Allocation Table")
    VC = {"HZ":"hz","SF":"sf","FF":"ff","IF":"if","AND":"and"}
    rows = ""
    for nid in order:
        node  = tree[nid]
        lvl   = get_level(tree, nid)
        val   = alloc.get(nid,0)
        t     = node["type"]
        vc    = VC.get(t,"sf")
        par   = tree[node["parent"]]["label"] if node["parent"] else "–"
        gc    = "g-and" if node["gate"]=="AND" else ("g-or" if node["gate"]=="OR" else "g-top")
        indent= lvl * 22

        rows += f"""<tr>
          <td style="padding-left:{indent+10}px"><span class="badge b-{t}">{t}</span></td>
          <td style="padding-left:{indent+10}px"><span class="vm c-{vc}">{node.get('label',nid)}</span></td>
          <td style="color:#c9d1d9;font-size:0.82rem">{node.get('name','')}</td>
          <td style="color:#8b949e;font-size:0.8rem;max-width:220px">{node.get('desc','')}</td>
          <td style="color:#8b949e;font-size:0.78rem;font-family:'IBM Plex Mono',monospace">{par}</td>
          <td><span class="{gc}">{node['gate']}</span></td>
          <td><span class="vm c-{vc}">{fmt(val)}</span></td>
        </tr>"""

    st.markdown(f"""
    <table class="tree-table">
    <thead><tr>
      <th>Type</th><th>Label</th><th>Name</th><th>Description</th>
      <th>Parent</th><th>Gate</th><th>Allocated (/yr)</th>
    </tr></thead>
    <tbody>{rows}</tbody>
    </table>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Breakdown expanders
    with st.expander("📊 Level Summaries", expanded=False):
        t1, t2, t3 = st.tabs(["🔵 System Failures","🟢 Following Failures","🟣 Initiating Failures"])
        with t1:
            rows_sf = []
            for nid in order:
                n = tree[nid]
                if n["type"] != "SF": continue
                ch = get_children(tree, nid)
                rows_sf.append({"Label":n.get("label",""),"Name":n.get("name",""),"Description":n.get("desc",""),
                    "# Children":len(ch),"Gate→Children":ch[0]["gate"] if ch else "–",
                    "Allocated (/yr)":fmt(alloc.get(nid,0)),"Per Child (/yr)":fmt(alloc.get(ch[0]["id"],0)) if ch else "–"})
            st.dataframe(pd.DataFrame(rows_sf), use_container_width=True, hide_index=True)
        with t2:
            rows_ff = []
            for nid in order:
                n = tree[nid]
                if n["type"] not in ("FF","AND"): continue
                ch = get_children(tree, nid); par = tree[n["parent"]]["label"] if n["parent"] else "–"
                rows_ff.append({"Label":n.get("label",""),"Name":n.get("name",""),"Type":n["type"],"Parent":par,
                    "Gate":n["gate"],"# IFs":len(ch),
                    "Allocated (/yr)":fmt(alloc.get(nid,0)),"Per IF (/yr)":fmt(alloc.get(ch[0]["id"],0)) if ch else "–"})
            st.dataframe(pd.DataFrame(rows_ff), use_container_width=True, hide_index=True)
        with t3:
            rows_if = []
            for nid in order:
                n = tree[nid]
                if n["type"] != "IF": continue
                par = tree[n["parent"]]["label"] if n["parent"] else "–"
                sibs = len(get_children(tree, n["parent"])) if n["parent"] else 1
                rows_if.append({"Label":n.get("label",""),"Name":n.get("name",""),"Description":n.get("desc",""),
                    "Parent FF":par,"# Siblings":sibs,"Allocated (/yr)":fmt(alloc.get(nid,0))})
            st.dataframe(pd.DataFrame(rows_if), use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════
# TAB 3 – EDIT NODES
# ═════════════════════════════════════════════════════════════
with tab_edit:
    st.markdown("#### ✏️ Edit Node Properties")
    st.caption("Select any node to edit its label, name, description and gate type. Changes reflect instantly in the tree.")

    col_sel, col_form = st.columns([1, 2])

    with col_sel:
        st.markdown("**Select Node**")
        edit_options = {k: f"{v.get('label',k)} ({v['type']})" for k, v in tree.items()}
        edit_key = st.selectbox("Node", list(edit_options.keys()),
                                format_func=lambda k: edit_options[k],
                                key="edit_select")

    with col_form:
        if edit_key:
            node = tree[edit_key]
            st.markdown(f'<div class="edit-card"><h4>Editing: {node.get("label", edit_key)} ({node["type"]})</h4>', unsafe_allow_html=True)

            e_label = st.text_input("Label (short ID)", value=node.get("label",""), key="e_label")
            e_name  = st.text_input("Name (full name)", value=node.get("name",""),  key="e_name")
            e_desc  = st.text_area("Description",       value=node.get("desc",""),  key="e_desc", height=80)

            # Gate selector (not for HZ or IF)
            if node["type"] not in ("HZ","IF"):
                current_gate = node.get("gate","OR")
                gate_opts = ["OR","AND"]
                e_gate = st.selectbox("Gate Type",
                                      gate_opts,
                                      index=gate_opts.index(current_gate) if current_gate in gate_opts else 0,
                                      key="e_gate",
                                      help="OR: any child causes this node | AND: all children must fail")
            else:
                e_gate = node.get("gate","–")
                st.info(f"Gate: `{e_gate}` (fixed for {node['type']} nodes)")

            st.markdown("</div>", unsafe_allow_html=True)

            if st.button("💾 Save Changes", use_container_width=True, key="save_edit"):
                st.session_state.tree[edit_key]["label"] = e_label
                st.session_state.tree[edit_key]["name"]  = e_name
                st.session_state.tree[edit_key]["desc"]  = e_desc
                st.session_state.tree[edit_key]["gate"]  = e_gate
                # If gate changed on a parent, update children's gate reference
                for k, n in st.session_state.tree.items():
                    if n["parent"] == edit_key and node["type"] not in ("HZ","IF"):
                        st.session_state.tree[k]["gate"] = e_gate
                st.success(f"✅ '{e_label}' updated!")
                st.rerun()

    st.markdown("---")
    st.markdown("#### 📋 All Nodes Overview")
    all_rows = []
    for nid in order:
        n = tree[nid]
        all_rows.append({
            "ID": nid,
            "Label": n.get("label",""),
            "Name": n.get("name",""),
            "Type": n["type"],
            "Gate": n["gate"],
            "Parent": tree[n["parent"]]["label"] if n["parent"] else "–",
            "Description": n.get("desc",""),
            "Allocated (/yr)": fmt(alloc.get(nid,0))
        })
    st.dataframe(pd.DataFrame(all_rows), use_container_width=True, hide_index=True)

# ═════════════════════════════════════════════════════════════
# TAB 4 – EXPORT
# ═════════════════════════════════════════════════════════════
with tab_export:
    st.markdown("#### 📥 Export Options")

    col_xl, col_json = st.columns(2)

    # Excel export
    with col_xl:
        st.markdown("**Excel (.xlsx)**")
        st.caption("Full tree with allocated values, names, descriptions and gate types.")

        def build_excel(tree, alloc, order):
            wb = Workbook(); ws = wb.active; ws.title = "FTA_Allocation"
            def fl(h): return PatternFill("solid",start_color=h,fgColor=h)
            def af(bold=False,color="000000",sz=10): return Font(name="Arial",bold=bold,color=color,size=sz)
            def tb():
                s=Side(style="thin",color="BFBFBF"); return Border(left=s,right=s,top=s,bottom=s)

            for i,w in enumerate([6,12,18,28,36,14,10,18,18],1):
                ws.column_dimensions[get_column_letter(i)].width = w

            ws.merge_cells("A1:I1")
            ws["A1"]="FAULT TREE ANALYSIS – RISK ALLOCATION"
            ws["A1"].font=af(bold=True,sz=13,color="FFFFFF"); ws["A1"].fill=fl("1F3864")
            ws["A1"].alignment=Alignment(horizontal="center",vertical="center"); ws.row_dimensions[1].height=26

            ws.merge_cells("A2:I2")
            ws["A2"]=f"Hazard Target: {st.session_state.hz_target:.2E} /yr  |  OR=÷n  |  AND=^(1/n)"
            ws["A2"].font=af(sz=9,color="595959"); ws["A2"].fill=fl("F2F2F2"); ws.row_dimensions[2].height=14

            hdrs=["Lvl","Type","Label","Name","Description","Parent","Gate","Allocated (/yr)","Calc Method"]
            for c,h in enumerate(hdrs,1):
                cell=ws.cell(row=3,column=c,value=h)
                cell.font=af(bold=True,sz=10,color="FFFFFF"); cell.fill=fl("2E75B6")
                cell.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); cell.border=tb()
            ws.row_dimensions[3].height=28

            BG={"HZ":"C00000","SF":"1F4E79","FF":"375623","IF":"833C00","AND":"4A148C"}
            LT={"HZ":"FFE7E7","SF":"DEEAF1","FF":"E2EFDA","IF":"FCE4D6","AND":"EAD1DC"}

            for i,nid in enumerate(order):
                n=tree[nid]; lvl=get_level(tree,nid); val=alloc.get(nid,0); t=n["type"]
                par=tree[n["parent"]]["label"] if n["parent"] else "–"
                method="AND:^(1/n)" if n["gate"]=="AND" else ("OR:÷n" if n["gate"]=="OR" else "Given")
                r=i+4
                vals=[lvl,t,"  "*lvl+n.get("label",nid),n.get("name",""),n.get("desc",""),par,n["gate"],val,method]
                for c,v in enumerate(vals,1):
                    cell=ws.cell(row=r,column=c,value=v); cell.border=tb()
                    cell.alignment=Alignment(horizontal="left" if c in(3,4,5,9) else "center",vertical="center",wrap_text=(c in(4,5)))
                    if c==2:
                        cell.fill=fl(BG.get(t,"1F3864")); cell.font=af(bold=True,sz=9,color="FFFFFF")
                        cell.alignment=Alignment(horizontal="center",vertical="center")
                    elif c==8:
                        cell.number_format="0.00E+00"; cell.font=af(bold=True,sz=10,color=BG.get(t,"000000"))
                    else:
                        cell.fill=fl(LT.get(t,"F2F2F2") if c in(3,7) else "FFFFFF"); cell.font=af(sz=9)
                ws.row_dimensions[r].height=18

            out=io.BytesIO(); wb.save(out); out.seek(0)
            return out.getvalue()

        xl = build_excel(tree, alloc, order)
        st.download_button("⬇️ Download Excel", data=xl,
                           file_name="FTA_Allocation.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)

    # JSON export/import
    with col_json:
        st.markdown("**JSON (Save/Load tree)**")
        st.caption("Export your full tree to JSON so you can reload it later.")

        tree_json = json.dumps({
            "hz_target": st.session_state.hz_target,
            "tree": st.session_state.tree
        }, indent=2)

        st.download_button("⬇️ Download JSON", data=tree_json,
                           file_name="fta_tree.json",
                           mime="application/json",
                           use_container_width=True)

        st.markdown("**Load saved JSON**")
        uploaded = st.file_uploader("Upload fta_tree.json", type="json", key="json_upload")
        if uploaded:
            try:
                loaded = json.load(uploaded)
                if "tree" in loaded and "hz_target" in loaded:
                    st.session_state.tree      = loaded["tree"]
                    st.session_state.hz_target = loaded["hz_target"]
                    st.success("✅ Tree loaded successfully!")
                    st.rerun()
                else:
                    st.error("Invalid JSON format.")
            except Exception as e:
                st.error(f"Error loading: {e}")

    st.markdown("---")
    st.markdown("#### 📐 Allocation Logic Reference")
    st.markdown("""
| Gate | Formula | When to use |
|------|---------|-------------|
| **OR** | `Child = Parent ÷ n` | Any single child failure causes the parent |
| **AND** | `Child = Parent^(1/n)` | All children must fail simultaneously (Combined Faults) |

**Auto-reallocation rule:** Adding or removing any node instantly re-divides the parent budget equally across all current siblings at that level.
    """)
