import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import math, io, json
from collections import defaultdict
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="FTA Risk Allocator v7", page_icon="🌳", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif}
.stApp{background:#0d1117;color:#e6edf3}
section[data-testid="stSidebar"]{background:#161b22 !important;border-right:1px solid #30363d}
section[data-testid="stSidebar"] *{color:#e6edf3 !important}
.fta-header{background:linear-gradient(135deg,#1a2332,#0d1117);border:1px solid #30363d;
  border-left:4px solid #f97316;border-radius:8px;padding:18px 24px;margin-bottom:16px}
.fta-header h1{font-family:'IBM Plex Mono',monospace;font-size:1.4rem;color:#f97316;margin:0 0 3px 0}
.fta-header p{color:#8b949e;margin:0;font-size:0.8rem}
.metric-card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 16px}
.metric-card .ml{font-size:0.65rem;color:#8b949e;text-transform:uppercase;letter-spacing:1px;margin-bottom:4px}
.metric-card .mv{font-family:'IBM Plex Mono',monospace;font-size:1.1rem;font-weight:700}
.hz-summary{border-radius:10px;padding:16px 22px;margin-bottom:10px;border:1px solid #30363d}
.hz-summary.pass{border-left:4px solid #3fb950;background:#0a1f0d}
.hz-summary.fail{border-left:4px solid #f85149;background:#1f0a0a}
.hz-summary.partial{border-left:4px solid #fbbf24;background:#1f1800}
.hz-summary h3{font-family:'IBM Plex Mono',monospace;font-size:1rem;margin:0 0 8px 0}
.hz-summary .row{display:flex;gap:28px;flex-wrap:wrap;margin-top:6px}
.hz-summary .stat .lbl{color:#8b949e;font-size:0.65rem;text-transform:uppercase;letter-spacing:1px}
.hz-summary .stat .val{font-family:'IBM Plex Mono',monospace;font-weight:700;font-size:0.88rem}
.pass-val{color:#3fb950}.fail-val{color:#f85149}.warn-val{color:#fbbf24}
.tree-table{width:100%;border-collapse:collapse;font-size:0.82rem}
.tree-table th{background:#1c2128;color:#8b949e;font-size:0.65rem;text-transform:uppercase;
  letter-spacing:1px;padding:9px 11px;text-align:left;border-bottom:1px solid #30363d}
.tree-table td{padding:7px 11px;border-bottom:1px solid #21262d;vertical-align:middle}
.tree-table tr:hover td{background:#1c2128}
.badge{display:inline-block;padding:2px 7px;border-radius:10px;font-size:0.68rem;
  font-weight:700;font-family:'IBM Plex Mono',monospace}
.b-HZ{background:#3d1a00;color:#f97316;border:1px solid #f97316}
.b-SF{background:#0d2136;color:#58a6ff;border:1px solid #58a6ff}
.b-FF{background:#0d2b14;color:#3fb950;border:1px solid #3fb950}
.b-IF{background:#1e0d36;color:#d2a8ff;border:1px solid #d2a8ff}
.b-AND{background:#2d1a3d;color:#e040fb;border:1px solid #e040fb}
.g-or{color:#58a6ff;font-weight:700;font-family:'IBM Plex Mono';font-size:0.75rem}
.g-and{color:#e040fb;font-weight:700;font-family:'IBM Plex Mono';font-size:0.75rem}
.vm{font-family:'IBM Plex Mono',monospace;font-size:0.8rem;font-weight:600}
.c-hz{color:#f97316}.c-sf{color:#58a6ff}.c-ff{color:#3fb950}.c-if{color:#d2a8ff}.c-and{color:#e040fb}
.lock-tag{display:inline-block;padding:1px 5px;border-radius:6px;font-size:0.6rem;
  font-weight:700;background:#1c2128;color:#fbbf24;border:1px solid #fbbf24;margin-left:3px}
.sync-tag{display:inline-block;padding:1px 5px;border-radius:6px;font-size:0.6rem;
  font-weight:700;background:#2d1e00;color:#fbbf24;border:1px solid #fbbf24;margin-left:3px}
.rebal-tag{display:inline-block;padding:1px 5px;border-radius:6px;font-size:0.6rem;
  font-weight:700;background:#0d2136;color:#58a6ff;border:1px solid #58a6ff;margin-left:3px}
div[data-testid="stExpander"]{background:#161b22;border:1px solid #30363d;border-radius:8px}
.stButton button{background:#1c2128 !important;border:1px solid #30363d !important;
  color:#e6edf3 !important;border-radius:6px !important}
.stButton button:hover{border-color:#58a6ff !important;color:#58a6ff !important}
.stTabs [data-baseweb="tab"]{color:#8b949e}
.stTabs [aria-selected="true"]{color:#f97316 !important;border-bottom-color:#f97316 !important}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════
VALID_PARENTS = {
    "SF":  ["HZ","SF","AND"],
    "FF":  ["SF","FF","AND"],
    "IF":  ["FF"],
    "AND": ["HZ","SF","FF"],
}
VC = {"HZ":"hz","SF":"sf","FF":"ff","IF":"if","AND":"and"}
HZ_PALETTE = ["#f97316","#58a6ff","#3fb950","#e040fb","#fbbf24","#06b6d4","#f43f5e","#a3e635"]

# ═══════════════════════════════════════════════════════════════
# DEFAULT STATE
# ═══════════════════════════════════════════════════════════════
def default_state():
    return {
        "nodes": {
            "HZ01":  {"id":"HZ01","label":"HZ01","name":"Pressurized Fluid Hazard","type":"HZ","parent":None,   "gate":"–",  "desc":"Hazard 1","achieved":None,"locked":False},
            "SF01":  {"id":"SF01","label":"SF01","name":"System Failure 01",       "type":"SF","parent":"HZ01", "gate":"OR", "desc":"SF","achieved":None,"locked":False},
            "SF02":  {"id":"SF02","label":"SF02","name":"System Failure 02",       "type":"SF","parent":"HZ01", "gate":"OR", "desc":"SF","achieved":None,"locked":False},
            "AND01": {"id":"AND01","label":"AND01","name":"Combined Faults A",     "type":"AND","parent":"SF02","gate":"AND","desc":"AND","achieved":None,"locked":False},
            "FF01":  {"id":"FF01","label":"FF01","name":"Following Failure 01",    "type":"FF","parent":"SF01", "gate":"OR", "desc":"FF","achieved":None,"locked":False},
            "FF02":  {"id":"FF02","label":"FF02","name":"Following Failure 02",    "type":"FF","parent":"SF01", "gate":"OR", "desc":"FF","achieved":None,"locked":False},
            "FF03":  {"id":"FF03","label":"FF03","name":"Following Failure 03",    "type":"FF","parent":"AND01","gate":"AND","desc":"FF","achieved":None,"locked":False},
            "FF04":  {"id":"FF04","label":"FF04","name":"Following Failure 04",    "type":"FF","parent":"AND01","gate":"AND","desc":"FF","achieved":None,"locked":False},
            "IF01":  {"id":"IF01","label":"IF01","name":"Initiating Failure 01",   "type":"IF","parent":"FF01", "gate":"OR", "desc":"IF","achieved":None,"locked":False},
            "IF02":  {"id":"IF02","label":"IF02","name":"Initiating Failure 02",   "type":"IF","parent":"FF01", "gate":"OR", "desc":"IF","achieved":None,"locked":False},
            "IF03":  {"id":"IF03","label":"IF03","name":"Initiating Failure 03",   "type":"IF","parent":"FF02", "gate":"OR", "desc":"IF","achieved":None,"locked":False},
            "IF04":  {"id":"IF04","label":"IF04","name":"Initiating Failure 04",   "type":"IF","parent":"FF03", "gate":"OR", "desc":"IF","achieved":None,"locked":False},
            "IF05":  {"id":"IF05","label":"IF05","name":"Initiating Failure 05",   "type":"IF","parent":"FF04", "gate":"OR", "desc":"IF","achieved":None,"locked":False},
            "HZ02":  {"id":"HZ02","label":"HZ02","name":"Thermal Runaway Hazard",  "type":"HZ","parent":None,   "gate":"–",  "desc":"Hazard 2","achieved":None,"locked":False},
            "SF03":  {"id":"SF03","label":"SF03","name":"System Failure 03",       "type":"SF","parent":"HZ02", "gate":"OR", "desc":"SF","achieved":None,"locked":False},
            "SF04":  {"id":"SF04","label":"SF04","name":"System Failure 04",       "type":"SF","parent":"HZ02", "gate":"OR", "desc":"SF","achieved":None,"locked":False},
            "FF05":  {"id":"FF05","label":"FF05","name":"Following Failure 05",    "type":"FF","parent":"SF03", "gate":"OR", "desc":"FF","achieved":None,"locked":False},
            "FF06":  {"id":"FF06","label":"FF02","name":"Following Failure 02 (HZ02 dup)","type":"FF","parent":"SF04","gate":"OR","desc":"Duplicate of FF02","achieved":None,"locked":False},
            "IF06":  {"id":"IF06","label":"IF06","name":"Initiating Failure 06",   "type":"IF","parent":"FF05", "gate":"OR", "desc":"IF","achieved":None,"locked":False},
            "IF07":  {"id":"IF07","label":"IF07","name":"Initiating Failure 07",   "type":"IF","parent":"FF05", "gate":"OR", "desc":"IF","achieved":None,"locked":False},
            "IF08":  {"id":"IF08","label":"IF03","name":"Initiating Failure 03 (HZ02 dup)","type":"IF","parent":"FF06","gate":"OR","desc":"Dup of IF03","achieved":None,"locked":False},
        },
        "hz_targets": {"HZ01": 1e-8, "HZ02": 1e-7},
        "next_id": 200,
        # alloc is the live budget table — starts from top-down but gets adjusted by rebalancing
        "alloc_override": {},   # nid -> overridden alloc value from rebalancing
        "rebalanced_nodes": set(),  # nodes whose alloc was adjusted by rebalancing
    }

for k, v in default_state().items():
    if k not in st.session_state:
        st.session_state[k] = v
# Ensure set types survive rerun
if not isinstance(st.session_state.get("rebalanced_nodes"), set):
    st.session_state["rebalanced_nodes"] = set()

# ═══════════════════════════════════════════════════════════════
# CORE HELPERS
# ═══════════════════════════════════════════════════════════════
def get_children(nodes, pid):
    return [n for n in nodes.values() if n.get("parent") == pid]

def get_hz_roots(nodes):
    return [n for n in nodes.values() if n["type"] == "HZ"]

def bfs_order(nodes):
    roots = [n["id"] for n in get_hz_roots(nodes)]
    visited, order, queue = set(), [], list(roots)
    while queue:
        nid = queue.pop(0)
        if nid in visited: continue
        visited.add(nid); order.append(nid)
        queue.extend(c["id"] for c in get_children(nodes, nid))
    return order

def get_depth(nodes, nid):
    depth, cur, seen = 0, nid, set()
    while nodes.get(cur, {}).get("parent"):
        cur = nodes[cur]["parent"]
        if cur in seen: break
        seen.add(cur); depth += 1
    return depth

def get_hz_ancestor(nodes, nid):
    cur, seen = nid, set()
    while cur:
        if cur in seen: break
        seen.add(cur)
        nd = nodes.get(cur)
        if not nd: break
        if nd["type"] == "HZ": return cur
        cur = nd.get("parent")
    return None

def descendants(nodes, nid):
    d = []
    for k, n in nodes.items():
        if n.get("parent") == nid:
            d.append(k); d.extend(descendants(nodes, k))
    return d

def fmt(v):
    if v is None: return "–"
    if v == 0:    return "0.000E+00"
    return f"{v:.3E}"

# ═══════════════════════════════════════════════════════════════
# TOP-DOWN BASE ALLOCATION  (initial, before any rebalancing)
# ═══════════════════════════════════════════════════════════════
def base_allocate(nodes, hz_targets):
    alloc = {}
    def recurse(nid, budget):
        alloc[nid] = budget
        children = get_children(nodes, nid)
        if not children: return
        n = len(children)
        for child in children:
            cb = budget ** (1.0/n) if child["gate"] == "AND" else budget / n
            recurse(child["id"], cb)
    for hz in get_hz_roots(nodes):
        recurse(hz["id"], hz_targets.get(hz["id"], 1e-8))
    return alloc

# ═══════════════════════════════════════════════════════════════
# REBALANCING ENGINE
# ═══════════════════════════════════════════════════════════════
def rebalance(nodes, alloc, changed_nid, changed_value, rebalanced_set):
    """
    When a node's achieved value is set:
      1. Parent alloc stays FIXED (sacred)
      2. Remaining budget = parent_alloc - sum_of_locked_siblings_achieved - changed_value
         (for OR gate)  OR  remaining = (parent_alloc / changed_value) ^ sibling_count
         (for AND gate, each unlocked sibling gets parent_alloc ^ (1/n) which is already set)
      3. Remaining budget is split among UNLOCKED siblings using gate logic
      4. Each adjusted sibling cascades its new alloc down to its own children
      5. Marks all touched alloc entries in rebalanced_set

    Returns updated alloc dict.
    """
    alloc = dict(alloc)  # copy

    node = nodes.get(changed_nid)
    if not node: return alloc
    parent_id = node.get("parent")
    if not parent_id or parent_id not in nodes: return alloc

    parent   = nodes[parent_id]
    parent_budget = alloc.get(parent_id)
    if parent_budget is None: return alloc

    all_siblings = get_children(nodes, parent_id)  # includes changed node
    gate = node.get("gate", "OR")  # gate type of changed node (same for all siblings)

    # Separate: locked siblings (their achieved is fixed), the changed node, free siblings
    locked_siblings = [
        s for s in all_siblings
        if s["id"] != changed_nid and nodes[s["id"]].get("locked", False)
    ]
    free_siblings = [
        s for s in all_siblings
        if s["id"] != changed_nid and not nodes[s["id"]].get("locked", False)
    ]

    locked_sum = sum(
        nodes[s["id"]].get("achieved") or alloc.get(s["id"], 0)
        for s in locked_siblings
    )

    if gate == "OR":
        # parent = changed + locked_siblings + free_siblings  (sum)
        remaining = parent_budget - changed_value - locked_sum
        n_free = len(free_siblings)
        if n_free == 0:
            # nowhere to rebalance, just flag
            pass
        elif remaining <= 0:
            # Infeasible — clamp free siblings to 0, mark non-compliant
            for s in free_siblings:
                alloc[s["id"]] = 0.0
                rebalanced_set.add(s["id"])
                _cascade_alloc_down(nodes, alloc, s["id"], 0.0, rebalanced_set)
        else:
            # Split remaining equally among free siblings
            share = remaining / n_free
            for s in free_siblings:
                alloc[s["id"]] = share
                rebalanced_set.add(s["id"])
                _cascade_alloc_down(nodes, alloc, s["id"], share, rebalanced_set)

    elif gate == "AND":
        # parent = product(all children)  →  each child = parent^(1/n)
        # If changed node is fixed, recompute each free sibling so product still = parent
        # product = changed_value * prod(locked) * prod(free)
        # free siblings all get same value x  →  x^n_free = parent / (changed * prod_locked)
        n_all = len(all_siblings)
        prod_locked = 1.0
        for s in locked_siblings:
            v = nodes[s["id"]].get("achieved") or alloc.get(s["id"], 1e-8)
            prod_locked *= v

        n_free = len(free_siblings)
        if n_free == 0:
            pass
        else:
            # x^n_free = parent_budget / (changed_value * prod_locked)
            numerator = parent_budget / (changed_value * prod_locked) if (changed_value * prod_locked) > 0 else 0
            if numerator <= 0:
                for s in free_siblings:
                    alloc[s["id"]] = 0.0
                    rebalanced_set.add(s["id"])
                    _cascade_alloc_down(nodes, alloc, s["id"], 0.0, rebalanced_set)
            else:
                x = numerator ** (1.0 / n_free)
                for s in free_siblings:
                    alloc[s["id"]] = x
                    rebalanced_set.add(s["id"])
                    _cascade_alloc_down(nodes, alloc, s["id"], x, rebalanced_set)

    # Also update the changed node's own alloc to its achieved value
    alloc[changed_nid] = changed_value
    # Cascade changed node's own children down with its new budget
    _cascade_alloc_down(nodes, alloc, changed_nid, changed_value, rebalanced_set)

    return alloc


def _cascade_alloc_down(nodes, alloc, nid, budget, rebalanced_set):
    """
    Given that nid now has budget `budget`, redistribute this budget
    to all its children using gate logic. Recurse downward.
    Only adjusts children that are NOT locked.
    """
    alloc[nid] = budget
    children = get_children(nodes, nid)
    if not children: return

    # Separate locked vs free children
    locked_ch = [c for c in children if nodes[c["id"]].get("locked", False)]
    free_ch   = [c for c in children if not nodes[c["id"]].get("locked", False)]

    gate = children[0].get("gate", "OR")  # gate is on child, all siblings share

    # Compute locked contribution
    locked_sum  = sum(nodes[c["id"]].get("achieved") or alloc.get(c["id"], 0) for c in locked_ch)
    locked_prod = 1.0
    for c in locked_ch:
        v = nodes[c["id"]].get("achieved") or alloc.get(c["id"], 1e-8)
        locked_prod *= v

    n_free = len(free_ch)
    if n_free == 0: return

    if gate == "OR":
        remaining = max(0.0, budget - locked_sum)
        share = remaining / n_free
        for c in free_ch:
            alloc[c["id"]] = share
            rebalanced_set.add(c["id"])
            _cascade_alloc_down(nodes, alloc, c["id"], share, rebalanced_set)

    elif gate == "AND":
        n_all = len(children)
        if locked_prod > 0 and budget > 0:
            x = (budget / locked_prod) ** (1.0 / n_free)
        else:
            x = budget ** (1.0 / n_all)
        for c in free_ch:
            alloc[c["id"]] = x
            rebalanced_set.add(c["id"])
            _cascade_alloc_down(nodes, alloc, c["id"], x, rebalanced_set)


def compute_alloc(nodes, hz_targets):
    """
    Build the live allocation table:
      - Start from base top-down allocation
      - Apply any rebalancing overrides stored in session state
    Returns alloc dict and rebalanced_set.
    """
    alloc = base_allocate(nodes, hz_targets)
    # Apply stored overrides
    overrides = st.session_state.get("alloc_override", {})
    for nid, val in overrides.items():
        if nid in nodes:
            alloc[nid] = val
    rebalanced = st.session_state.get("rebalanced_nodes", set())
    return alloc, rebalanced

# ═══════════════════════════════════════════════════════════════
# LABEL-BASED WORST-CASE SYNC
# ═══════════════════════════════════════════════════════════════
def sync_worst_case(nodes):
    label_groups = defaultdict(list)
    for nid, n in nodes.items():
        label_groups[n.get("label","")].append(nid)
    synced = {}
    for lbl, ids in label_groups.items():
        if len(ids) < 2: continue
        vals = [nodes[i]["achieved"] for i in ids if nodes[i].get("achieved") is not None]
        if not vals: continue
        worst = max(vals)
        synced[lbl] = worst
        for i in ids:
            nodes[i]["achieved"] = worst
    return synced

# ═══════════════════════════════════════════════════════════════
# BOTTOM-UP ROLLUP
# ═══════════════════════════════════════════════════════════════
def rollup_achieved(nodes):
    rolled = {}
    def compute(nid):
        if nid in rolled: return rolled[nid]
        children = get_children(nodes, nid)
        node = nodes.get(nid)
        if not node: rolled[nid]=None; return None
        if not children:
            rolled[nid] = node.get("achieved"); return rolled[nid]
        child_vals = [compute(c["id"]) for c in children]
        if any(v is None for v in child_vals):
            rolled[nid] = node.get("achieved"); return rolled[nid]
        gate = node.get("gate","OR")
        if gate == "AND":
            val = 1.0
            for v in child_vals: val *= v
        else:
            val = sum(child_vals)
        manual = node.get("achieved")
        rolled[nid] = manual if manual is not None else val
        return rolled[nid]
    for hz in get_hz_roots(nodes):
        compute(hz["id"])
    for nid in nodes:
        if nid not in rolled: compute(nid)
    return rolled

# ═══════════════════════════════════════════════════════════════
# COMPLIANCE
# ═══════════════════════════════════════════════════════════════
def node_status(achieved, allocated):
    if achieved is None or allocated is None: return "na"
    return "pass" if achieved <= allocated else "fail"

def hz_compliance(nodes, hz_targets, rolled, alloc):
    results = {}
    for hz in get_hz_roots(nodes):
        hid = hz["id"]
        tgt = hz_targets.get(hid, 1e-8)
        ach = rolled.get(hid)
        all_ids  = descendants(nodes, hid)
        if_ids   = [i for i in all_ids if nodes.get(i,{}).get("type")=="IF"]
        if_done  = [i for i in if_ids if nodes.get(i,{}).get("achieved") is not None]
        results[hid] = {
            "target":     tgt,
            "achieved":   ach,
            "status":     node_status(ach, tgt),
            "if_total":   len(if_ids),
            "if_entered": len(if_done),
            "margin":     ach/tgt if (ach is not None and tgt) else None,
        }
    return results

# ═══════════════════════════════════════════════════════════════
# VISUALIZATION
# ═══════════════════════════════════════════════════════════════
def build_viz(nodes, alloc, rolled, hz_targets, rebalanced_set):
    order = bfs_order(nodes)
    hz_ids = [n["id"] for n in get_hz_roots(nodes)]
    hz_color_map = {hid: HZ_PALETTE[i % len(HZ_PALETTE)] for i, hid in enumerate(hz_ids)}

    node_data = []
    for nid in order:
        if nid not in nodes: continue
        n = nodes[nid]
        hz_anc   = get_hz_ancestor(nodes, nid)
        hz_color = hz_color_map.get(hz_anc, "#58a6ff") if hz_anc else "#58a6ff"
        depth    = get_depth(nodes, nid)
        ach      = rolled.get(nid)
        alc      = alloc.get(nid)
        stat     = node_status(ach, alc)
        is_rebal = nid in rebalanced_set
        is_locked= n.get("locked", False)
        node_data.append({
            "id": nid, "label": n.get("label",nid), "name": n.get("name",""),
            "desc": n.get("desc",""), "type": n["type"], "gate": n["gate"],
            "alloc": fmt(alc), "achieved": fmt(ach), "status": stat,
            "rebalanced": is_rebal, "locked": is_locked,
            "hz": hz_anc or "", "hz_color": hz_color,
            "depth": depth, "parent": n.get("parent") or "",
        })

    edge_data = [
        {"from": n.get("parent"), "to": nid, "gate": n["gate"]}
        for nid, n in nodes.items() if n.get("parent") and n["parent"] in nodes
    ]
    hz_list    = [{"id":h,"color":hz_color_map[h],"target":fmt(hz_targets.get(h,1e-8))} for h in hz_ids]
    nodes_json = json.dumps(node_data)
    edges_json = json.dumps(edge_data)
    hz_json    = json.dumps(hz_list)

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;font-family:'IBM Plex Sans',sans-serif;overflow:hidden;user-select:none}}
#wrap{{position:relative;width:100%;height:700px;overflow:hidden}}
canvas{{position:absolute;top:0;left:0;cursor:grab}}
canvas.grabbing{{cursor:grabbing}}
#ctrl{{position:absolute;top:12px;left:12px;display:flex;flex-direction:column;gap:5px;z-index:20}}
.btn{{background:#161b22;border:1px solid #30363d;color:#e6edf3;padding:5px 11px;border-radius:6px;
  cursor:pointer;font-size:11px;font-family:inherit;transition:all .15s}}
.btn:hover{{border-color:#58a6ff;color:#58a6ff}}
.btn.active{{border-color:#f97316;color:#f97316}}
#hzf{{position:absolute;top:12px;right:12px;background:#161b22;border:1px solid #30363d;
  border-radius:8px;padding:10px 14px;z-index:20;min-width:185px}}
#hzf .title{{color:#8b949e;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}}
.hchip{{display:flex;align-items:center;gap:7px;cursor:pointer;padding:3px 0;font-size:11px;
  color:#e6edf3;transition:opacity .15s}}
.hchip.off{{opacity:0.3}}
.hdot{{width:10px;height:10px;border-radius:50%;flex-shrink:0}}
#legend{{position:absolute;bottom:48px;left:12px;background:#161b22;border:1px solid #30363d;
  border-radius:6px;padding:8px 12px;font-size:10px;color:#8b949e;z-index:20;display:flex;gap:12px;flex-wrap:wrap}}
.leg{{display:flex;align-items:center;gap:5px}}
.leg-dot{{width:9px;height:9px;border-radius:50%}}
#info{{position:absolute;bottom:10px;left:12px;background:#161b22;border:1px solid #30363d;
  border-radius:6px;padding:5px 12px;font-size:10px;color:#8b949e;z-index:20}}
#popup{{position:absolute;background:#1c2128;border:1px solid #30363d;border-radius:10px;
  padding:14px 18px;min-width:260px;max-width:300px;z-index:30;display:none;
  box-shadow:0 12px 40px rgba(0,0,0,0.7);pointer-events:none}}
#popup h3{{font-family:'IBM Plex Mono',monospace;font-size:13px;margin:0 0 2px 0}}
#popup .psub{{font-size:10px;color:#8b949e;margin-bottom:10px}}
#popup .prow{{display:flex;justify-content:space-between;gap:12px;padding:3px 0;border-bottom:1px solid #21262d}}
#popup .prow:last-of-type{{border:none}}
#popup .pk{{color:#8b949e;font-size:10px}}
#popup .pv{{color:#e6edf3;font-size:10px;font-family:'IBM Plex Mono',monospace;text-align:right}}
#popup .pv.pass{{color:#3fb950}} #popup .pv.fail{{color:#f85149}}
#popup .hint{{margin-top:8px;font-size:9px;color:#444;text-align:center}}
#mm{{position:absolute;bottom:10px;right:12px;width:170px;height:95px;background:#161b22;
  border:1px solid #30363d;border-radius:6px;z-index:20;overflow:hidden}}
</style></head><body>
<div id="wrap">
  <canvas id="c"></canvas>
  <div id="ctrl">
    <button class="btn active" id="btnSim" onclick="toggleSim()">⟳ Force ON</button>
    <button class="btn" onclick="zoomIn()">＋ Zoom</button>
    <button class="btn" onclick="zoomOut()">－ Zoom</button>
    <button class="btn" onclick="resetView()">⌖ Reset</button>
    <button class="btn" onclick="clearHL()">✕ Clear</button>
    <button class="btn" id="btnCA" onclick="toggleCA()">▶ Collapse All</button>
  </div>
  <div id="hzf"><div class="title">Filter Hazard</div><div id="hzchips"></div></div>
  <div id="legend">
    <div class="leg"><div class="leg-dot" style="background:#3fb950"></div>Pass</div>
    <div class="leg"><div class="leg-dot" style="background:#f85149"></div>Exceeds</div>
    <div class="leg"><div class="leg-dot" style="background:#444"></div>No data</div>
    <div class="leg"><div class="leg-dot" style="background:#fbbf24;border-radius:2px"></div>Rebalanced</div>
    <div class="leg"><div class="leg-dot" style="background:#fbbf24;border:1px solid #fbbf24;background:transparent;border-radius:50%"></div>Locked</div>
  </div>
  <div id="popup">
    <h3 id="p-lbl"></h3><div class="psub" id="p-type"></div>
    <div class="prow"><span class="pk">Name</span><span class="pv" id="p-name"></span></div>
    <div class="prow"><span class="pk">Gate</span><span class="pv" id="p-gate"></span></div>
    <div class="prow"><span class="pk">Allocated (live)</span><span class="pv" id="p-alloc"></span></div>
    <div class="prow"><span class="pk">Achieved (rolled)</span><span class="pv" id="p-ach"></span></div>
    <div class="prow"><span class="pk">Margin</span><span class="pv" id="p-margin"></span></div>
    <div class="prow"><span class="pk">Status</span><span class="pv" id="p-status"></span></div>
    <div class="prow"><span class="pk">Rebalanced</span><span class="pv" id="p-rebal"></span></div>
    <div class="prow"><span class="pk">Locked</span><span class="pv" id="p-locked"></span></div>
    <div class="prow"><span class="pk">Hazard</span><span class="pv" id="p-hz"></span></div>
    <div class="hint">Click to highlight path · Click elsewhere to close</div>
  </div>
  <div id="info">🖱 Drag nodes · Scroll=zoom · Drag=pan · Click=details · ▼=collapse · 🔒=locked · 🔵=rebalanced</div>
  <div id="mm"><canvas id="mmc" width="170" height="95"></canvas></div>
</div>
<script>
const NODES={nodes_json};
const EDGES={edges_json};
const HZ={hz_json};
const BOX_W=154,BOX_H=66,GATE_R=12;
const TYPE_COL={{
  HZ:{{fill:"#3d1a00",stroke:"#f97316",text:"#f97316"}},
  SF:{{fill:"#0d2136",stroke:"#58a6ff",text:"#58a6ff"}},
  FF:{{fill:"#0d2b14",stroke:"#3fb950",text:"#3fb950"}},
  IF:{{fill:"#1e0d36",stroke:"#d2a8ff",text:"#d2a8ff"}},
  AND:{{fill:"#2d1a3d",stroke:"#e040fb",text:"#e040fb"}},
}};
const STATUS_COL={{pass:"#3fb950",fail:"#f85149",na:"#333"}};
const wrap=document.getElementById('wrap');
const c=document.getElementById('c'),ctx=c.getContext('2d');
const mmc=document.getElementById('mmc'),mmx=mmc.getContext('2d');
function resize(){{c.width=wrap.clientWidth;c.height=wrap.clientHeight;}}
resize();window.addEventListener('resize',()=>{{resize();draw();}});
let scale=1,panX=wrap.clientWidth/2,panY=50;
let dragging=null,dragOffX=0,dragOffY=0,dragMoved=false;
let isPan=false,lastMX=0,lastMY=0;
let hlSet=new Set(),collapsed=new Set(),activeHz=new Set(HZ.map(h=>h.id));
let simRunning=true,allCA=false,popup=null;
const pos={{}};
const hzIds=HZ.map(h=>h.id);
NODES.forEach(n=>{{
  const hi=hzIds.indexOf(n.hz);
  const hzX=(hi>=0?hi:0)*740-(hzIds.length-1)*370;
  pos[n.id]={{x:hzX+(Math.random()-.5)*110,y:n.depth*140+75+(Math.random()-.5)*28,vx:0,vy:0}};
}});
function simulate(){{
  if(!simRunning)return;
  const ids=Object.keys(pos);
  for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){{
    const a=pos[ids[i]],b=pos[ids[j]];
    const dx=b.x-a.x,dy=b.y-a.y,dist=Math.sqrt(dx*dx+dy*dy)||1;
    const f=3900/(dist*dist),fx=dx/dist*f,fy=dy/dist*f;
    a.vx-=fx;a.vy-=fy;b.vx+=fx;b.vy+=fy;
  }}
  EDGES.forEach(e=>{{
    const a=pos[e.from],b=pos[e.to];if(!a||!b)return;
    const dx=b.x-a.x,dy=b.y-a.y,dist=Math.sqrt(dx*dx+dy*dy)||1;
    const f=(dist-148)*0.04,fx=dx/dist*f,fy=dy/dist*f;
    a.vx+=fx;a.vy+=fy;b.vx-=fx;b.vy-=fy;
  }});
  ids.forEach(id=>{{
    const n=NODES.find(x=>x.id===id);if(!n)return;
    pos[id].vy+=n.depth*0.017;pos[id].vx*=0.74;pos[id].vy*=0.74;
    if(id!==dragging){{pos[id].x+=pos[id].vx;pos[id].y+=pos[id].vy;}}
  }});
}}
function isVisible(nid){{
  const n=NODES.find(x=>x.id===nid);if(!n)return false;
  if(n.type==='HZ')return activeHz.has(n.id);
  if(!activeHz.has(n.hz))return false;
  let cur=n.parent;const seen=new Set();
  while(cur&&!seen.has(cur)){{seen.add(cur);if(collapsed.has(cur))return false;const p=NODES.find(x=>x.id===cur);if(!p)break;cur=p.parent;}}
  return true;
}}
function draw(){{
  ctx.clearRect(0,0,c.width,c.height);ctx.save();ctx.translate(panX,panY);ctx.scale(scale,scale);
  EDGES.forEach(e=>{{if(!isVisible(e.from)||!isVisible(e.to))return;drawEdge(pos[e.from],pos[e.to],e.gate,hlSet.size>0&&(!hlSet.has(e.from)||!hlSet.has(e.to)));}} );
  NODES.forEach(n=>{{if(!isVisible(n.id))return;drawNode(n,pos[n.id],hlSet.size>0&&!hlSet.has(n.id),popup===n.id);}});
  ctx.restore();drawMinimap();
}}
function rr(ctx,x,y,w,h,r){{ctx.beginPath();ctx.moveTo(x+r,y);ctx.lineTo(x+w-r,y);ctx.arcTo(x+w,y,x+w,y+r,r);ctx.lineTo(x+w,y+h-r);ctx.arcTo(x+w,y+h,x+w-r,y+h,r);ctx.lineTo(x+r,y+h);ctx.arcTo(x,y+h,x,y+h-r,r);ctx.lineTo(x,y+r);ctx.arcTo(x,y,x+r,y,r);ctx.closePath();}}
function drawEdge(a,b,gate,faded){{
  if(!a||!b)return;
  const gc=gate==='AND'?'#e040fb':'#58a6ff';
  ctx.save();ctx.globalAlpha=faded?0.06:0.9;
  ctx.beginPath();ctx.moveTo(a.x,a.y+BOX_H/2);ctx.bezierCurveTo(a.x,a.y+BOX_H/2+38,b.x,b.y-BOX_H/2-38,b.x,b.y-BOX_H/2-6);
  ctx.strokeStyle=faded?'#2d333b':gc;ctx.lineWidth=faded?1:1.5;ctx.stroke();
  if(!faded){{
    const ex=b.x,ey=b.y-BOX_H/2-2;const ang=Math.atan2(ey-(b.y-BOX_H/2-40),ex-b.x);
    ctx.beginPath();ctx.moveTo(ex,ey);ctx.lineTo(ex-9*Math.cos(ang-.4),ey-9*Math.sin(ang-.4));ctx.lineTo(ex-9*Math.cos(ang+.4),ey-9*Math.sin(ang+.4));ctx.closePath();ctx.fillStyle=gc;ctx.fill();
    const gx=(a.x+b.x)/2,gy=(a.y+BOX_H/2+b.y-BOX_H/2)/2;
    if(gate==='AND'){{ctx.fillStyle='#2d1a3d';ctx.strokeStyle='#e040fb';ctx.lineWidth=1.5;rr(ctx,gx-GATE_R,gy-GATE_R,GATE_R*2,GATE_R*2,5);ctx.fill();ctx.stroke();ctx.fillStyle='#e040fb';ctx.font='bold 7px monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('AND',gx,gy);}}
    else{{ctx.fillStyle='#0d2136';ctx.strokeStyle='#58a6ff';ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(gx,gy,GATE_R,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle='#58a6ff';ctx.font='bold 7px monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('OR',gx,gy);}}
  }}
  ctx.restore();
}}
function drawNode(n,p,faded,isHL){{
  const col=TYPE_COL[n.type]||TYPE_COL.SF;
  const scol=STATUS_COL[n.status]||'#333';
  const x=p.x-BOX_W/2,y=p.y-BOX_H/2;
  const hasKids=EDGES.some(e=>e.from===n.id);
  const isColl=collapsed.has(n.id);
  ctx.save();ctx.globalAlpha=faded?0.08:1;
  if(n.status!=='na'&&!faded){{ctx.shadowColor=scol;ctx.shadowBlur=isHL?18:7;}}
  // Rebalanced outline (dashed blue outer ring)
  if(n.rebalanced&&!faded){{
    ctx.save();ctx.strokeStyle='#58a6ff';ctx.lineWidth=2;ctx.setLineDash([4,3]);
    rr(ctx,x-3,y-3,BOX_W+6,BOX_H+6,11);ctx.stroke();ctx.setLineDash([]);ctx.restore();
  }}
  ctx.fillStyle='rgba(0,0,0,0.45)';rr(ctx,x+3,y+3,BOX_W,BOX_H,9);ctx.fill();
  ctx.fillStyle=col.fill;rr(ctx,x,y,BOX_W,BOX_H,9);ctx.fill();
  ctx.strokeStyle=n.status!=='na'?scol:col.stroke;ctx.lineWidth=isHL?2.8:(n.status!=='na'?2:1.8);
  ctx.shadowBlur=0;rr(ctx,x,y,BOX_W,BOX_H,9);ctx.stroke();
  ctx.fillStyle=col.stroke;ctx.globalAlpha=(faded?0.08:1)*0.18;rr(ctx,x,y,BOX_W,18,9);ctx.fill();ctx.fillRect(x,y+9,BOX_W,9);
  ctx.globalAlpha=faded?0.08:1;
  // Type
  ctx.fillStyle=col.text;ctx.font='bold 7.5px monospace';ctx.textAlign='center';ctx.textBaseline='top';ctx.fillText(n.type,p.x,y+4);
  // Lock icon
  if(n.locked){{ctx.font='10px monospace';ctx.fillStyle='#fbbf24';ctx.textAlign='left';ctx.fillText('🔒',x+4,y+3);}}
  // Label
  ctx.fillStyle=col.text;ctx.font='bold 12px monospace';ctx.textBaseline='middle';ctx.fillText(n.label.substring(0,16),p.x,p.y-9);
  // Name
  ctx.fillStyle=col.text;ctx.font='7.5px sans-serif';ctx.globalAlpha=(faded?0.08:1)*0.68;ctx.fillText(n.name.substring(0,22),p.x,p.y+5);
  ctx.globalAlpha=faded?0.08:1;
  // Bottom row: A (achieved) | T (allocated)
  const achStr=n.achieved!=='–'?'A:'+n.achieved:'A:–';
  const alcStr='T:'+n.alloc;
  ctx.font='6.8px monospace';
  ctx.fillStyle=n.status==='pass'?'#3fb950':n.status==='fail'?'#f85149':'#555';
  ctx.textAlign='left';ctx.fillText(achStr,x+6,y+BOX_H-8);
  ctx.fillStyle=n.rebalanced?'#58a6ff':'#555';ctx.textAlign='right';ctx.fillText(alcStr,x+BOX_W-6,y+BOX_H-8);
  // Collapse btn
  if(hasKids){{
    const bx=p.x-BOX_W/2+BOX_W-15,by=y+3,br=7;
    ctx.fillStyle=isColl?col.stroke:'#21262d';ctx.beginPath();ctx.arc(bx,by+br,br,0,Math.PI*2);ctx.fill();
    ctx.strokeStyle=col.stroke;ctx.lineWidth=1;ctx.stroke();
    ctx.fillStyle=isColl?'#0d1117':col.text;ctx.font='bold 9px monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(isColl?'▶':'▼',bx,by+br);
  }}
  ctx.restore();
}}
function drawMinimap(){{
  mmx.clearRect(0,0,170,95);mmx.fillStyle='#161b22';mmx.fillRect(0,0,170,95);
  const vis=NODES.filter(n=>isVisible(n.id));if(!vis.length)return;
  const allX=vis.map(n=>pos[n.id]?.x||0),allY=vis.map(n=>pos[n.id]?.y||0);
  const minX=Math.min(...allX)-80,maxX=Math.max(...allX)+80,minY=Math.min(...allY)-40,maxY=Math.max(...allY)+40;
  const s=Math.min(160/Math.max(maxX-minX,1),85/Math.max(maxY-minY,1))*0.85;
  vis.forEach(n=>{{
    const p=pos[n.id];const sc=STATUS_COL[n.status]||'#333';
    mmx.fillStyle=sc;mmx.globalAlpha=0.8;mmx.fillRect((p.x-minX)*s+3-4,(p.y-minY)*s+3-2,10,6);
  }});
  mmx.globalAlpha=1;mmx.strokeStyle='#f97316';mmx.lineWidth=1.5;
  mmx.strokeRect((-panX/scale-minX)*s+3,(-panY/scale-minY)*s+3,Math.min((c.width/scale)*s,160),Math.min((c.height/scale)*s,88));
}}
function toWorld(cx,cy){{return{{x:(cx-panX)/scale,y:(cy-panY)/scale}};}}
function nodeAt(wx,wy){{for(let i=NODES.length-1;i>=0;i--){{const n=NODES[i];if(!isVisible(n.id))continue;const p=pos[n.id];if(wx>=p.x-BOX_W/2&&wx<=p.x+BOX_W/2&&wy>=p.y-BOX_H/2&&wy<=p.y+BOX_H/2)return n;}}return null;}}
function collapseHit(n,wx,wy){{const bx=pos[n.id].x-BOX_W/2+BOX_W-15,by=pos[n.id].y-BOX_H/2+10;return Math.sqrt((wx-bx)**2+(wy-by)**2)<9;}}
c.addEventListener('mousedown',ev=>{{
  const rect=c.getBoundingClientRect();const cx=ev.clientX-rect.left,cy=ev.clientY-rect.top;const{{x:wx,y:wy}}=toWorld(cx,cy);
  const n=nodeAt(wx,wy);
  if(n){{if(EDGES.some(e=>e.from===n.id)&&collapseHit(n,wx,wy)){{collapsed.has(n.id)?collapsed.delete(n.id):collapsed.add(n.id);ev.preventDefault();return;}}
    dragging=n.id;dragMoved=false;dragOffX=wx-pos[n.id].x;dragOffY=wy-pos[n.id].y;c.classList.add('grabbing');
  }}else{{isPan=true;lastMX=cx;lastMY=cy;c.classList.add('grabbing');popup=null;document.getElementById('popup').style.display='none';}}
  ev.preventDefault();
}});
window.addEventListener('mousemove',ev=>{{
  const rect=c.getBoundingClientRect();const cx=ev.clientX-rect.left,cy=ev.clientY-rect.top;const{{x:wx,y:wy}}=toWorld(cx,cy);
  if(dragging){{const dx=wx-dragOffX-pos[dragging].x,dy=wy-dragOffY-pos[dragging].y;if(Math.abs(dx)>2||Math.abs(dy)>2)dragMoved=true;pos[dragging].x=wx-dragOffX;pos[dragging].y=wy-dragOffY;pos[dragging].vx=0;pos[dragging].vy=0;}}
  else if(isPan){{panX+=cx-lastMX;panY+=cy-lastMY;lastMX=cx;lastMY=cy;}}
}});
window.addEventListener('mouseup',ev=>{{
  if(dragging&&!dragMoved){{const rect=c.getBoundingClientRect();const{{x:wx,y:wy}}=toWorld(ev.clientX-rect.left,ev.clientY-rect.top);const n=nodeAt(wx,wy);if(n&&n.id===dragging)handleClick(n,ev.clientX-rect.left,ev.clientY-rect.top);}}
  dragging=null;isPan=false;dragMoved=false;c.classList.remove('grabbing');
}});
c.addEventListener('wheel',ev=>{{ev.preventDefault();const rect=c.getBoundingClientRect();const cx=ev.clientX-rect.left,cy=ev.clientY-rect.top;const delta=ev.deltaY<0?1.12:.89;const ns=Math.max(.1,Math.min(5,scale*delta));panX=cx-(cx-panX)*(ns/scale);panY=cy-(cy-panY)*(ns/scale);scale=ns;}},{{passive:false}});
function walkPath(nid){{const s=new Set();let cur=nid;const seen=new Set();while(cur&&!seen.has(cur)){{seen.add(cur);s.add(cur);const nd=NODES.find(x=>x.id===cur);if(!nd)break;cur=nd.parent;}}function down(id){{s.add(id);EDGES.filter(e=>e.from===id).forEach(e=>down(e.to));}}down(nid);return s;}}
function handleClick(n,sx,sy){{hlSet=walkPath(n.id);popup=n.id;showPopup(n,sx,sy);}}
function showPopup(n,sx,sy){{
  const pp=document.getElementById('popup');
  document.getElementById('p-lbl').textContent=n.label;document.getElementById('p-lbl').style.color=TYPE_COL[n.type]?.text||'#e6edf3';
  document.getElementById('p-type').textContent='Type: '+n.type+' | Gate: '+n.gate;
  document.getElementById('p-name').textContent=n.name;document.getElementById('p-gate').textContent=n.gate;
  document.getElementById('p-alloc').textContent=n.alloc+' /yr';
  const ae=document.getElementById('p-ach');ae.textContent=n.achieved+' /yr';ae.className='pv '+(n.status==='pass'?'pass':n.status==='fail'?'fail':'');
  const me=document.getElementById('p-margin');
  if(n.achieved!=='–'&&n.alloc!=='–'){{const r=parseFloat(n.achieved.replace('E','e'))/parseFloat(n.alloc.replace('E','e'));me.textContent=isNaN(r)?'–':r.toFixed(3)+'×';me.className='pv '+(r<=1?'pass':'fail');}}else{{me.textContent='–';me.className='pv';}}
  const se=document.getElementById('p-status');se.textContent=n.status==='pass'?'✅ PASS':n.status==='fail'?'❌ EXCEEDS':'⬜ No data';se.className='pv '+(n.status==='pass'?'pass':n.status==='fail'?'fail':'');
  document.getElementById('p-rebal').textContent=n.rebalanced?'🔵 Yes (budget adjusted)':'No';
  document.getElementById('p-locked').textContent=n.locked?'🔒 Yes (excluded from rebalancing)':'No';
  document.getElementById('p-hz').textContent=n.hz||'–';
  pp.style.display='block';let tx=sx+16,ty=sy-10;if(tx+300>c.width-10)tx=sx-310;if(ty+320>c.height-10)ty=sy-320;pp.style.left=tx+'px';pp.style.top=ty+'px';
}}
function clearHL(){{hlSet.clear();popup=null;document.getElementById('popup').style.display='none';}}
function zoomIn(){{scale=Math.min(5,scale*1.2);}}function zoomOut(){{scale=Math.max(.1,scale/1.2);}}function resetView(){{scale=1;panX=c.width/2;panY=50;clearHL();}}
function toggleSim(){{simRunning=!simRunning;const b=document.getElementById('btnSim');b.textContent=simRunning?'⟳ Force ON':'⟳ Force OFF';b.classList.toggle('active',simRunning);}}
function toggleCA(){{allCA=!allCA;if(allCA)NODES.forEach(n=>{{if(EDGES.some(e=>e.from===n.id))collapsed.add(n.id);}});else collapsed.clear();document.getElementById('btnCA').textContent=allCA?'▼ Expand All':'▶ Collapse All';}}
const hzchips=document.getElementById('hzchips');
HZ.forEach(h=>{{const d=document.createElement('div');d.className='hchip';d.innerHTML=`<div class="hdot" style="background:${{h.color}}"></div>${{h.id}} <span style="color:#8b949e;font-size:10px">${{h.target}}</span>`;let on=true;d.addEventListener('click',()=>{{on=!on;d.classList.toggle('off',!on);on?activeHz.add(h.id):activeHz.delete(h.id);}});hzchips.appendChild(d);}});
function loop(){{simulate();draw();requestAnimationFrame(loop);}}
loop();
</script></body></html>"""

# ═══════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ FTA Controls")
    st.markdown("---")
    nodes      = st.session_state.nodes
    hz_targets = st.session_state.hz_targets

    st.markdown("**⚠️ Hazards**")
    hz_list = [n for n in nodes.values() if n["type"]=="HZ"]
    for hz in hz_list:
        hid = hz["id"]; cur = hz_targets.get(hid,1e-8)
        ev  = int(math.floor(math.log10(cur))) if cur>0 else -8
        mv  = round(cur/(10**ev),2)
        c1,c2 = st.columns([3,1])
        with c1:
            e2 = st.number_input(f"E {hid}",value=ev,min_value=-20,max_value=-1,step=1,key=f"exp_{hid}",label_visibility="collapsed")
            m2 = st.number_input(f"M {hid}",value=mv,min_value=0.1,max_value=9.9,step=0.1,key=f"mnt_{hid}",format="%.1f",label_visibility="collapsed")
            st.caption(f"**{hz['label']}**: {m2*(10**e2):.2E} /yr"); hz_targets[hid]=m2*(10**e2)
        with c2:
            if len(hz_list)>1 and st.button("🗑",key=f"delhz_{hid}"):
                for d in [hid]+descendants(nodes,hid): nodes.pop(d,None)
                hz_targets.pop(hid,None); st.rerun()

    nhl=st.text_input("New hazard label",value=f"HZ{st.session_state.next_id:02d}",key="nhl")
    nhn=st.text_input("New hazard name", value="New Hazard Event",key="nhn")
    if st.button("➕ Add Hazard",use_container_width=True):
        nid=f"HZ{st.session_state.next_id}"
        nodes[nid]={"id":nid,"label":nhl,"name":nhn,"type":"HZ","parent":None,"gate":"–","desc":"","achieved":None,"locked":False}
        hz_targets[nid]=1e-8; st.session_state.next_id+=1; st.rerun()

    st.markdown("---")
    st.markdown("**➕ Add Node**")
    node_type=st.selectbox("Type",["SF","FF","IF","AND"])
    gate_choice=st.selectbox("Gate",["OR","AND"])
    allowed=VALID_PARENTS.get(node_type,[])
    valid_pars={k:f"{v.get('label',k)} [{v['type']}]" for k,v in nodes.items() if v["type"] in allowed}
    if valid_pars:
        par_key=st.selectbox("Parent",list(valid_pars.keys()),format_func=lambda k:valid_pars[k])
        new_label=st.text_input("Label",value=f"{node_type}{st.session_state.next_id:02d}")
        new_name=st.text_input("Name",value=f"New {node_type}")
        new_desc=st.text_input("Desc",value="")
        gate_val="AND" if node_type=="AND" else gate_choice
        if st.button("➕ Add",use_container_width=True):
            nid=f"N{st.session_state.next_id}"
            nodes[nid]={"id":nid,"label":new_label,"name":new_name,"type":node_type,"parent":par_key,"gate":gate_val,"desc":new_desc,"achieved":None,"locked":False}
            st.session_state.next_id+=1; st.rerun()
    else:
        st.info(f"No valid parents for {node_type}")

    st.markdown("---")
    st.markdown("**🗑️ Delete Node**")
    del_opts={k:f"{v.get('label',k)} ({v['type']})" for k,v in nodes.items() if v["type"]!="HZ"}
    if del_opts:
        del_k=st.selectbox("Node",list(del_opts.keys()),format_func=lambda k:del_opts[k])
        nd=len(descendants(nodes,del_k))
        if nd: st.warning(f"Also removes {nd} child node(s).")
        if st.button("🗑️ Delete",use_container_width=True):
            for d in [del_k]+descendants(nodes,del_k): nodes.pop(d,None)
            st.session_state.alloc_override.pop(del_k,None)
            st.session_state.rebalanced_nodes.discard(del_k); st.rerun()

    st.markdown("---")
    if st.button("🔄 Reset to Default",use_container_width=True):
        for k in list(default_state().keys()): st.session_state.pop(k,None)
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# COMPUTE
# ═══════════════════════════════════════════════════════════════
nodes      = st.session_state.nodes
hz_targets = st.session_state.hz_targets

synced_labels = sync_worst_case(nodes)
alloc, rebalanced_set = compute_alloc(nodes, hz_targets)
rolled    = rollup_achieved(nodes)
compliance= hz_compliance(nodes, hz_targets, rolled, alloc)
order     = bfs_order(nodes)
hz_list   = [n for n in nodes.values() if n["type"]=="HZ"]
n_sf      = sum(1 for v in nodes.values() if v["type"]=="SF")
n_ff      = sum(1 for v in nodes.values() if v["type"] in ("FF","AND"))
n_if      = sum(1 for v in nodes.values() if v["type"]=="IF")
all_if    = [n for n in nodes.values() if n["type"]=="IF"]
if_done   = sum(1 for n in all_if if n.get("achieved") is not None)

# ═══════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════
st.markdown("""
<div class="fta-header">
  <h1>🌳 FTA Risk Allocator v7</h1>
  <p>Multi-hazard · Top-down allocation · Bottom-up rollup · Sibling rebalancing · Lock nodes · Worst-case sync</p>
</div>""", unsafe_allow_html=True)

# Hazard compliance banners
st.markdown("### 📊 Hazard Compliance Summary")
hz_cols = st.columns(max(len(hz_list),1))
for col, hz in zip(hz_cols, hz_list):
    hid  = hz["id"]; comp = compliance.get(hid,{}); tgt = comp.get("target",0)
    ach  = comp.get("achieved"); stat = comp.get("status","na")
    margin = comp.get("margin"); ift = comp.get("if_total",0); ife = comp.get("if_entered",0)
    css  = "pass" if stat=="pass" else ("fail" if stat=="fail" else "partial")
    icon = "✅" if stat=="pass" else ("❌" if stat=="fail" else "⬜")
    acls = "pass-val" if stat=="pass" else ("fail-val" if stat=="fail" else "warn-val")
    mcls = "pass-val" if (margin and margin<=1) else ("fail-val" if (margin and margin>1) else "warn-val")
    with col:
        st.markdown(f"""<div class="hz-summary {css}">
  <h3>{icon} {hz.get('label',hid)} — {hz.get('name','')}</h3>
  <div class="row">
    <div class="stat"><div class="lbl">Target</div><div class="val" style="color:#8b949e">{fmt(tgt)}</div></div>
    <div class="stat"><div class="lbl">Achieved</div><div class="val {acls}">{fmt(ach) if ach else '–'}</div></div>
    <div class="stat"><div class="lbl">Margin</div><div class="val {mcls}">{f"{margin:.3f}×" if margin else "–"}</div></div>
    <div class="stat"><div class="lbl">IF Progress</div><div class="val" style="color:#8b949e">{ife}/{ift}</div></div>
  </div>
</div>""", unsafe_allow_html=True)

if synced_labels:
    st.info(f"🔄 Worst-case sync: {', '.join(f'**{l}**' for l in synced_labels)} — duplicates share the worst-case achieved value.")

st.markdown("<br>", unsafe_allow_html=True)
c0,c1,c2,c3,c4 = st.columns(5)
def mc(l,v,col): return f'<div class="metric-card"><div class="ml">{l}</div><div class="mv" style="color:{col}">{v}</div></div>'
with c0: st.markdown(mc("Hazards",len(hz_list),"#f97316"),unsafe_allow_html=True)
with c1: st.markdown(mc("Sys Failures",n_sf,"#58a6ff"),unsafe_allow_html=True)
with c2: st.markdown(mc("Flw Failures",n_ff,"#3fb950"),unsafe_allow_html=True)
with c3: st.markdown(mc("Init Failures",n_if,"#d2a8ff"),unsafe_allow_html=True)
with c4: st.markdown(mc(f"IF Values",f"{if_done}/{len(all_if)}","#fbbf24"),unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tab_viz, tab_vals, tab_table, tab_edit, tab_export = st.tabs([
    "🌳 Tree","✏️ Achieved Values & Rebalancing","📋 Allocation Table","🔧 Edit Nodes","📥 Export"
])

# ── TAB 1: VIZ ───────────────────────────────────────────────
with tab_viz:
    st.caption("**🔵 Dashed ring** = rebalanced budget · **Status border**: 🟢 pass / 🔴 exceeds / ⬜ no data · **🔒** = locked node · Bottom of box: A=achieved T=allocated")
    components.html(build_viz(nodes, alloc, rolled, hz_targets, rebalanced_set), height=720, scrolling=False)

# ── TAB 2: ACHIEVED VALUES & REBALANCING ─────────────────────
with tab_vals:
    st.markdown("### ✏️ Achieved Values & Sibling Rebalancing")
    st.markdown("""
**Workflow:**
1. Enter achieved/demonstrated values at **IF level** (or any level)
2. The **parent budget stays fixed** — sibling budgets **auto-rebalance** to keep the parent sum intact
3. **Lock** 🔒 any node to exclude it from rebalancing (its budget won't move)
4. Rollup flows upward: FF → SF → HZ using gate logic
5. If achieved > parent budget, siblings clamp to 0 and hazard is flagged **non-compliant**

> Nodes sharing the same **Label** across hazards auto-sync to the worst-case value.
    """)

    for hz in hz_list:
        hid  = hz["id"]; comp = compliance.get(hid,{}); stat = comp.get("status","na")
        icon = "✅" if stat=="pass" else ("❌" if stat=="fail" else "⬜")
        st.markdown(f"#### {icon} {hz.get('label',hid)} — {hz.get('name','')}")

        subtree_ids = [i for i in order if i in ([hid]+descendants(nodes,hid)) and i!=hid and i in nodes]

        hdr = st.columns([0.3,1.2,2.2,0.6,1.4,1.8,1.4,1.2,0.7])
        for h,t in zip(hdr,["🔒","Label","Name","Type","Allocated (T)","Achieved (manual)","Rolled-up","Margin","Status"]):
            h.markdown(f"<span style='font-size:0.65rem;color:#8b949e;text-transform:uppercase'>{t}</span>",unsafe_allow_html=True)

        changed_nid = None
        changed_val = None

        for nid in subtree_ids:
            if nid not in nodes: continue
            n   = nodes[nid]; t = n["type"]
            alc = alloc.get(nid); ach = n.get("achieved"); roll = rolled.get(nid)
            stat_n = node_status(roll, alc)
            depth  = get_depth(nodes, nid)
            indent = "　"*depth
            is_synced  = n.get("label","") in synced_labels
            is_rebal   = nid in rebalanced_set
            is_locked  = n.get("locked", False)

            cols = st.columns([0.3,1.2,2.2,0.6,1.4,1.8,1.4,1.2,0.7])

            # Lock toggle
            new_lock = cols[0].checkbox("", value=is_locked, key=f"lock_{nid}", label_visibility="collapsed", help="Lock this node's budget — excluded from rebalancing")
            if new_lock != is_locked:
                nodes[nid]["locked"] = new_lock
                st.rerun()

            # Label
            tags = ""
            if is_synced: tags += '<span class="sync-tag">🔄sync</span>'
            if is_rebal:  tags += '<span class="rebal-tag">🔵rebal</span>'
            if is_locked: tags += '<span class="lock-tag">🔒locked</span>'
            cols[1].markdown(f"`{indent}{n.get('label',nid)}`{tags}", unsafe_allow_html=True)
            cols[2].markdown(f"<span style='font-size:0.78rem;color:#c9d1d9'>{n.get('name','')}</span>", unsafe_allow_html=True)
            cols[3].markdown(f"<span class='badge b-{t}'>{t}</span>", unsafe_allow_html=True)

            # Allocated (live — may be rebalanced)
            alc_color = "#58a6ff" if is_rebal else "#8b949e"
            cols[4].markdown(f"<span style='font-family:monospace;font-size:0.78rem;color:{alc_color}'>{fmt(alc)}</span>", unsafe_allow_html=True)

            # Achieved input
            with cols[5]:
                si1,si2,si3 = st.columns([1.8,1.2,0.8])
                if ach is not None and ach > 0:
                    def_e = int(math.floor(math.log10(ach))); def_m = round(ach/(10**def_e),2)
                else:
                    def_e = -3; def_m = 1.0
                m_in = si1.number_input("M",value=def_m,min_value=0.0,max_value=9.99,step=0.01,format="%.2f",key=f"am_{nid}",label_visibility="collapsed")
                e_in = si2.number_input("E",value=def_e,min_value=-20,max_value=0,step=1,key=f"ae_{nid}",label_visibility="collapsed")
                clr  = si3.button("✕",key=f"ac_{nid}",help="Clear value")
                if clr:
                    nodes[nid]["achieved"] = None
                    # Remove rebalancing override for this node's subtree
                    for d in [nid]+descendants(nodes,nid):
                        st.session_state.alloc_override.pop(d,None)
                        st.session_state.rebalanced_nodes.discard(d)
                    st.rerun()
                else:
                    new_val = m_in*(10**e_in) if m_in>0 else None
                    if new_val != ach:
                        changed_nid = nid
                        changed_val = new_val

            # Rolled-up
            cols[6].markdown(f"<span style='font-family:monospace;font-size:0.78rem;color:#8b949e'>{fmt(roll)}</span>", unsafe_allow_html=True)

            # Margin
            margin = roll/alc if (roll is not None and alc and alc>0) else None
            m_str  = f"{margin:.3f}×" if margin is not None else "–"
            m_col  = "#3fb950" if (margin and margin<=1) else ("#f85149" if margin else "#8b949e")
            cols[7].markdown(f"<span style='font-family:monospace;font-size:0.78rem;color:{m_col}'>{m_str}</span>", unsafe_allow_html=True)

            # Status
            stat_html = (
                "<span style='color:#3fb950;font-size:0.9rem'>✅</span>" if stat_n=="pass" else
                "<span style='color:#f85149;font-size:0.9rem'>❌</span>" if stat_n=="fail" else
                "<span style='color:#555;font-size:0.9rem'>–</span>"
            )
            cols[8].markdown(stat_html, unsafe_allow_html=True)

        # Apply rebalancing AFTER rendering all rows (avoids mid-loop rerun issues)
        if changed_nid is not None and changed_val is not None:
            nodes[changed_nid]["achieved"] = changed_val
            new_alloc = rebalance(nodes, alloc, changed_nid, changed_val, st.session_state.rebalanced_nodes)
            # Store overrides
            for k, v in new_alloc.items():
                base = base_allocate(nodes, hz_targets)
                if abs(v - base.get(k,0)) > 1e-30:
                    st.session_state.alloc_override[k] = v
            st.rerun()

        st.markdown("---")

# ── TAB 3: TABLE ─────────────────────────────────────────────
with tab_table:
    st.markdown("#### Full Allocation & Achieved Table")
    rows_html=""
    for nid in order:
        if nid not in nodes: continue
        n=nodes[nid]; t=n["type"]; vc=VC.get(t,"sf")
        alc=alloc.get(nid); roll=rolled.get(nid)
        stat=node_status(roll,alc)
        par=nodes[n["parent"]]["label"] if n.get("parent") and n["parent"] in nodes else "–"
        lvl=get_depth(nodes,nid); indent=lvl*18
        is_synced=n.get("label","") in synced_labels
        is_rebal=nid in rebalanced_set; is_locked=n.get("locked",False)
        tags=""
        if is_synced: tags+='<span class="sync-tag">🔄</span>'
        if is_rebal:  tags+='<span class="rebal-tag">🔵</span>'
        if is_locked: tags+='<span class="lock-tag">🔒</span>'
        stat_html=("<span style='color:#3fb950'>✅</span>" if stat=="pass" else "<span style='color:#f85149'>❌</span>" if stat=="fail" else "<span style='color:#555'>–</span>")
        margin=roll/alc if (roll is not None and alc and alc>0) else None
        mcol="#3fb950" if (margin and margin<=1) else ("#f85149" if (margin and margin>1) else "#555")
        alc_col="#58a6ff" if is_rebal else "#8b949e"
        rows_html+=f"""<tr>
          <td style="padding-left:{indent+8}px"><span class="badge b-{t}">{t}</span></td>
          <td style="padding-left:{indent+8}px"><span class="vm c-{vc}">{n.get('label',nid)}</span>{tags}</td>
          <td style="color:#c9d1d9;font-size:0.79rem">{n.get('name','')}</td>
          <td style="color:#8b949e;font-size:0.75rem;font-family:monospace">{par}</td>
          <td><span class="{'g-and' if n['gate']=='AND' else 'g-or' if n['gate']=='OR' else ''}">{n['gate']}</span></td>
          <td><span style="font-family:monospace;font-size:0.79rem;color:{alc_col}">{fmt(alc)}</span></td>
          <td style="font-family:monospace;font-size:0.79rem;color:#8b949e">{fmt(roll)}</td>
          <td style="font-family:monospace;font-size:0.79rem;color:{mcol}">{f"{margin:.3f}×" if margin else "–"}</td>
          <td>{stat_html}</td>
        </tr>"""
    st.markdown(f"""<table class="tree-table"><thead><tr>
      <th>Type</th><th>Label</th><th>Name</th><th>Parent</th><th>Gate</th>
      <th>Allocated (live)</th><th>Achieved (rolled)</th><th>Margin</th><th>Status</th>
    </tr></thead><tbody>{rows_html}</tbody></table>""",unsafe_allow_html=True)

# ── TAB 4: EDIT ──────────────────────────────────────────────
with tab_edit:
    st.markdown("#### 🔧 Edit Node Properties")
    cs,cf=st.columns([1,2])
    with cs:
        edit_opts={k:f"{v.get('label',k)} ({v['type']})" for k,v in nodes.items()}
        ek=st.selectbox("Node",list(edit_opts.keys()),format_func=lambda k:edit_opts[k],key="ek")
    with cf:
        if ek and ek in nodes:
            n=nodes[ek]; t=n["type"]
            el=st.text_input("Label",value=n.get("label",""),key="el")
            en=st.text_input("Name",value=n.get("name",""),key="en2")
            ed=st.text_area("Description",value=n.get("desc",""),key="ed2",height=60)
            if t not in ("HZ","IF"):
                go=["OR","AND"]; cg=n.get("gate","OR")
                eg=st.selectbox("Gate",go,index=go.index(cg) if cg in go else 0,key="eg2")
            else:
                eg=n.get("gate","–"); st.info(f"Gate `{eg}` fixed for {t}")
            if t!="HZ":
                ap=VALID_PARENTS.get(t,[]); vp={k:f"{v.get('label',k)} [{v['type']}]" for k,v in nodes.items() if v["type"] in ap and k!=ek and k not in descendants(nodes,ek)}
                cpk=n.get("parent",""); pk=list(vp.keys()); pi=pk.index(cpk) if cpk in pk else 0
                ep=st.selectbox("Parent",pk,index=pi,format_func=lambda k:vp[k],key="ep2") if pk else None
            else:
                ep=None
            if st.button("💾 Save",use_container_width=True,key="sv2"):
                nodes[ek].update({"label":el,"name":en,"desc":ed,"gate":eg})
                if ep: nodes[ek]["parent"]=ep
                st.success("✅ Saved!"); st.rerun()

    st.markdown("---")
    rows_all=[]
    for nid in order:
        if nid not in nodes: continue
        n=nodes[nid]; par=nodes[n["parent"]]["label"] if n.get("parent") and n["parent"] in nodes else "–"
        rows_all.append({"Label":n.get("label",""),"Name":n.get("name",""),"Type":n["type"],"Gate":n["gate"],
            "Parent":par,"Depth":get_depth(nodes,nid),"Locked":n.get("locked",False),
            "Allocated":fmt(alloc.get(nid)),"Achieved":fmt(rolled.get(nid))})
    st.dataframe(pd.DataFrame(rows_all),use_container_width=True,hide_index=True)

# ── TAB 5: EXPORT ─────────────────────────────────────────────
with tab_export:
    cx,cj=st.columns(2)
    with cx:
        st.markdown("**Excel (.xlsx)**")
        def build_excel():
            wb=Workbook(); ws=wb.active; ws.title="FTA_v7"
            def fl(h): return PatternFill("solid",start_color=h,fgColor=h)
            def af(bold=False,color="000000",sz=10): return Font(name="Arial",bold=bold,color=color,size=sz)
            def tb(): s=Side(style="thin",color="BFBFBF"); return Border(left=s,right=s,top=s,bottom=s)
            for i,w in enumerate([6,10,12,24,30,12,10,16,16,10,10,8],1):
                ws.column_dimensions[get_column_letter(i)].width=w
            ws.merge_cells("A1:L1")
            ws["A1"]="FAULT TREE ANALYSIS v7 – Multi-Hazard | Rebalanced Allocation | Achieved Rollup"
            ws["A1"].font=af(bold=True,sz=12,color="FFFFFF"); ws["A1"].fill=fl("1F3864")
            ws["A1"].alignment=Alignment(horizontal="center",vertical="center"); ws.row_dimensions[1].height=28
            hdrs=["Type","Label","Name","Description","Parent","Gate","Allocated","Achieved","Rolled-up","Margin","Status","Locked"]
            for c2,h in enumerate(hdrs,1):
                cell=ws.cell(row=2,column=c2,value=h); cell.font=af(bold=True,sz=10,color="FFFFFF"); cell.fill=fl("2E75B6")
                cell.alignment=Alignment(horizontal="center",vertical="center",wrap_text=True); cell.border=tb()
            ws.row_dimensions[2].height=26
            BG={"HZ":"C00000","SF":"1F4E79","FF":"375623","IF":"833C00","AND":"4A148C"}
            LT={"HZ":"FFE7E7","SF":"DEEAF1","FF":"E2EFDA","IF":"FCE4D6","AND":"EAD1DC"}
            for i,nid in enumerate(order):
                if nid not in nodes: continue
                n=nodes[nid]; t=n["type"]
                par=nodes[n["parent"]]["label"] if n.get("parent") and n["parent"] in nodes else "–"
                alc=alloc.get(nid); rol=rolled.get(nid)
                margin=rol/alc if (rol is not None and alc and alc>0) else None
                status="PASS" if node_status(rol,alc)=="pass" else ("EXCEEDS" if node_status(rol,alc)=="fail" else "–")
                r=i+3
                vals=[t,n.get("label",""),n.get("name",""),n.get("desc",""),par,n["gate"],alc,n.get("achieved"),rol,margin,status,"YES" if n.get("locked") else "no"]
                for c2,v in enumerate(vals,1):
                    cell=ws.cell(row=r,column=c2,value=v); cell.border=tb()
                    cell.alignment=Alignment(horizontal="left" if c2 in(2,3,4) else "center",vertical="center",wrap_text=(c2 in(3,4)))
                    if c2==1:
                        cell.fill=fl(BG.get(t,"1F3864")); cell.font=af(bold=True,sz=9,color="FFFFFF")
                        cell.alignment=Alignment(horizontal="center",vertical="center")
                    elif c2 in(7,8,9):
                        cell.number_format="0.00E+00"
                        fc=("375623" if status=="PASS" else "C00000") if c2==9 else "000000"
                        cell.font=af(bold=(c2==9),sz=10,color=fc)
                    elif c2==10:
                        cell.number_format="0.000"
                        cell.font=af(sz=9,color="375623" if (margin and margin<=1) else ("C00000" if (margin and margin>1) else "595959"))
                    elif c2==11:
                        cell.font=af(bold=True,sz=9,color="375623" if status=="PASS" else ("C00000" if status=="EXCEEDS" else "595959"))
                    else:
                        cell.fill=fl(LT.get(t,"F2F2F2") if c2 in(2,6) else "FFFFFF"); cell.font=af(sz=9)
                ws.row_dimensions[r].height=16
            out=io.BytesIO(); wb.save(out); out.seek(0); return out.getvalue()
        st.download_button("⬇️ Excel",data=build_excel(),file_name="FTA_v7.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
    with cj:
        st.markdown("**JSON – Save / Load**")
        payload=json.dumps({"nodes":st.session_state.nodes,"hz_targets":st.session_state.hz_targets,
                            "alloc_override":st.session_state.alloc_override,
                            "rebalanced_nodes":list(st.session_state.rebalanced_nodes)},indent=2)
        st.download_button("⬇️ JSON",data=payload,file_name="fta_v7.json",mime="application/json",use_container_width=True)
        up=st.file_uploader("Load JSON",type="json",key="jup")
        if up:
            try:
                d=json.load(up)
                if "nodes" in d and "hz_targets" in d:
                    st.session_state.nodes=d["nodes"]; st.session_state.hz_targets=d["hz_targets"]
                    st.session_state.alloc_override=d.get("alloc_override",{})
                    st.session_state.rebalanced_nodes=set(d.get("rebalanced_nodes",[]))
                    st.success("✅ Loaded!"); st.rerun()
            except Exception as e: st.error(str(e))
    st.markdown("---")
    st.markdown("""
#### Rebalancing Logic Reference

| Gate | Allocation formula | Rebalancing when one child is fixed |
|------|--------------------|-------------------------------------|
| **OR** | Child = Parent ÷ n | Remaining = Parent − fixed − Σlocked; free siblings split remaining equally |
| **AND** | Child = Parent^(1/n) | x^n_free = Parent / (fixed × Πlocked); each free sibling gets x |

**Lock feature:** Locked nodes are excluded from all rebalancing. Their budget stays at current allocated value.
**Cascade:** When a sibling is rebalanced, it cascades the new budget down to all its children recursively.
**Non-compliant:** If fixed value > parent budget, free siblings clamp to 0 and hazard is marked ❌.
    """)
