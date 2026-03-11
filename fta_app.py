import streamlit as st
import pandas as pd
import math
import io
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
.metric-card { background:#161b22; border:1px solid #30363d; border-radius:8px; padding:14px 18px; }
.metric-card .mlabel { font-size:0.68rem; color:#8b949e; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; }
.metric-card .mvalue { font-family:'IBM Plex Mono',monospace; font-size:1.2rem; font-weight:700; }
.tree-table { width:100%; border-collapse:collapse; margin-top:6px; font-size:0.84rem; }
.tree-table th { background:#1c2128; color:#8b949e; font-size:0.68rem; text-transform:uppercase; letter-spacing:1px; padding:10px 12px; text-align:left; border-bottom:1px solid #30363d; font-family:'IBM Plex Mono',monospace; }
.tree-table td { padding:8px 12px; border-bottom:1px solid #21262d; vertical-align:middle; }
.tree-table tr:hover td { background:#1c2128; }
.badge { display:inline-block; padding:2px 8px; border-radius:10px; font-size:0.7rem; font-weight:700; font-family:'IBM Plex Mono',monospace; }
.b-HZ { background:#3d1a00; color:#f97316; border:1px solid #f97316; }
.b-SF { background:#0d2136; color:#58a6ff; border:1px solid #58a6ff; }
.b-FF { background:#0d2b14; color:#3fb950; border:1px solid #3fb950; }
.b-IF { background:#1e0d36; color:#d2a8ff; border:1px solid #d2a8ff; }
.b-AND { background:#2d1a3d; color:#e040fb; border:1px solid #e040fb; }
.g-or { color:#58a6ff; font-weight:700; font-family:'IBM Plex Mono'; font-size:0.78rem; }
.g-and { color:#e040fb; font-weight:700; font-family:'IBM Plex Mono'; font-size:0.78rem; }
.g-top { color:#8b949e; font-size:0.78rem; }
.vm { font-family:'IBM Plex Mono',monospace; font-size:0.83rem; font-weight:600; }
.c-hz{color:#f97316} .c-sf{color:#58a6ff} .c-ff{color:#3fb950} .c-if{color:#d2a8ff} .c-and{color:#e040fb}
div[data-testid="stExpander"] { background:#161b22; border:1px solid #30363d; border-radius:8px; }
.stButton button { background:#1c2128 !important; border:1px solid #30363d !important; color:#e6edf3 !important; border-radius:6px !important; }
.stButton button:hover { border-color:#58a6ff !important; color:#58a6ff !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
def init_state():
    if "tree" not in st.session_state:
        st.session_state.tree = {
            "HZ01": {"id":"HZ01","label":"HZxx","type":"HZ","parent":None,"gate":"–","desc":"Top-level Hazard Event"},
            "SF01": {"id":"SF01","label":"SF01","type":"SF","parent":"HZ01","gate":"OR","desc":"System Failure 01"},
            "SF02": {"id":"SF02","label":"SF02","type":"SF","parent":"HZ01","gate":"OR","desc":"System Failure 02"},
            "SF03": {"id":"SF03","label":"SF03","type":"SF","parent":"HZ01","gate":"OR","desc":"System Failure 03"},
            "AND01":{"id":"AND01","label":"CombFaults","type":"AND","parent":"SF03","gate":"AND","desc":"Combined Faults (AND gate)"},
            "FF01": {"id":"FF01","label":"FF01","type":"FF","parent":"SF01","gate":"OR","desc":"Following Failure 01"},
            "FF02": {"id":"FF02","label":"FF02","type":"FF","parent":"SF01","gate":"OR","desc":"Following Failure 02"},
            "FF03": {"id":"FF03","label":"FF03","type":"FF","parent":"SF02","gate":"OR","desc":"Following Failure 03"},
            "FF04": {"id":"FF04","label":"FF04","type":"FF","parent":"SF02","gate":"OR","desc":"Following Failure 04"},
            "FF05": {"id":"FF05","label":"FF05","type":"FF","parent":"AND01","gate":"AND","desc":"Following Failure 05"},
            "FF06": {"id":"FF06","label":"FF06","type":"FF","parent":"AND01","gate":"AND","desc":"Following Failure 06"},
            "IF01": {"id":"IF01","label":"IF01","type":"IF","parent":"FF01","gate":"OR","desc":"Initiating Failure 01"},
            "IF02": {"id":"IF02","label":"IF02","type":"IF","parent":"FF01","gate":"OR","desc":"Initiating Failure 02"},
            "IF03": {"id":"IF03","label":"IF03","type":"IF","parent":"FF02","gate":"OR","desc":"Initiating Failure 03"},
            "IF04": {"id":"IF04","label":"IF04","type":"IF","parent":"FF02","gate":"OR","desc":"Initiating Failure 04"},
            "IF05": {"id":"IF05","label":"IF05","type":"IF","parent":"FF03","gate":"OR","desc":"Initiating Failure 05"},
            "IF06": {"id":"IF06","label":"IF06","type":"IF","parent":"FF03","gate":"OR","desc":"Initiating Failure 06"},
            "IF07": {"id":"IF07","label":"IF07","type":"IF","parent":"FF04","gate":"OR","desc":"Initiating Failure 07"},
            "IF08": {"id":"IF08","label":"IF08","type":"IF","parent":"FF04","gate":"OR","desc":"Initiating Failure 08"},
            "IF09": {"id":"IF09","label":"IF09","type":"IF","parent":"FF05","gate":"OR","desc":"Initiating Failure 09"},
            "IF10": {"id":"IF10","label":"IF10","type":"IF","parent":"FF05","gate":"OR","desc":"Initiating Failure 10"},
            "IF11": {"id":"IF11","label":"IF11","type":"IF","parent":"FF06","gate":"OR","desc":"Initiating Failure 11"},
            "IF12": {"id":"IF12","label":"IF12","type":"IF","parent":"FF06","gate":"OR","desc":"Initiating Failure 12"},
        }
    if "hz_target" not in st.session_state:
        st.session_state.hz_target = 1e-8
    if "next_id" not in st.session_state:
        st.session_state.next_id = 100

init_state()

# ── Allocation engine ─────────────────────────────────────────────────────────
def get_children(tree, pid):
    return [n for n in tree.values() if n["parent"] == pid]

def allocate_tree(tree, hz_target):
    alloc = {}
    def recurse(nid, budget):
        alloc[nid] = budget
        children = get_children(tree, nid)
        if not children: return
        n = len(children)
        gate = children[0]["gate"]
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

def fmt(v):
    return f"{v:.3E}" if v is not None else "–"

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ FTA Controls")
    st.markdown("---")

    # Hazard target
    st.markdown("**🎯 Set Hazard Target**")
    hz_exp  = st.number_input("Exponent (10ˣ)", value=-8, min_value=-20, max_value=-1, step=1)
    hz_mant = st.number_input("Mantissa", value=1.0, min_value=0.1, max_value=9.9, step=0.1, format="%.1f")
    new_target = hz_mant * (10 ** hz_exp)
    st.session_state.hz_target = new_target
    st.success(f"Target: **{new_target:.2E}** /yr")

    st.markdown("---")
    st.markdown("**➕ Add Node**")
    tree = st.session_state.tree

    node_type = st.selectbox("Node Type", ["SF","FF","IF","AND"])
    if node_type == "SF":
        parents = {k: v["label"] for k, v in tree.items() if v["type"]=="HZ"}
    elif node_type == "AND":
        parents = {k: v["label"] for k, v in tree.items() if v["type"]=="SF"}
    elif node_type == "FF":
        parents = {k: v["label"] for k, v in tree.items() if v["type"] in ("SF","AND")}
    else:
        parents = {k: v["label"] for k, v in tree.items() if v["type"]=="FF"}

    if parents:
        par_key  = st.selectbox("Parent", list(parents.keys()), format_func=lambda k: f"{parents[k]} ({tree[k]['type']})")
        lbl      = st.text_input("Label", value=f"{node_type}{st.session_state.next_id:02d}")
        desc     = st.text_input("Description", value=f"New {node_type}")
        gate     = "AND" if node_type == "AND" else "OR"
        if st.button("➕ Add Node", use_container_width=True):
            nid = f"N{st.session_state.next_id}"
            st.session_state.tree[nid] = {"id":nid,"label":lbl,"type":node_type,"parent":par_key,"gate":gate,"desc":desc}
            st.session_state.next_id += 1
            st.rerun()
    else:
        st.info(f"No valid parents for {node_type}")

    st.markdown("---")
    st.markdown("**🗑️ Delete Node**")
    deletable = {k: f"{v['label']} ({v['type']})" for k, v in tree.items() if v["type"] != "HZ"}
    if deletable:
        del_k = st.selectbox("Node to delete", list(deletable.keys()), format_func=lambda k: deletable[k])
        if st.button("🗑️ Delete", use_container_width=True):
            def descendants(tid):
                d = []
                for k, n in list(st.session_state.tree.items()):
                    if n["parent"] == tid:
                        d.append(k); d.extend(descendants(k))
                return d
            for d in [del_k] + descendants(del_k):
                st.session_state.tree.pop(d, None)
            st.rerun()

    st.markdown("---")
    if st.button("🔄 Reset to Default", use_container_width=True):
        for k in ["tree","hz_target","next_id"]: st.session_state.pop(k, None)
        st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────
tree  = st.session_state.tree
alloc = allocate_tree(tree, st.session_state.hz_target)
order = get_ordered(tree)
hz_id = next(k for k, v in tree.items() if v["type"]=="HZ")

n_sf = sum(1 for v in tree.values() if v["type"]=="SF")
n_ff = sum(1 for v in tree.values() if v["type"] in ("FF","AND"))
n_if = sum(1 for v in tree.values() if v["type"]=="IF")

st.markdown("""
<div class="fta-header">
  <h1>🌳 FTA Risk Allocator</h1>
  <p>Dynamic fault tree · Change hazard target or add/remove nodes → all values recalculate instantly</p>
</div>""", unsafe_allow_html=True)

# Metrics
c1,c2,c3,c4 = st.columns(4)
with c1: st.markdown(f'<div class="metric-card"><div class="mlabel">Hazard Target</div><div class="mvalue c-hz">{st.session_state.hz_target:.2E}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="metric-card"><div class="mlabel">System Failures</div><div class="mvalue c-sf">{n_sf}</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="metric-card"><div class="mlabel">Following Failures</div><div class="mvalue c-ff">{n_ff}</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="metric-card"><div class="mlabel">Initiating Failures</div><div class="mvalue c-if">{n_if}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Tree table ────────────────────────────────────────────────────────────────
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
    indent= lvl * 20

    rows += f"""<tr>
      <td style="padding-left:{indent+12}px"><span class="badge b-{t}">{t}</span></td>
      <td style="padding-left:{indent+12}px"><span class="vm c-{vc}">{node['label']}</span></td>
      <td style="color:#8b949e;font-size:0.8rem;max-width:260px">{node['desc']}</td>
      <td style="color:#8b949e;font-size:0.78rem;font-family:'IBM Plex Mono',monospace">{par}</td>
      <td><span class="{gc}">{node['gate']}</span></td>
      <td><span class="vm c-{vc}">{fmt(val)}</span></td>
    </tr>"""

st.markdown(f"""
<table class="tree-table">
<thead><tr>
  <th>Type</th><th>Node ID</th><th>Description</th>
  <th>Parent</th><th>Gate</th><th>Allocated Target (/yr)</th>
</tr></thead>
<tbody>{rows}</tbody>
</table>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Breakdown tabs ────────────────────────────────────────────────────────────
with st.expander("📊 Detailed Breakdown by Level", expanded=True):
    t1, t2, t3, t4 = st.tabs(["⚠️ Hazard","🔵 System Failures","🟢 Following Failures","🟣 Initiating Failures"])

    with t1:
        sf_budget = alloc.get(next((k for k,v in tree.items() if v["type"]=="SF"), hz_id), 0)
        st.markdown(f"""
| | |
|---|---|
| **Hazard ID** | `{tree[hz_id]['label']}` |
| **Description** | {tree[hz_id]['desc']} |
| **Target** | `{fmt(st.session_state.hz_target)}` /yr |
| **No. of SFs** | {n_sf} |
| **Budget per SF** | `{fmt(sf_budget)}` /yr |
| **Gate → SFs** | OR (divide equally) |
""")

    with t2:
        rows_sf = []
        for nid in order:
            n = tree[nid]
            if n["type"] != "SF": continue
            ch = get_children(tree, nid)
            rows_sf.append({
                "SF ID": n["label"], "Description": n["desc"],
                "# Children": len(ch),
                "Gate → Children": ch[0]["gate"] if ch else "–",
                "Allocated (/yr)": fmt(alloc.get(nid,0)),
                "Per Child (/yr)": fmt(alloc.get(ch[0]["id"],0)) if ch else "–"
            })
        st.dataframe(pd.DataFrame(rows_sf), use_container_width=True, hide_index=True)

    with t3:
        rows_ff = []
        for nid in order:
            n = tree[nid]
            if n["type"] not in ("FF","AND"): continue
            ch  = get_children(tree, nid)
            par = tree[n["parent"]]["label"] if n["parent"] else "–"
            rows_ff.append({
                "Node ID": n["label"], "Type": n["type"], "Parent": par,
                "Gate": n["gate"], "# IFs": len(ch),
                "Allocated (/yr)": fmt(alloc.get(nid,0)),
                "Per IF (/yr)": fmt(alloc.get(ch[0]["id"],0)) if ch else "–"
            })
        st.dataframe(pd.DataFrame(rows_ff), use_container_width=True, hide_index=True)

    with t4:
        rows_if = []
        for nid in order:
            n = tree[nid]
            if n["type"] != "IF": continue
            par = tree[n["parent"]]["label"] if n["parent"] else "–"
            sibs = len(get_children(tree, n["parent"])) if n["parent"] else 1
            rows_if.append({
                "IF ID": n["label"], "Description": n["desc"],
                "Parent FF": par, "# Siblings": sibs,
                "Allocated Target (/yr)": fmt(alloc.get(nid,0))
            })
        st.dataframe(pd.DataFrame(rows_if), use_container_width=True, hide_index=True)

# ── Allocation rules ──────────────────────────────────────────────────────────
with st.expander("📐 Allocation Rules", expanded=False):
    st.markdown("""
**OR Gate** – any child causes parent:
```
Child_target = Parent_target ÷ n_children
```
**AND Gate** – all children must fail simultaneously (Combined Faults):
```
Child_target = Parent_target ^ (1 / n_children)
```
**Auto-reallocation:**  Adding or removing any node instantly re-divides the parent's budget equally across all current siblings.
    """)

# ── Export ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📥 Export to Excel")

def build_excel(tree, alloc, order):
    wb = Workbook()
    ws = wb.active; ws.title = "FTA_Allocation"
    def fl(h): return PatternFill("solid",start_color=h,fgColor=h)
    def af(bold=False,color="000000",sz=10): return Font(name="Arial",bold=bold,color=color,size=sz)
    def tb():
        s=Side(style="thin",color="BFBFBF"); return Border(left=s,right=s,top=s,bottom=s)

    for i,w in enumerate([6,10,20,40,14,10,18,20],1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.merge_cells("A1:H1")
    ws["A1"]="FAULT TREE ANALYSIS – RISK ALLOCATION"
    ws["A1"].font=af(bold=True,sz=13,color="FFFFFF"); ws["A1"].fill=fl("1F3864")
    ws["A1"].alignment=Alignment(horizontal="center",vertical="center"); ws.row_dimensions[1].height=26

    ws.merge_cells("A2:H2")
    ws["A2"]=f"Hazard Target: {st.session_state.hz_target:.2E} /yr  |  OR gate=÷n  |  AND gate=^(1/n)"
    ws["A2"].font=af(sz=9,color="595959"); ws["A2"].fill=fl("F2F2F2"); ws.row_dimensions[2].height=14

    hdrs=["Lvl","Type","Node ID","Description","Parent","Gate","Allocated (/yr)","Method"]
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
        for c,v in enumerate([lvl,t,"  "*lvl+n["label"],n["desc"],par,n["gate"],val,method],1):
            cell=ws.cell(row=r,column=c,value=v); cell.border=tb()
            cell.alignment=Alignment(horizontal="left" if c in(3,4,8) else "center",vertical="center",wrap_text=(c==4))
            if c==2:
                cell.fill=fl(BG.get(t,"1F3864")); cell.font=af(bold=True,sz=9,color="FFFFFF")
                cell.alignment=Alignment(horizontal="center",vertical="center")
            elif c==7:
                cell.number_format="0.00E+00"; cell.font=af(bold=True,sz=10,color=BG.get(t,"000000"))
            else:
                cell.fill=fl(LT.get(t,"F2F2F2") if c in(3,6) else "FFFFFF"); cell.font=af(sz=9)
        ws.row_dimensions[r].height=16

    out=io.BytesIO(); wb.save(out); out.seek(0)
    return out.getvalue()

xl = build_excel(tree, alloc, order)
col_a, col_b = st.columns([1,3])
with col_a:
    st.download_button("⬇️ Download Excel", data=xl, file_name="FTA_Allocation.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True)
with col_b:
    st.caption("Exports the full tree with all allocated targets, gate types and calculation methods.")
