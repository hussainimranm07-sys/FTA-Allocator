import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import math, io, json, datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

st.set_page_config(page_title="FTA Risk Allocator v9", page_icon="🌳", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');
html,body,[class*="css"]{font-family:'IBM Plex Sans',sans-serif}
.stApp{background:#0d1117;color:#e6edf3}
section[data-testid="stSidebar"]{background:#161b22!important;border-right:1px solid #30363d}
section[data-testid="stSidebar"] *{color:#e6edf3!important}
.fta-header{background:linear-gradient(135deg,#1a2332,#0d1117);border:1px solid #30363d;
  border-left:4px solid #f97316;border-radius:8px;padding:14px 22px;margin-bottom:14px}
.fta-header h1{font-family:'IBM Plex Mono',monospace;font-size:1.3rem;color:#f97316;margin:0 0 2px}
.fta-header p{color:#8b949e;margin:0;font-size:0.75rem}
.metric-card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px 14px}
.metric-card .ml{font-size:0.62rem;color:#8b949e;text-transform:uppercase;letter-spacing:1px;margin-bottom:3px}
.metric-card .mv{font-family:'IBM Plex Mono',monospace;font-size:1rem;font-weight:700}
.tree-table{width:100%;border-collapse:collapse;font-size:0.8rem}
.tree-table th{background:#1c2128;color:#8b949e;font-size:0.62rem;text-transform:uppercase;
  letter-spacing:1px;padding:8px 10px;text-align:left;border-bottom:1px solid #30363d}
.tree-table td{padding:6px 10px;border-bottom:1px solid #21262d;vertical-align:middle}
.tree-table tr:hover td{background:#1c2128}
.badge{display:inline-block;padding:2px 7px;border-radius:10px;font-size:0.67rem;
  font-weight:700;font-family:'IBM Plex Mono',monospace}
.b-HZ{background:#3d1a00;color:#f97316;border:1px solid #f97316}
.b-SF{background:#0d2136;color:#58a6ff;border:1px solid #58a6ff}
.b-FF{background:#0d2b14;color:#3fb950;border:1px solid #3fb950}
.b-IF{background:#1e0d36;color:#d2a8ff;border:1px solid #d2a8ff}
.b-AND{background:#2d1a3d;color:#e040fb;border:1px solid #e040fb}
.g-or{color:#58a6ff;font-weight:700;font-family:'IBM Plex Mono';font-size:0.73rem}
.g-and{color:#e040fb;font-weight:700;font-family:'IBM Plex Mono';font-size:0.73rem}
.vm{font-family:'IBM Plex Mono',monospace;font-size:0.78rem;font-weight:600}
.c-hz{color:#f97316}.c-sf{color:#58a6ff}.c-ff{color:#3fb950}.c-if{color:#d2a8ff}.c-and{color:#e040fb}
.tag{display:inline-block;padding:1px 5px;border-radius:5px;font-size:0.59rem;font-weight:700;margin-left:3px}
.tag-lock{background:#1c2128;color:#fbbf24;border:1px solid #fbbf24}
.tag-sync{background:#2d1e00;color:#fbbf24;border:1px solid #fbbf24}
.tag-rebal{background:#0d2136;color:#58a6ff;border:1px solid #58a6ff}
.change-log{background:#161b22;border:1px solid #30363d;border-left:3px solid #fbbf24;
  border-radius:6px;padding:10px 14px;margin:8px 0;font-size:0.78rem}
.change-log .cl-title{color:#fbbf24;font-weight:700;margin-bottom:6px;font-family:'IBM Plex Mono',monospace}
.change-log .cl-row{color:#8b949e;padding:2px 0;font-size:0.73rem}
.change-log .cl-row span{color:#e6edf3;font-family:'IBM Plex Mono',monospace}
div[data-testid="stExpander"]{background:#161b22;border:1px solid #30363d;border-radius:8px}
.stButton button{background:#1c2128!important;border:1px solid #30363d!important;color:#e6edf3!important;border-radius:6px!important}
.stButton button:hover{border-color:#58a6ff!important;color:#58a6ff!important}
.stTabs [data-baseweb="tab"]{color:#8b949e}
.stTabs [aria-selected="true"]{color:#f97316!important;border-bottom-color:#f97316!important}
.tip{display:inline-block;position:relative;cursor:help;color:#58a6ff;font-size:0.75rem;margin-left:4px;vertical-align:middle}
.tip:hover .tipbox{display:block}
.tipbox{display:none;position:absolute;left:50%;transform:translateX(-50%);bottom:130%;background:#1c2128;border:1px solid #30363d;border-radius:7px;padding:9px 13px;min-width:260px;max-width:320px;font-size:0.72rem;color:#c9d1d9;z-index:999;box-shadow:0 8px 32px rgba(0,0,0,.8);line-height:1.55;pointer-events:none;white-space:normal;text-align:left}
.tipbox strong{color:#f97316}.tipbox code{color:#3fb950;font-family:monospace}
.col-alloc{display:inline-block;background:#0d2136;border:1px solid #1e3a5f;border-radius:6px;padding:2px 8px;font-family:monospace;font-size:0.78rem;color:#58a6ff;font-weight:700}
.col-alloc.rebal{color:#fbbf24;background:#1a1400;border-color:#4a3500}
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

GATE_INFO = {
    "OR":  "OR Gate: Any single child failure causes the parent.\nAlloc (top-down): each child = parent ÷ n\nRollup (bottom-up): parent = Σ children",
    "AND": "AND Gate: ALL children must fail simultaneously.\nAlloc (top-down): each child = parent^(1/n)\nRollup (bottom-up): parent = Π children",
    "–":   "Top-level Hazard node. Budget = HZ target.",
}
TYPE_INFO = {
    "HZ":  "Hazard (HZ): Top-level undesired event. Target = max tolerable failure rate/year.",
    "SF":  "System Failure (SF): High-level failure mode contributing to the hazard.",
    "FF":  "Following Failure (FF): Sub-system failure mode. Child of SF or another FF.",
    "IF":  "Initiating Failure (IF): Leaf-level basic event. Enter demonstrated/achieved value here.",
    "AND": "AND Node: Combined Faults gate — all children must fail simultaneously.",
}

# ═══════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════
def default_state():
    return {
        "nodes": {},
        "hz_targets": {},
        "next_id": 1,
        # alloc_override: maps nid -> float, ONLY for manually rebalanced nodes
        # Key rule: these override the pure top-down allocation ONLY when explicitly set
        # They are NEVER set from achieved values
        "alloc_override": {},
        "rebalanced_nodes": set(),
        "change_log": [],
        "flash_ids": [],
        "cascade_summary": [],
    }

for k, v in default_state().items():
    if k not in st.session_state:
        st.session_state[k] = v
if not isinstance(st.session_state.get("rebalanced_nodes"), set):
    st.session_state["rebalanced_nodes"] = set()

# Startup: clear any zero/invalid overrides that may have been saved
_ov = st.session_state.get("alloc_override", {})
_nd = st.session_state.get("nodes", {})
for _k in [k for k, v in _ov.items() if not (v and v > 0 and k in _nd)]:
    _ov.pop(_k, None)

# ═══════════════════════════════════════════════════════════════
# AUTOSAVE
# ═══════════════════════════════════════════════════════════════
def serialize_state():
    return json.dumps({
        "nodes":            st.session_state.nodes,
        "hz_targets":       st.session_state.hz_targets,
        "next_id":          st.session_state.next_id,
        "alloc_override":   {k:v for k,v in st.session_state.alloc_override.items() if v and v > 0},
        "rebalanced_nodes": list(st.session_state.rebalanced_nodes),
        "saved_at":         datetime.datetime.utcnow().isoformat() + "Z",
        "version": "v9",
    })

def deserialize_state(raw):
    try:
        d = json.loads(raw)
        if "nodes" not in d or "hz_targets" not in d: return False
        st.session_state.nodes            = d["nodes"]
        st.session_state.hz_targets       = d["hz_targets"]
        st.session_state.next_id          = d.get("next_id", 1)
        st.session_state.alloc_override   = {k:v for k,v in d.get("alloc_override",{}).items() if v and v > 0}
        st.session_state.rebalanced_nodes = set(d.get("rebalanced_nodes", []))
        st.session_state.change_log       = []
        st.session_state.flash_ids        = []
        st.session_state.cascade_summary  = []
        return True
    except Exception:
        return False

AUTOSAVE_KEY = "fta_autosave_v9"

def autosave_bridge(state_json, slot_names):
    sj = json.dumps(state_json)
    sl = json.dumps(slot_names)
    return f"""<!DOCTYPE html><html><head><style>body{{margin:0;height:0;overflow:hidden}}</style></head><body><script>
const KEY='{AUTOSAVE_KEY}';
try{{localStorage.setItem(KEY,{sj});}}catch(e){{}}
if(!sessionStorage.getItem('fta_restored_v9')){{
  sessionStorage.setItem('fta_restored_v9','1');
  const s=localStorage.getItem(KEY);
  if(s)try{{window.parent.postMessage({{type:'fta_restore',data:s}},'*');}}catch(e){{}}
}}
try{{const sl=JSON.parse(localStorage.getItem('fta_slot_list_v9')||'[]');
window.parent.postMessage({{type:'fta_slots_list',slots:sl}},'*');}}catch(e){{}}
window.addEventListener('message',function(ev){{
  if(!ev.data||!ev.data.type)return;
  if(ev.data.type==='fta_slot_save'){{
    try{{localStorage.setItem('fta_slot_v9_'+ev.data.name,ev.data.data);
    let sl=JSON.parse(localStorage.getItem('fta_slot_list_v9')||'[]');
    if(!sl.includes(ev.data.name))sl.push(ev.data.name);
    localStorage.setItem('fta_slot_list_v9',JSON.stringify(sl));
    window.parent.postMessage({{type:'fta_slots_list',slots:sl}},'*');}}catch(e){{}}
  }}
  if(ev.data.type==='fta_slot_load'){{
    try{{const d=localStorage.getItem('fta_slot_v9_'+ev.data.name);
    if(d)window.parent.postMessage({{type:'fta_restore',data:d}},'*');}}catch(e){{}}
  }}
  if(ev.data.type==='fta_slot_delete'){{
    try{{localStorage.removeItem('fta_slot_v9_'+ev.data.name);
    let sl=JSON.parse(localStorage.getItem('fta_slot_list_v9')||'[]');
    sl=sl.filter(s=>s!==ev.data.name);
    localStorage.setItem('fta_slot_list_v9',JSON.stringify(sl));
    window.parent.postMessage({{type:'fta_slots_list',slots:sl}},'*');}}catch(e){{}}
  }}
}});
</script></body></html>"""

RELAY_COMPONENT = """<!DOCTYPE html><html><head><style>body{margin:0;height:0;overflow:hidden}</style></head><body><script>
window.addEventListener('message',function(ev){
  if(!ev.data)return;
  function relay(label,val){
    const el=window.parent.document.querySelector('input[aria-label="'+label+'"]');
    if(el){const s=Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype,'value').set;
    s.call(el,val);el.dispatchEvent(new Event('input',{bubbles:true}));}
  }
  if(ev.data.type==='fta_restore')relay('__fta_restore__',ev.data.data);
  if(ev.data.type==='fta_slots_list')relay('__fta_slots__',JSON.stringify(ev.data.slots));
});
</script></body></html>"""

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

def get_parent_chain(nodes, nid):
    chain, cur, seen = [], nid, set()
    while cur and cur not in seen:
        seen.add(cur); chain.append(cur)
        cur = nodes.get(cur, {}).get("parent")
    return list(reversed(chain))

def descendants(nodes, nid):
    d = []
    for k, n in nodes.items():
        if n.get("parent") == nid:
            d.append(k); d.extend(descendants(nodes, k))
    return d

def get_siblings(nodes, nid):
    node = nodes.get(nid)
    if not node or not node.get("parent"): return []
    return [n["id"] for n in get_children(nodes, node["parent"]) if n["id"] != nid]

def fmt(v):
    if v is None: return "–"
    if v == 0:    return "0.000E+00"
    return f"{v:.3E}"

def nodes_by_label(nodes, label):
    return [nid for nid, n in nodes.items() if n.get("label","") == label]

def _tip(label, body):
    body_esc = body.replace('"', "&quot;")
    return (f'<span class="tip">{label}'
            f'<span class="tipbox">{body_esc}</span></span>')

TIP_ALLOC = _tip(
    "ⓘ",
    "<strong>Allocated (T)</strong> — Target failure rate budget, calculated pure top-down from the Hazard target.<br>"
    "OR gate: <code>T = Parent &divide; n</code><br>"
    "AND gate: <code>T = Parent<sup>1/n</sup></code><br>"
    "This value is <em>pure maths</em> — it <strong>never changes</strong> because of achieved values. "
    "It only changes when the tree structure changes or you lock a node and manually rebalance."
)
TIP_ACHIEVED = _tip(
    "ⓘ",
    "<strong>Achieved (A)</strong> — The demonstrated or estimated failure rate you enter.<br>"
    "Enter at <strong>IF (Initiating Failure)</strong> leaf nodes for the most accurate rollup.<br>"
    "You can also override at SF or FF level.<br>"
    "Nodes sharing the same <strong>Label</strong> across hazards are synced: "
    "the highest (worst-case) value propagates automatically to all of them."
)
TIP_ROLLED = _tip(
    "ⓘ",
    "<strong>Rolled-up (A)</strong> — Bottom-up calculated result.<br>"
    "OR gate: <code>A = &sum; children</code><br>"
    "AND gate: <code>A = &prod; children</code><br>"
    "<strong style='color:#3fb950'>Green</strong> = A &le; T (within budget)<br>"
    "<strong style='color:#f85149'>Red</strong> = A &gt; T (exceeds budget)<br>"
    "For non-leaf nodes: if you entered a manual value, that overrides the rollup."
)

# ═══════════════════════════════════════════════════════════════
# ALLOCATION ENGINE
# ═══════════════════════════════════════════════════════════════
# RULE: Allocation (Target/Budget) is COMPLETELY independent of Achieved values.
# Achieved values NEVER influence the allocation tree.
# The only way allocation changes is:
#   1. Pure top-down from HZ targets (base_allocate)
#   2. Manual lock + rebalance triggered by user via the rebalance button
#      (alloc_override stores per-node manual budget splits)
# ═══════════════════════════════════════════════════════════════

def base_allocate(nodes, hz_targets):
    """
    Pure top-down allocation. Completely ignores achieved values.
    OR gate:  each child = parent / n
    AND gate: each child = parent ^ (1/n)
    """
    alloc = {}
    def recurse(nid, budget):
        alloc[nid] = budget
        children = get_children(nodes, nid)
        if not children: return
        n = len(children)
        for child in children:
            if child["gate"] == "AND":
                cb = budget ** (1.0 / n) if budget > 0 else 0.0
            else:  # OR or –
                cb = budget / n if n > 0 else 0.0
            recurse(child["id"], cb)
    for hz in get_hz_roots(nodes):
        recurse(hz["id"], hz_targets.get(hz["id"], 1e-8))
    return alloc

def compute_alloc(nodes, hz_targets):
    """
    Final allocation = base_allocate + manual overrides.
    Overrides are only applied when:
    - node exists in tree
    - override value is strictly positive
    - base allocation for that node is also positive (reachable)
    Zero overrides are NEVER applied — they are treated as stale/invalid.
    """
    alloc = base_allocate(nodes, hz_targets)
    # Prune stale overrides
    stale = [k for k, v in st.session_state.get("alloc_override", {}).items()
             if k not in nodes or not (v and v > 0)]
    for k in stale:
        st.session_state["alloc_override"].pop(k, None)
    # Apply valid overrides
    for nid, val in st.session_state.get("alloc_override", {}).items():
        if nid in nodes and val > 0 and alloc.get(nid, 0) > 0:
            alloc[nid] = val
    return alloc, st.session_state.get("rebalanced_nodes", set())

# ═══════════════════════════════════════════════════════════════
# MANUAL REBALANCE ENGINE
# Triggered only by explicit user action (lock + rebalance button).
# Uses ONLY alloc values — never touches achieved.
# ═══════════════════════════════════════════════════════════════

def _split_budget_down(nodes, alloc, nid, budget, rebal_set, log):
    """
    Recursively distribute `budget` to children of `nid`.
    Uses locked children's CURRENT ALLOC (never achieved) to compute remaining.
    """
    alloc[nid] = budget
    children = get_children(nodes, nid)
    if not children: return
    locked   = [c for c in children if nodes[c["id"]].get("locked", False)]
    free     = [c for c in children if not nodes[c["id"]].get("locked", False)]
    gate     = children[0].get("gate", "OR")
    n_free   = len(free)
    if n_free == 0: return

    if gate == "OR":
        # locked children keep their current alloc; split remainder among free
        locked_sum = sum(alloc.get(c["id"], 0) for c in locked)
        remaining  = max(0.0, budget - locked_sum)
        share      = remaining / n_free
        for c in free:
            old = alloc.get(c["id"])
            alloc[c["id"]] = share
            rebal_set.add(c["id"])
            if old is not None and abs(share - (old or 0)) > 1e-30:
                log.append({"nid": c["id"], "label": nodes[c["id"]].get("label",""),
                            "old": old, "new": share, "reason": "OR rebalance"})
            _split_budget_down(nodes, alloc, c["id"], share, rebal_set, log)
    else:  # AND
        locked_prod = 1.0
        for c in locked:
            v = alloc.get(c["id"], 1e-8) or 1e-8
            locked_prod *= max(v, 1e-300)
        denom = locked_prod if locked_prod > 0 else 1e-300
        numerator = (budget / denom) if budget > 0 else 0
        x = numerator ** (1.0 / n_free) if numerator > 0 else 0.0
        for c in free:
            old = alloc.get(c["id"])
            alloc[c["id"]] = x
            rebal_set.add(c["id"])
            if old is not None and abs(x - (old or 0)) > 1e-30:
                log.append({"nid": c["id"], "label": nodes[c["id"]].get("label",""),
                            "old": old, "new": x, "reason": "AND rebalance"})
            _split_budget_down(nodes, alloc, c["id"], x, rebal_set, log)

def manual_rebalance(nodes, alloc, locked_nid, log):
    """
    When user locks a node and triggers rebalance:
    - parent budget is sacred and unchanged
    - locked node keeps its current alloc
    - free siblings split the remainder
    - cascades down to their children
    """
    alloc = dict(alloc)
    node = nodes.get(locked_nid)
    if not node: return alloc
    parent_id = node.get("parent")
    if not parent_id or parent_id not in nodes: return alloc
    parent_budget = alloc.get(parent_id, 0)
    rebal_set = set(st.session_state.get("rebalanced_nodes", set()))
    _split_budget_down(nodes, alloc, parent_id, parent_budget, rebal_set, log)
    st.session_state["rebalanced_nodes"] = rebal_set
    # Persist overrides (only positive, non-base values)
    base = base_allocate(nodes, st.session_state["hz_targets"])
    for nid, val in alloc.items():
        if nid in nodes and val > 0 and abs(val - base.get(nid, 0)) > 1e-30:
            st.session_state["alloc_override"][nid] = val
        else:
            st.session_state["alloc_override"].pop(nid, None)
    return alloc

# ═══════════════════════════════════════════════════════════════
# ACHIEVED ROLLUP  (completely separate from allocation)
# ═══════════════════════════════════════════════════════════════

def rollup_achieved(nodes):
    """
    Bottom-up rollup of achieved values.
    Completely independent of allocation — never modifies alloc.
    OR gate:  parent = Σ children
    AND gate: parent = Π children
    Leaf nodes use their manually entered achieved value.
    Non-leaf nodes: if manual override exists, use it; else use rollup.
    """
    rolled = {}
    def compute(nid):
        if nid in rolled: return rolled[nid]
        node = nodes.get(nid)
        if not node: rolled[nid] = None; return None
        children = get_children(nodes, nid)
        if not children:
            rolled[nid] = node.get("achieved")
            return rolled[nid]
        child_vals = [compute(c["id"]) for c in children]
        if any(v is None for v in child_vals):
            # incomplete subtree — use manual if available
            rolled[nid] = node.get("achieved")
            return rolled[nid]
        gate = node.get("gate", "OR")
        if gate == "AND":
            val = 1.0
            for v in child_vals: val *= v
        else:
            val = sum(child_vals)
        manual = node.get("achieved")
        rolled[nid] = manual if manual is not None else val
        return rolled[nid]
    for hz in get_hz_roots(nodes): compute(hz["id"])
    for nid in nodes:
        if nid not in rolled: compute(nid)
    return rolled

# ═══════════════════════════════════════════════════════════════
# SHARED FAILURE SYNC
# When achieved value changes on node N with label L:
#   1. Find all nodes with same label (across all hazards)
#   2. Apply worst-case (max) achieved to all of them
#   3. Log the changes
# NOTE: This does NOT touch allocation at all.
# ═══════════════════════════════════════════════════════════════

def apply_shared_sync(nodes, changed_nid, changed_value):
    """
    Sync worst-case achieved value across all nodes sharing the same label.
    Returns: (log entries, list of synced node ids)
    Does NOT modify allocation.
    """
    log = []
    label = nodes[changed_nid].get("label", "")
    peers = nodes_by_label(nodes, label)
    peer_vals = [nodes[p].get("achieved") for p in peers if nodes[p].get("achieved") is not None]
    worst = max([changed_value] + [v for v in peer_vals if v is not None])
    synced_ids = []
    for peer_id in peers:
        old_ach = nodes[peer_id].get("achieved")
        nodes[peer_id]["achieved"] = worst
        synced_ids.append(peer_id)
        if peer_id != changed_nid:
            log.append({
                "nid": peer_id, "label": label,
                "old": old_ach, "new": worst,
                "reason": "shared label → worst-case sync"
            })
    return log, synced_ids

# ═══════════════════════════════════════════════════════════════
# NODE STATUS  (compare achieved rollup vs allocated)
# ═══════════════════════════════════════════════════════════════

def node_status(achieved, allocated):
    if achieved is None or allocated is None: return "na"
    return "pass" if achieved <= allocated else "fail"

# ═══════════════════════════════════════════════════════════════
# VISUALIZATION
# ═══════════════════════════════════════════════════════════════
def build_viz(nodes, alloc, rolled, hz_targets, rebal_set, flash_ids=None):
    if flash_ids is None: flash_ids = set()
    order = bfs_order(nodes)
    hz_ids = [n["id"] for n in get_hz_roots(nodes)]
    hz_color_map = {hid: HZ_PALETTE[i%len(HZ_PALETTE)] for i,hid in enumerate(hz_ids)}

    node_data = []
    for nid in order:
        if nid not in nodes: continue
        n = nodes[nid]
        hz_anc = get_hz_ancestor(nodes, nid)
        depth  = get_depth(nodes, nid)
        ach    = rolled.get(nid); alc = alloc.get(nid)
        stat   = node_status(ach, alc)
        chain  = " → ".join(nodes[c].get("label","?") for c in get_parent_chain(nodes, nid) if c in nodes)
        siblings = get_siblings(nodes, nid)
        sib_info = [{"label": nodes[s].get("label",""), "alloc": fmt(alloc.get(s)), "achieved": fmt(rolled.get(s))} for s in siblings if s in nodes]
        margin = ach/alc if (ach is not None and alc and alc > 0) else None
        node_data.append({
            "id": nid, "label": n.get("label",nid), "name": n.get("name",""),
            "desc": n.get("desc",""), "type": n["type"], "gate": n["gate"],
            "alloc": fmt(alc), "achieved": fmt(ach), "ach_raw": n.get("achieved"),
            "margin": f"{margin:.3f}×" if margin is not None else "–",
            "status": stat, "rebalanced": nid in rebal_set,
            "locked": n.get("locked",False),
            "hz": hz_anc or "", "hz_color": hz_color_map.get(hz_anc,"#58a6ff"),
            "depth": depth, "parent": n.get("parent") or "",
            "chain": chain, "siblings": sib_info,
            "type_info": TYPE_INFO.get(n["type"],""),
            "gate_info": GATE_INFO.get(n["gate"],""),
            "flash": nid in flash_ids,
        })

    edge_data = [{"from": n.get("parent"), "to": nid, "gate": n["gate"]}
                 for nid, n in nodes.items() if n.get("parent") and n["parent"] in nodes]
    hz_list   = [{"id":h,"color":hz_color_map[h],"target":fmt(hz_targets.get(h,1e-8))} for h in hz_ids]
    nj = json.dumps(node_data); ej = json.dumps(edge_data)
    hj = json.dumps(hz_list);   fj = json.dumps(list(flash_ids))

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0d1117;font-family:'IBM Plex Sans',sans-serif;overflow:hidden;user-select:none}}
#wrap{{position:relative;width:100%;height:720px;overflow:hidden}}
canvas{{position:absolute;top:0;left:0;cursor:grab}}canvas.grabbing{{cursor:grabbing}}
#ctrl{{position:absolute;top:12px;left:12px;display:flex;flex-direction:column;gap:4px;z-index:20}}
.btn{{background:#161b22;border:1px solid #30363d;color:#e6edf3;padding:5px 10px;border-radius:6px;cursor:pointer;font-size:11px;font-family:inherit;transition:all .15s;white-space:nowrap}}
.btn:hover{{border-color:#58a6ff;color:#58a6ff}}.btn.active{{border-color:#f97316;color:#f97316}}
#search-box{{position:absolute;top:12px;left:50%;transform:translateX(-50%);z-index:25;display:flex;gap:6px;align-items:center}}
#search-input{{background:#161b22;border:1px solid #30363d;color:#e6edf3;padding:5px 12px;border-radius:6px;font-size:12px;font-family:inherit;width:230px;outline:none}}
#search-input:focus{{border-color:#58a6ff}}#search-input::placeholder{{color:#555}}
#search-count{{color:#8b949e;font-size:10px;white-space:nowrap}}
#hzf{{position:absolute;top:12px;right:12px;background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px 14px;z-index:20;min-width:175px}}
#hzf .title{{color:#8b949e;font-size:10px;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px}}
.hchip{{display:flex;align-items:center;gap:6px;cursor:pointer;padding:3px 0;font-size:11px;color:#e6edf3;transition:opacity .15s}}
.hchip.off{{opacity:0.3}}.hdot{{width:9px;height:9px;border-radius:50%;flex-shrink:0}}
#legend{{position:absolute;bottom:46px;left:12px;background:#161b22;border:1px solid #30363d;border-radius:6px;padding:7px 11px;font-size:10px;color:#8b949e;z-index:20;display:flex;gap:10px;flex-wrap:wrap;max-width:420px}}
.leg{{display:flex;align-items:center;gap:4px}}.leg-dot{{width:8px;height:8px;border-radius:50%}}
#info{{position:absolute;bottom:10px;left:12px;background:#161b22;border:1px solid #30363d;border-radius:6px;padding:4px 11px;font-size:10px;color:#8b949e;z-index:20}}
#popup{{position:absolute;background:#1c2128;border:1px solid #30363d;border-radius:10px;padding:12px 16px;min-width:260px;max-width:295px;z-index:30;display:none;box-shadow:0 12px 40px rgba(0,0,0,.75);pointer-events:none}}
#popup h3{{font-family:'IBM Plex Mono',monospace;font-size:13px;margin:0 0 2px}}
#popup .psub{{font-size:9px;color:#8b949e;margin-bottom:8px;word-break:break-all}}
#popup .prow{{display:flex;justify-content:space-between;gap:10px;padding:3px 0;border-bottom:1px solid #21262d;font-size:10px}}
#popup .prow:last-of-type{{border:none}}
#popup .pk{{color:#8b949e}}#popup .pv{{color:#e6edf3;font-family:'IBM Plex Mono',monospace;text-align:right}}
#popup .pv.pass{{color:#3fb950}}#popup .pv.fail{{color:#f85149}}
#popup .phint{{margin-top:7px;font-size:9px;color:#444;text-align:center}}
#ctx-menu{{position:absolute;background:#1c2128;border:1px solid #30363d;border-radius:10px;padding:0;width:320px;z-index:40;display:none;box-shadow:0 12px 48px rgba(0,0,0,.85);overflow:hidden;pointer-events:all}}
#ctx-menu .cm-head{{padding:9px 14px 8px;background:#161b22;border-bottom:1px solid #30363d;display:flex;align-items:center;justify-content:space-between}}
#ctx-menu .cm-head h4{{font-family:'IBM Plex Mono',monospace;font-size:12px;color:#f97316;margin:0}}
#ctx-menu .cm-head .cm-close{{background:none;border:none;color:#8b949e;cursor:pointer;font-size:16px;padding:0}}
#ctx-menu .cm-head .cm-close:hover{{color:#e6edf3}}
#ctx-menu .cm-body{{padding:10px 14px;max-height:490px;overflow-y:auto}}
#ctx-menu .cm-sec{{font-size:9px;color:#8b949e;text-transform:uppercase;letter-spacing:1px;margin:10px 0 4px;border-top:1px solid #21262d;padding-top:7px}}
#ctx-menu .cm-sec.first{{margin-top:0;border-top:none;padding-top:0}}
#ctx-menu .cm-row{{display:flex;justify-content:space-between;align-items:flex-start;padding:3px 0;font-size:10px}}
#ctx-menu .cm-key{{color:#8b949e;flex-shrink:0;min-width:90px}}
#ctx-menu .cm-val{{font-family:'IBM Plex Mono',monospace;font-size:10px;color:#e6edf3;text-align:right;word-break:break-all}}
#ctx-menu .cm-val.pass{{color:#3fb950}}#ctx-menu .cm-val.fail{{color:#f85149}}
#ctx-menu .cm-val.rebal{{color:#58a6ff}}#ctx-menu .cm-val.warn{{color:#fbbf24}}
#ctx-menu .cm-chain{{color:#fbbf24;font-size:10px;padding:3px 0;word-break:break-all}}
#ctx-menu .cm-info{{color:#8b949e;font-size:9px;font-style:italic;padding:3px 0;line-height:1.5}}
#ctx-menu .cm-sib{{display:flex;justify-content:space-between;padding:2px 0;font-size:10px;font-family:monospace;color:#8b949e}}
#ctx-menu .cm-el{{font-size:9px;color:#8b949e;margin-bottom:3px;text-transform:uppercase;letter-spacing:1px}}
#ctx-menu .cm-er{{display:flex;gap:6px;align-items:center;margin-bottom:5px}}
#ctx-menu .cm-er label{{font-size:10px;color:#8b949e;flex-shrink:0;width:62px}}
#ctx-menu input[type=number]{{background:#0d1117;border:1px solid #30363d;color:#e6edf3;padding:4px 7px;border-radius:5px;font-size:11px;font-family:'IBM Plex Mono',monospace;width:100%;outline:none}}
#ctx-menu input:focus{{border-color:#58a6ff}}
#ctx-menu .cm-preview{{font-family:monospace;font-size:11px;color:#8b949e;margin:4px 0;text-align:center}}
#ctx-menu .cm-btns{{display:flex;gap:6px;margin-top:7px}}
#ctx-menu .cm-btn{{background:#1c2128;border:1px solid #30363d;color:#e6edf3;padding:5px 10px;border-radius:5px;cursor:pointer;font-size:11px;flex:1;transition:all .15s}}
#ctx-menu .cm-btn:hover{{border-color:#58a6ff;color:#58a6ff}}
#ctx-menu .cm-btn.save{{background:#0a2a1a;border-color:#3fb950;color:#3fb950}}
#ctx-menu .cm-btn.clr{{background:#2a0a0a;border-color:#f85149;color:#f85149}}
#cascade-overlay{{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);background:#1c2128;border:2px solid #fbbf24;border-radius:12px;padding:18px 22px;z-index:50;display:none;box-shadow:0 16px 56px rgba(0,0,0,.9);min-width:300px;max-width:400px;pointer-events:all}}
#cascade-overlay h4{{font-family:'IBM Plex Mono',monospace;font-size:13px;color:#fbbf24;margin:0 0 10px}}
.co-row{{font-size:11px;color:#8b949e;padding:3px 0;border-bottom:1px solid #21262d}}
.co-row span{{color:#e6edf3;font-family:'IBM Plex Mono',monospace}}
#cascade-overlay .co-close{{margin-top:12px;width:100%;background:#2d1e00;border:1px solid #fbbf24;color:#fbbf24;padding:6px;border-radius:6px;cursor:pointer;font-size:11px}}
#mm{{position:absolute;bottom:10px;right:12px;width:165px;height:92px;background:#161b22;border:1px solid #30363d;border-radius:6px;z-index:20;overflow:hidden}}
</style></head><body>
<div id="wrap">
  <canvas id="c"></canvas>
  <div id="ctrl">
    <button class="btn" id="btnSim" onclick="toggleSim()">⟳ Force OFF</button>
    <button class="btn" onclick="doAutoLayout()">⊞ Auto Layout</button>
    <button class="btn" onclick="zoomIn()">＋</button>
    <button class="btn" onclick="zoomOut()">－</button>
    <button class="btn" onclick="resetView()">⌖ Reset</button>
    <button class="btn" onclick="clearHL()">✕ Clear</button>
    <button class="btn" id="btnCA" onclick="toggleCA()">▶ Collapse All</button>
  </div>
  <div id="search-box">
    <input id="search-input" type="text" placeholder="🔍 Search label / name / type…" oninput="onSearch(this.value)">
    <span id="search-count"></span>
    <button class="btn" onclick="clearSearch()">✕</button>
  </div>
  <div id="hzf"><div class="title">Filter Hazard</div><div id="hzchips"></div></div>
  <div id="legend">
    <div class="leg"><div class="leg-dot" style="background:#3fb950"></div>Pass</div>
    <div class="leg"><div class="leg-dot" style="background:#f85149"></div>Exceeds</div>
    <div class="leg"><div class="leg-dot" style="background:#444"></div>No data</div>
    <div class="leg"><div class="leg-dot" style="background:#fbbf24"></div>Flash=shared sync</div>
    <div class="leg"><div class="leg-dot" style="background:#58a6ff;border-radius:2px"></div>Rebalanced alloc</div>
    <div class="leg">🔒 Locked &nbsp;✏️ Right-click=edit</div>
  </div>
  <div id="popup">
    <h3 id="p-lbl"></h3><div class="psub" id="p-path"></div>
    <div class="prow"><span class="pk">Allocated (T)</span><span class="pv" id="p-alloc"></span></div>
    <div class="prow"><span class="pk">Achieved (A)</span><span class="pv" id="p-ach"></span></div>
    <div class="prow"><span class="pk">Status</span><span class="pv" id="p-status"></span></div>
    <div class="phint">🔗 Path to root highlighted · Right-click = full edit + info</div>
  </div>
  <div id="ctx-menu">
    <div class="cm-head"><h4 id="cm-title">Node</h4><button class="cm-close" onclick="hideCtxMenu()">✕</button></div>
    <div class="cm-body" id="cm-body"></div>
  </div>
  <div id="cascade-overlay">
    <h4>🔄 Shared Sync — Updated Nodes</h4>
    <div id="co-content"></div>
    <button class="co-close" onclick="document.getElementById('cascade-overlay').style.display='none'">✕ Close</button>
  </div>
  <div id="info">🖱 Drag · Scroll=zoom · Pan=drag bg · Left=highlight path · Right-click=edit+info · ▼=collapse</div>
  <div id="mm"><canvas id="mmc" width="165" height="92"></canvas></div>
</div>
<script>
const NODES={nj};const EDGES={ej};const HZ={hj};
const FLASH_IDS=new Set({fj});
const BOX_W=154,BOX_H=68,GATE_R=12;
const TC={{HZ:{{fill:"#3d1a00",stroke:"#f97316",text:"#f97316"}},SF:{{fill:"#0d2136",stroke:"#58a6ff",text:"#58a6ff"}},FF:{{fill:"#0d2b14",stroke:"#3fb950",text:"#3fb950"}},IF:{{fill:"#1e0d36",stroke:"#d2a8ff",text:"#d2a8ff"}},AND:{{fill:"#2d1a3d",stroke:"#e040fb",text:"#e040fb"}}}};
const SC={{pass:"#3fb950",fail:"#f85149",na:"#2d333b"}};
const wrap=document.getElementById('wrap'),c=document.getElementById('c'),ctx=c.getContext('2d');
const mmc=document.getElementById('mmc'),mmx=mmc.getContext('2d');
function resize(){{c.width=wrap.clientWidth;c.height=wrap.clientHeight;}}
resize();window.addEventListener('resize',()=>{{resize();draw();}});
let scale=1,panX=0,panY=50,dragging=null,dragOffX=0,dragOffY=0,dragMoved=false;
let isPan=false,lastMX=0,lastMY=0;
let hlSet=new Set(),searchSet=new Set(),searchPathSet=new Set(),searchQuery="";
let collapsed=new Set(),activeHz=new Set(HZ.map(h=>h.id));
let simRunning=false,allCA=false,popup=null,ctxNode=null;
let flashTimer=0,flashAlpha=0;
const pos={{}};
function doAutoLayout(){{
  const hzIds=HZ.map(h=>h.id);const byLvl={{}};
  NODES.forEach(n=>{{(byLvl[n.depth]||(byLvl[n.depth]=[])).push(n.id);}});
  const hzSp=720;
  Object.entries(byLvl).forEach(([lvl,ids])=>{{
    const byHz={{}};ids.forEach(id=>{{const n=NODES.find(x=>x.id===id);(byHz[n?.hz||'']||(byHz[n?.hz||'']=[])).push(id);}});
    Object.entries(byHz).forEach(([hz,hids])=>{{
      const hzX=(hzIds.indexOf(hz))*hzSp-(hzIds.length-1)*hzSp/2;
      const tw=hids.length*(BOX_W+22)-22;
      hids.forEach((id,i)=>{{pos[id]={{x:hzX+i*(BOX_W+22)-tw/2+BOX_W/2,y:parseInt(lvl)*(BOX_H+95)+85,vx:0,vy:0}};}});
    }});
  }});
}}
doAutoLayout();panX=wrap.clientWidth/2;
if(FLASH_IDS.size>0){{flashTimer=90;flashAlpha=1;}}
function simulate(){{
  if(!simRunning)return;
  const ids=Object.keys(pos);
  for(let i=0;i<ids.length;i++)for(let j=i+1;j<ids.length;j++){{
    const a=pos[ids[i]],b=pos[ids[j]];const dx=b.x-a.x,dy=b.y-a.y,dist=Math.sqrt(dx*dx+dy*dy)||1;
    const f=3800/(dist*dist);a.vx-=dx/dist*f;a.vy-=dy/dist*f;b.vx+=dx/dist*f;b.vy+=dy/dist*f;
  }}
  EDGES.forEach(e=>{{const a=pos[e.from],b=pos[e.to];if(!a||!b)return;
    const dx=b.x-a.x,dy=b.y-a.y,dist=Math.sqrt(dx*dx+dy*dy)||1;const f=(dist-145)*0.04;
    a.vx+=dx/dist*f;a.vy+=dy/dist*f;b.vx-=dx/dist*f;b.vy-=dy/dist*f;
  }});
  ids.forEach(id=>{{const n=NODES.find(x=>x.id===id);if(!n)return;
    pos[id].vy+=n.depth*0.015;pos[id].vx*=0.75;pos[id].vy*=0.75;
    if(id!==dragging){{pos[id].x+=pos[id].vx;pos[id].y+=pos[id].vy;}}
  }});
}}
function isVisible(nid){{
  const n=NODES.find(x=>x.id===nid);if(!n)return false;
  if(n.type==='HZ')return activeHz.has(n.id);if(!activeHz.has(n.hz))return false;
  let cur=n.parent;const seen=new Set();
  while(cur&&!seen.has(cur)){{seen.add(cur);if(collapsed.has(cur))return false;const p=NODES.find(x=>x.id===cur);if(!p)break;cur=p.parent;}}
  return true;
}}
function draw(){{
  if(flashTimer>0){{flashTimer--;flashAlpha=Math.max(0,(flashTimer/90)*(0.7+Math.sin(flashTimer*0.25)*0.3));}}
  ctx.clearRect(0,0,c.width,c.height);ctx.save();ctx.translate(panX,panY);ctx.scale(scale,scale);
  EDGES.forEach(e=>{{if(!isVisible(e.from)||!isVisible(e.to))return;
    const bHL=hlSet.size===0||(hlSet.has(e.from)&&hlSet.has(e.to));
    const bSP=searchPathSet.size===0||(searchPathSet.has(e.from)&&searchPathSet.has(e.to));
    drawEdge(pos[e.from],pos[e.to],e.gate,!bHL||!bSP);
  }});
  NODES.forEach(n=>{{if(!isVisible(n.id))return;
    const inHL=hlSet.size===0||hlSet.has(n.id);const inSP=searchPathSet.size===0||searchPathSet.has(n.id);
    drawNode(n,pos[n.id],!inHL||!inSP,popup===n.id,searchQuery!==''&&searchSet.has(n.id),FLASH_IDS.has(n.id)&&flashTimer>0);
  }});
  ctx.restore();drawMinimap();
}}
function rr(ctx,x,y,w,h,r){{ctx.beginPath();ctx.moveTo(x+r,y);ctx.lineTo(x+w-r,y);ctx.arcTo(x+w,y,x+w,y+r,r);ctx.lineTo(x+w,y+h-r);ctx.arcTo(x+w,y+h,x+w-r,y+h,r);ctx.lineTo(x+r,y+h);ctx.arcTo(x,y+h,x,y+h-r,r);ctx.lineTo(x,y+r);ctx.arcTo(x,y,x+r,y,r);ctx.closePath();}}
function drawEdge(a,b,gate,faded){{
  if(!a||!b)return;const gc=gate==='AND'?'#e040fb':'#58a6ff';
  ctx.save();ctx.globalAlpha=faded?0.05:0.88;
  ctx.beginPath();ctx.moveTo(a.x,a.y+BOX_H/2);ctx.bezierCurveTo(a.x,a.y+BOX_H/2+36,b.x,b.y-BOX_H/2-36,b.x,b.y-BOX_H/2-5);
  ctx.strokeStyle=faded?'#2d333b':gc;ctx.lineWidth=faded?0.8:1.4;ctx.stroke();
  if(!faded){{
    const ex=b.x,ey=b.y-BOX_H/2-2;
    ctx.beginPath();ctx.moveTo(ex,ey);ctx.lineTo(ex-8*Math.cos(-.4),ey-8*Math.sin(-.4));ctx.lineTo(ex-8*Math.cos(.4),ey-8*Math.sin(.4));ctx.closePath();ctx.fillStyle=gc;ctx.fill();
    const gx=(a.x+b.x)/2,gy=(a.y+BOX_H/2+b.y-BOX_H/2)/2;
    if(gate==='AND'){{ctx.fillStyle='#2d1a3d';ctx.strokeStyle='#e040fb';ctx.lineWidth=1.4;rr(ctx,gx-GATE_R,gy-GATE_R,GATE_R*2,GATE_R*2,4);ctx.fill();ctx.stroke();ctx.fillStyle='#e040fb';ctx.font='bold 7px monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('AND',gx,gy);}}
    else{{ctx.fillStyle='#0d2136';ctx.strokeStyle='#58a6ff';ctx.lineWidth=1.4;ctx.beginPath();ctx.arc(gx,gy,GATE_R,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle='#58a6ff';ctx.font='bold 7px monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText('OR',gx,gy);}}
  }}
  ctx.restore();
}}
function drawNode(n,p,faded,isHL,isMatch,isFlash){{
  if(!p)return;const col=TC[n.type]||TC.SF,scol=SC[n.status]||'#2d333b';
  const x=p.x-BOX_W/2,y=p.y-BOX_H/2;const hasKids=EDGES.some(e=>e.from===n.id),isColl=collapsed.has(n.id);
  ctx.save();ctx.globalAlpha=faded?0.07:1;
  if(isFlash){{ctx.save();ctx.strokeStyle=`rgba(251,191,36,${{flashAlpha}})`;ctx.lineWidth=4;ctx.shadowColor='#fbbf24';ctx.shadowBlur=20*flashAlpha;rr(ctx,x-5,y-5,BOX_W+10,BOX_H+10,13);ctx.stroke();ctx.restore();}}
  if(isMatch){{ctx.save();ctx.strokeStyle='#f97316';ctx.lineWidth=3;ctx.shadowColor='#f97316';ctx.shadowBlur=14;rr(ctx,x-4,y-4,BOX_W+8,BOX_H+8,12);ctx.stroke();ctx.restore();}}
  if(n.rebalanced&&!faded){{ctx.save();ctx.strokeStyle='#58a6ff';ctx.lineWidth=1.8;ctx.setLineDash([4,3]);rr(ctx,x-3,y-3,BOX_W+6,BOX_H+6,11);ctx.stroke();ctx.setLineDash([]);ctx.restore();}}
  if(n.status!=='na'&&!faded){{ctx.shadowColor=scol;ctx.shadowBlur=isHL?14:5;}}
  ctx.fillStyle='rgba(0,0,0,.42)';rr(ctx,x+3,y+3,BOX_W,BOX_H,9);ctx.fill();
  ctx.fillStyle=col.fill;rr(ctx,x,y,BOX_W,BOX_H,9);ctx.fill();
  ctx.strokeStyle=isFlash?`rgba(251,191,36,${{Math.min(1,flashAlpha+.2)}})`:n.status!=='na'?scol:col.stroke;
  ctx.lineWidth=isHL?2.6:1.7;ctx.shadowBlur=0;rr(ctx,x,y,BOX_W,BOX_H,9);ctx.stroke();
  ctx.fillStyle=col.stroke;ctx.globalAlpha=(faded?.07:1)*.17;rr(ctx,x,y,BOX_W,18,9);ctx.fill();ctx.fillRect(x,y+9,BOX_W,9);
  ctx.globalAlpha=faded?.07:1;
  ctx.fillStyle=col.text;ctx.font='bold 7.5px monospace';ctx.textAlign='center';ctx.textBaseline='top';ctx.fillText(n.type,p.x,y+4);
  if(n.locked){{ctx.font='9px sans-serif';ctx.fillStyle='#fbbf24';ctx.textAlign='left';ctx.fillText('🔒',x+4,y+3);}}
  ctx.fillStyle=col.text;ctx.font='bold 12px monospace';ctx.textBaseline='middle';ctx.fillText(n.label.substring(0,16),p.x,p.y-9);
  ctx.fillStyle=col.text;ctx.font='7.5px sans-serif';ctx.globalAlpha=(faded?.07:1)*.65;ctx.fillText(n.name.substring(0,22),p.x,p.y+5);
  ctx.globalAlpha=faded?.07:1;ctx.font='6.8px monospace';
  ctx.fillStyle=n.status==='pass'?'#3fb950':n.status==='fail'?'#f85149':'#555';
  ctx.textAlign='left';ctx.fillText('A:'+n.achieved,x+5,y+BOX_H-8);
  ctx.fillStyle=n.rebalanced?'#58a6ff':'#8b949e';ctx.textAlign='right';ctx.fillText('T:'+n.alloc,x+BOX_W-5,y+BOX_H-8);
  if(hasKids){{const bx=p.x+BOX_W/2-15,by=y+3,br=7;ctx.fillStyle=isColl?col.stroke:'#21262d';ctx.beginPath();ctx.arc(bx,by+br,br,0,Math.PI*2);ctx.fill();ctx.strokeStyle=col.stroke;ctx.lineWidth=1;ctx.stroke();ctx.fillStyle=isColl?'#0d1117':col.text;ctx.font='bold 9px monospace';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(isColl?'▶':'▼',bx,by+br);}}
  ctx.restore();
}}
function drawMinimap(){{
  mmx.clearRect(0,0,165,92);mmx.fillStyle='#161b22';mmx.fillRect(0,0,165,92);
  const vis=NODES.filter(n=>isVisible(n.id)&&pos[n.id]);if(!vis.length)return;
  const allX=vis.map(n=>pos[n.id].x),allY=vis.map(n=>pos[n.id].y);
  const minX=Math.min(...allX)-80,maxX=Math.max(...allX)+80,minY=Math.min(...allY)-40,maxY=Math.max(...allY)+40;
  const s=Math.min(156/Math.max(maxX-minX,1),84/Math.max(maxY-minY,1))*.85;
  vis.forEach(n=>{{const p=pos[n.id];mmx.fillStyle=SC[n.status]||'#333';mmx.globalAlpha=.75;mmx.fillRect((p.x-minX)*s+3-4,(p.y-minY)*s+3-2,10,6);}});
  mmx.globalAlpha=1;mmx.strokeStyle='#f97316';mmx.lineWidth=1.5;
  mmx.strokeRect((-panX/scale-minX)*s+3,(-panY/scale-minY)*s+3,Math.min((c.width/scale)*s,156),Math.min((c.height/scale)*s,86));
}}
function walkUp(nid){{const s=new Set();let cur=nid;const seen=new Set();while(cur&&!seen.has(cur)){{seen.add(cur);s.add(cur);const nd=NODES.find(x=>x.id===cur);if(!nd)break;cur=nd.parent;}}return s;}}
function walkPath(nid){{const s=walkUp(nid);(function down(id){{s.add(id);EDGES.filter(e=>e.from===id).forEach(e=>down(e.to));}})( nid);return s;}}
function onSearch(q){{
  searchQuery=q.trim().toLowerCase();searchSet.clear();searchPathSet.clear();
  if(!searchQuery){{document.getElementById('search-count').textContent='';return;}}
  NODES.forEach(n=>{{if(n.label.toLowerCase().includes(searchQuery)||n.name.toLowerCase().includes(searchQuery)||n.type.toLowerCase().includes(searchQuery)||n.desc.toLowerCase().includes(searchQuery))searchSet.add(n.id);}});
  searchSet.forEach(id=>walkUp(id).forEach(pid=>searchPathSet.add(pid)));
  document.getElementById('search-count').textContent=searchSet.size+' match'+(searchSet.size!==1?'es':'');
  const first=[...searchSet][0];if(first&&pos[first]){{panX=c.width/2-pos[first].x*scale;panY=c.height/3-pos[first].y*scale;}}
}}
function clearSearch(){{document.getElementById('search-input').value='';onSearch('');}}
function toWorld(cx,cy){{return{{x:(cx-panX)/scale,y:(cy-panY)/scale}};}}
function nodeAt(wx,wy){{for(let i=NODES.length-1;i>=0;i--){{const n=NODES[i];if(!isVisible(n.id)||!pos[n.id])continue;const p=pos[n.id];if(wx>=p.x-BOX_W/2&&wx<=p.x+BOX_W/2&&wy>=p.y-BOX_H/2&&wy<=p.y+BOX_H/2)return n;}}return null;}}
function collapseHit(n,wx,wy){{const bx=pos[n.id].x+BOX_W/2-15,by=pos[n.id].y-BOX_H/2+10;return Math.sqrt((wx-bx)**2+(wy-by)**2)<9;}}
c.addEventListener('mousedown',ev=>{{
  if(ev.button===2)return;hideCtxMenu();
  const rect=c.getBoundingClientRect();const cx=ev.clientX-rect.left,cy=ev.clientY-rect.top;const{{x:wx,y:wy}}=toWorld(cx,cy);
  const n=nodeAt(wx,wy);
  if(n){{if(EDGES.some(e=>e.from===n.id)&&collapseHit(n,wx,wy)){{collapsed.has(n.id)?collapsed.delete(n.id):collapsed.add(n.id);ev.preventDefault();return;}}dragging=n.id;dragMoved=false;dragOffX=wx-pos[n.id].x;dragOffY=wy-pos[n.id].y;c.classList.add('grabbing');}}
  else{{isPan=true;lastMX=cx;lastMY=cy;c.classList.add('grabbing');popup=null;document.getElementById('popup').style.display='none';}}
  ev.preventDefault();
}});
window.addEventListener('mousemove',ev=>{{
  const rect=c.getBoundingClientRect();const cx=ev.clientX-rect.left,cy=ev.clientY-rect.top;const{{x:wx,y:wy}}=toWorld(cx,cy);
  if(dragging){{const dx=wx-dragOffX-pos[dragging].x,dy=wy-dragOffY-pos[dragging].y;if(Math.abs(dx)>2||Math.abs(dy)>2)dragMoved=true;pos[dragging].x=wx-dragOffX;pos[dragging].y=wy-dragOffY;pos[dragging].vx=0;pos[dragging].vy=0;}}
  else if(isPan){{panX+=cx-lastMX;panY+=cy-lastMY;lastMX=cx;lastMY=cy;}}
}});
window.addEventListener('mouseup',ev=>{{
  if(dragging&&!dragMoved){{const rect=c.getBoundingClientRect();const{{x:wx,y:wy}}=toWorld(ev.clientX-rect.left,ev.clientY-rect.top);const n=nodeAt(wx,wy);if(n&&n.id===dragging)handleLeftClick(n,ev.clientX-rect.left,ev.clientY-rect.top);}}
  dragging=null;isPan=false;dragMoved=false;c.classList.remove('grabbing');
}});
c.addEventListener('contextmenu',ev=>{{ev.preventDefault();const rect=c.getBoundingClientRect();const{{x:wx,y:wy}}=toWorld(ev.clientX-rect.left,ev.clientY-rect.top);const n=nodeAt(wx,wy);if(n)showCtxMenu(n,ev.clientX-rect.left,ev.clientY-rect.top);else hideCtxMenu();}});
c.addEventListener('wheel',ev=>{{ev.preventDefault();const rect=c.getBoundingClientRect();const cx=ev.clientX-rect.left,cy=ev.clientY-rect.top;const delta=ev.deltaY<0?1.12:.89;const ns=Math.max(.08,Math.min(5,scale*delta));panX=cx-(cx-panX)*(ns/scale);panY=cy-(cy-panY)*(ns/scale);scale=ns;}},{{passive:false}});
window.addEventListener('click',()=>hideCtxMenu());
function handleLeftClick(n,sx,sy){{
  hlSet=walkPath(n.id);popup=n.id;
  const pp=document.getElementById('popup');
  document.getElementById('p-lbl').textContent=n.label;document.getElementById('p-lbl').style.color=TC[n.type]?.text||'#e6edf3';
  document.getElementById('p-path').textContent='🔗 '+n.chain;
  document.getElementById('p-alloc').textContent=n.alloc+' /yr';
  const ae=document.getElementById('p-ach');ae.textContent=n.achieved+' /yr';ae.className='pv '+(n.status==='pass'?'pass':n.status==='fail'?'fail':'');
  const se=document.getElementById('p-status');se.textContent=n.status==='pass'?'✅ PASS':n.status==='fail'?'❌ EXCEEDS':'⬜ No data';se.className='pv '+(n.status==='pass'?'pass':n.status==='fail'?'fail':'');
  pp.style.display='block';let tx=sx+16,ty=sy-10;if(tx+300>c.width-10)tx=sx-305;if(ty+200>c.height-10)ty=sy-205;pp.style.left=tx+'px';pp.style.top=ty+'px';
}}
function showCtxMenu(n,sx,sy){{
  ctxNode=n;document.getElementById('cm-title').textContent='✏️ '+n.label+' — '+n.type;
  const alcCol=n.status==='pass'?'pass':n.status==='fail'?'fail':'';
  const sibRows=n.siblings.length?n.siblings.map(s=>`<div class="cm-sib"><span>${{s.label}}</span><span>T=${{s.alloc}}</span><span>A=${{s.achieved}}</span></div>`).join(''):'<div style="color:#555;font-size:10px">None</div>';
  let defM=1.0,defE=-3;
  if(n.ach_raw!==null&&n.ach_raw!==undefined&&n.ach_raw>0){{defE=Math.floor(Math.log10(n.ach_raw));defM=+(n.ach_raw/(10**defE)).toFixed(2);}}
  document.getElementById('cm-body').innerHTML=`
    <div class="cm-sec first">Identity</div>
    <div class="cm-row"><span class="cm-key">Name</span><span class="cm-val">${{n.name}}</span></div>
    <div class="cm-row"><span class="cm-key">Description</span><span class="cm-val" style="font-size:9px;color:#8b949e;font-family:sans-serif">${{n.desc||'–'}}</span></div>
    <div class="cm-row"><span class="cm-key">Gate</span><span class="cm-val" style="color:${{n.gate==='AND'?'#e040fb':'#58a6ff'}}">${{n.gate}}</span></div>
    <div class="cm-sec">Path to Root</div>
    <div class="cm-chain">🔗 ${{n.chain}}</div>
    <div class="cm-sec">Allocation & Status</div>
    <div class="cm-row"><span class="cm-key">Allocated (T)</span><span class="cm-val ${{n.rebalanced?'rebal':''}}">${{n.alloc}} /yr</span></div>
    <div class="cm-row"><span class="cm-key">Achieved (A)</span><span class="cm-val ${{alcCol}}">${{n.achieved}} /yr</span></div>
    <div class="cm-row"><span class="cm-key">Status</span><span class="cm-val ${{alcCol}}">${{n.status==='pass'?'✅ PASS':n.status==='fail'?'❌ EXCEEDS':'⬜ No data'}}</span></div>
    ${{n.rebalanced?'<div class="cm-row"><span></span><span class="cm-val rebal">🔵 T was manually rebalanced</span></div>':''}}
    ${{n.locked?'<div class="cm-row"><span></span><span class="cm-val warn">🔒 Locked (excluded from rebalance)</span></div>':''}}
    <div class="cm-sec">Siblings (${{n.siblings.length}})</div>
    ${{sibRows}}
    <div class="cm-sec">✏️ Edit Achieved Value</div>
    <div class="cm-el">Mantissa × 10^Exponent (e.g. 3.5E-06)</div>
    <div class="cm-er"><label>Mantissa</label><input type="number" id="edit-mant" value="${{defM}}" min="0" max="9.99" step="0.01" oninput="updatePreview()"></div>
    <div class="cm-er"><label>Exponent</label><input type="number" id="edit-exp" value="${{defE}}" min="-20" max="0" step="1" oninput="updatePreview()"></div>
    <div class="cm-preview" id="edit-preview">Preview: —</div>
    <div class="cm-btns">
      <button class="cm-btn save" onclick="submitEdit()">💾 Apply</button>
      <button class="cm-btn clr" onclick="clearEdit()">✕ Clear</button>
    </div>
    <div class="cm-sec">Node Type Info</div>
    <div class="cm-info">${{n.type_info}}</div>
    <div class="cm-sec">Gate Logic</div>
    <div class="cm-info">${{n.gate_info}}</div>
  `;
  updatePreview();
  const menu=document.getElementById('ctx-menu');menu.style.display='block';
  let mx=sx+10,my=Math.max(10,sy-40);
  setTimeout(()=>{{if(mx+menu.offsetWidth>c.width-10)mx=Math.max(10,sx-menu.offsetWidth-10);if(my+menu.offsetHeight>c.height-10)my=Math.max(10,c.height-menu.offsetHeight-10);menu.style.left=mx+'px';menu.style.top=my+'px';}},0);
}}
function updatePreview(){{
  const m=parseFloat(document.getElementById('edit-mant')?.value||'0');
  const e=parseInt(document.getElementById('edit-exp')?.value||'-3');
  const p=document.getElementById('edit-preview');
  if(p)p.textContent='Preview: '+(m>0?(m*(10**e)).toExponential(3)+' /yr':'—');
}}
function submitEdit(){{
  if(!ctxNode)return;
  const m=parseFloat(document.getElementById('edit-mant')?.value||'0');
  const e=parseInt(document.getElementById('edit-exp')?.value||'-3');
  if(m<=0){{alert('Mantissa must be > 0');return;}}
  window.parent.postMessage({{type:'fta_edit',nid:ctxNode.id,value:m*(10**e)}},'*');
  hideCtxMenu();
}}
function clearEdit(){{if(!ctxNode)return;window.parent.postMessage({{type:'fta_edit',nid:ctxNode.id,value:null}},'*');hideCtxMenu();}}
function hideCtxMenu(){{document.getElementById('ctx-menu').style.display='none';ctxNode=null;}}
function clearHL(){{hlSet.clear();popup=null;document.getElementById('popup').style.display='none';}}
function zoomIn(){{scale=Math.min(5,scale*1.2);}}function zoomOut(){{scale=Math.max(.08,scale/1.2);}}
function resetView(){{scale=1;panX=c.width/2;panY=50;clearHL();doAutoLayout();}}
function toggleSim(){{simRunning=!simRunning;const b=document.getElementById('btnSim');b.textContent=simRunning?'⟳ Force ON':'⟳ Force OFF';b.classList.toggle('active',simRunning);}}
function toggleCA(){{allCA=!allCA;if(allCA)NODES.forEach(n=>{{if(EDGES.some(e=>e.from===n.id))collapsed.add(n.id);}});else collapsed.clear();document.getElementById('btnCA').textContent=allCA?'▼ Expand All':'▶ Collapse All';}}
HZ.forEach(h=>{{const d=document.createElement('div');d.className='hchip';d.innerHTML=`<div class="hdot" style="background:${{h.color}}"></div>${{h.id}} <span style="color:#8b949e;font-size:10px">${{h.target}}</span>`;let on=true;d.addEventListener('click',()=>{{on=!on;d.classList.toggle('off',!on);on?activeHz.add(h.id):activeHz.delete(h.id);}});document.getElementById('hzchips').appendChild(d);}});
window.addEventListener('message',ev=>{{
  if(ev.data&&ev.data.type==='fta_edit'){{
    try{{const el=window.parent.document.querySelector('input[aria-label="viz_edit_relay"]');if(el){{const s=Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype,'value').set;s.call(el,JSON.stringify(ev.data));el.dispatchEvent(new Event('input',{{bubbles:true}}));}}}}catch(e){{}}
  }}
}});
function loop(){{simulate();draw();requestAnimationFrame(loop);}}loop();
</script></body></html>"""
with st.sidebar:
    st.markdown("### ⚙️ FTA Builder")

    # ── AUTOSAVE STATUS ───────────────────────────────────────
    # Hidden restore relay (catches postMessage from localStorage bridge)
    restore_raw = st.text_input("__fta_restore__", value="", key="fta_restore_input",
                                 label_visibility="collapsed")
    slots_raw   = st.text_input("__fta_slots__", value="", key="fta_slots_input",
                                 label_visibility="collapsed")

    # Process restore (only once per session, flag prevents loop)
    if restore_raw and not st.session_state.get("_restored", False):
        if deserialize_state(restore_raw):
            st.session_state["_restored"] = True
            st.rerun()

    # Parse slot list from localStorage
    try:
        saved_slots = json.loads(slots_raw) if slots_raw else []
    except Exception:
        saved_slots = []

    # Autosave status bar
    has_data = bool(st.session_state.nodes)
    saved_at_str = ""
    try:
        cur = json.loads(serialize_state())
        saved_at_str = cur.get("saved_at","")[:19].replace("T"," ") + " UTC" if has_data else ""
    except Exception:
        pass

    if has_data:
        st.markdown(f"""<div style="background:#0a1f0d;border:1px solid #3fb950;border-radius:6px;
            padding:6px 12px;margin-bottom:8px;font-size:0.72rem;color:#3fb950">
            💾 Auto-saved to browser &nbsp;·&nbsp; {saved_at_str}
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div style="background:#1c2128;border:1px solid #30363d;border-radius:6px;
            padding:6px 12px;margin-bottom:8px;font-size:0.72rem;color:#8b949e">
            💾 Auto-save active (browser storage)
        </div>""", unsafe_allow_html=True)

    # Named project slots
    with st.expander("📁 Project Slots (save/load named versions)", expanded=False):
        slot_name_in = st.text_input("Slot name", value="MyProject_v1", key="slot_name_input",
                                      placeholder="e.g. Reactor_FTA_draft1")
        sc1, sc2 = st.columns(2)
        if sc1.button("💾 Save slot", use_container_width=True):
            # Send save command to bridge via a hidden component
            st.session_state["_slot_cmd"] = json.dumps({
                "cmd": "save", "name": slot_name_in, "data": serialize_state()
            })
            st.rerun()
        if sc2.button("📂 Load slot", use_container_width=True):
            st.session_state["_slot_cmd"] = json.dumps({"cmd": "load", "name": slot_name_in})
            st.rerun()

        if saved_slots:
            st.markdown("**Saved slots:**")
            for sname in saved_slots:
                sa, sb = st.columns([3, 1])
                sa.markdown(f"<span style='font-family:monospace;font-size:0.78rem'>📄 {sname}</span>", unsafe_allow_html=True)
                if sb.button("🗑", key=f"del_slot_{sname}", help=f"Delete slot {sname}"):
                    st.session_state["_slot_cmd"] = json.dumps({"cmd": "delete", "name": sname})
                    st.rerun()
        else:
            st.caption("No saved slots yet.")

        st.caption("Slots are stored in **this browser only**. Use JSON export below for cross-device backup.")

    st.markdown("---")
    nodes      = st.session_state.nodes
    hz_targets = st.session_state.hz_targets

    # ── STEP 1: HAZARDS ───────────────────────────────────────
    with st.expander("⚠️ Step 1 — Hazards", expanded=True):
        for hz in [n for n in nodes.values() if n["type"]=="HZ"]:
            hid = hz["id"]; cur = hz_targets.get(hid,1e-8)
            ev  = int(math.floor(math.log10(cur))) if cur>0 else -8
            mv  = round(cur/(10**ev),2)
            ca,cb = st.columns([3,1])
            with ca:
                e2 = st.number_input(f"E",value=ev,min_value=-20,max_value=-1,step=1,key=f"hze_{hid}",label_visibility="collapsed")
                m2 = st.number_input(f"M",value=mv,min_value=0.1,max_value=9.9,step=0.1,format="%.1f",key=f"hzm_{hid}",label_visibility="collapsed")
                new_t = m2*(10**e2); hz_targets[hid] = new_t
                st.caption(f"**{hz['label']}** {hz['name'][:20]}: `{new_t:.2E}`")
            with cb:
                if len([n for n in nodes.values() if n["type"]=="HZ"])>1:
                    if st.button("🗑",key=f"delhz_{hid}",help="Delete this hazard"):
                        for d in [hid]+descendants(nodes,hid): nodes.pop(d,None)
                        hz_targets.pop(hid,None); st.session_state.alloc_override.clear(); st.session_state.rebalanced_nodes.clear(); st.rerun()

        with st.form("add_hz_form",clear_on_submit=True):
            nhl = st.text_input("Label",value=f"HZ{st.session_state.next_id:02d}",key="ahl")
            nhn = st.text_input("Name",value="New Hazard Event",key="ahn")
            nhd = st.text_input("Desc",value="",key="ahd")
            c_e = st.number_input("Target exp",value=-8,min_value=-20,max_value=-1,step=1)
            c_m = st.number_input("Target mant",value=1.0,min_value=0.1,max_value=9.9,step=0.1,format="%.1f")
            if st.form_submit_button("➕ Add Hazard",use_container_width=True):
                nid = f"HZ{st.session_state.next_id}"
                nodes[nid]={"id":nid,"label":nhl,"name":nhn,"type":"HZ","parent":None,"gate":"–","desc":nhd,"achieved":None,"locked":False}
                hz_targets[nid]=c_m*(10**c_e); st.session_state.next_id+=1; st.rerun()

    # ── STEPS 2-5: SF / AND / FF / IF ─────────────────────────
    step_map = [("SF","Step 2 — System Failures (SF)"),("AND","Step 3 — AND / Combined Faults"),("FF","Step 4 — Following Failures (FF)"),("IF","Step 5 — Initiating Failures (IF)")]
    for node_type, step_label in step_map:
        with st.expander(f"🔷 {step_label}", expanded=False):
            allowed = VALID_PARENTS.get(node_type,[])
            valid_pars = {k:f"{v.get('label',k)} [{v['type']}]" for k,v in nodes.items() if v["type"] in allowed}
            if not valid_pars:
                st.caption(f"⚠️ Add {'HZ' if node_type=='SF' else 'SF/AND' if node_type in ('FF','AND') else 'FF'} nodes first.")
                continue
            with st.form(f"add_{node_type}_form",clear_on_submit=True):
                par_key  = st.selectbox("Parent",list(valid_pars.keys()),format_func=lambda k:valid_pars[k])
                lbl_val  = st.text_input("Label",value=f"{node_type}{st.session_state.next_id:02d}")
                name_val = st.text_input("Name",value=f"New {node_type}")
                desc_val = st.text_input("Desc",value="")
                gate_val = "AND" if node_type=="AND" else st.selectbox("Gate",["OR","AND"],key=f"g_{node_type}")
                if st.form_submit_button(f"➕ Add {node_type}",use_container_width=True):
                    nid=f"N{st.session_state.next_id}"
                    nodes[nid]={"id":nid,"label":lbl_val,"name":name_val,"type":node_type,"parent":par_key,"gate":gate_val,"desc":desc_val,"achieved":None,"locked":False}
                    st.session_state.next_id+=1
                    # Immediately recalculate allocations
                    st.session_state.alloc_override.clear()
                    st.session_state.rebalanced_nodes.clear()
                    st.rerun()

    st.markdown("---")
    # Delete
    with st.expander("🗑️ Delete Node"):
        del_opts={k:f"{v.get('label',k)} ({v['type']})" for k,v in nodes.items() if v["type"]!="HZ"}
        if del_opts:
            del_k=st.selectbox("Node",list(del_opts.keys()),format_func=lambda k:del_opts[k],key="delk")
            nd=len(descendants(nodes,del_k))
            if nd: st.warning(f"Also removes {nd} child(ren).")
            if st.button("🗑️ Delete",use_container_width=True):
                for d in [del_k]+descendants(nodes,del_k):
                    nodes.pop(d,None); st.session_state.alloc_override.pop(d,None); st.session_state.rebalanced_nodes.discard(d)
                st.session_state.alloc_override.clear(); st.session_state.rebalanced_nodes.clear(); st.rerun()
        else:
            st.caption("No deletable nodes.")

    st.markdown("---")
    if st.button("🔄 Reset Everything",use_container_width=True):
        for k in list(default_state().keys()): st.session_state.pop(k,None)
        st.rerun()

# ═══════════════════════════════════════════════════════════════
# COMPUTE
# ═══════════════════════════════════════════════════════════════
nodes      = st.session_state.nodes
hz_targets = st.session_state.hz_targets
# Pure top-down allocation — never influenced by achieved values
alloc, rebal_set = compute_alloc(nodes, hz_targets)
# Pure bottom-up rollup — completely separate from allocation
rolled     = rollup_achieved(nodes)
order      = bfs_order(nodes)
hz_list    = [n for n in nodes.values() if n["type"]=="HZ"]
n_sf = sum(1 for v in nodes.values() if v["type"]=="SF")
n_ff = sum(1 for v in nodes.values() if v["type"] in ("FF","AND"))
n_if = sum(1 for v in nodes.values() if v["type"]=="IF")
all_if   = [n for n in nodes.values() if n["type"]=="IF"]
if_done  = sum(1 for n in all_if if n.get("achieved") is not None)

# ═══════════════════════════════════════════════════════════════
# HEADER
st.markdown("""<div class="fta-header">
  <h1>🌳 FTA Risk Allocator v9</h1>
  <p>Auto-calculated budgets (OR: T÷n · AND: T^(1/n)) · Shared failure worst-case sync · Lock &amp; manual rebalance · Search · Right-click edit</p>
</div>""", unsafe_allow_html=True)

# Metric bar
st.markdown("<br>",unsafe_allow_html=True)
st.markdown("<br>",unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════
tab_viz,tab_vals,tab_table,tab_edit,tab_export = st.tabs([
    "🌳 Tree","✏️ Values & Rebalancing","📋 Table","🔧 Edit","📥 Export"
])

# ── AUTOSAVE BRIDGE (hidden, runs every render) ────────────────
slot_cmd = st.session_state.pop("_slot_cmd", None)
state_payload = serialize_state() if st.session_state.nodes else json.dumps({})

# Hidden bridge iframe: saves to localStorage, restores on first load
components.html(autosave_bridge(state_payload, saved_slots), height=0, scrolling=False)
# Hidden relay: catches postMessages from bridge and relays to text inputs
components.html(RELAY_COMPONENT, height=0, scrolling=False)

# Process slot commands (save/load/delete via bridge)
if slot_cmd:
    try:
        cmd_obj = json.loads(slot_cmd)
        cmd = cmd_obj.get("cmd")
        name = cmd_obj.get("name","")
        if cmd == "save":
            slot_js = f"""<script>
              window.parent.postMessage({{type:'fta_slot_save',name:{json.dumps(name)},data:{json.dumps(cmd_obj.get('data',''))}}},'*');
            </script>"""
            components.html(slot_js, height=0)
            st.toast(f"💾 Saved to slot '{name}'", icon="💾")
        elif cmd == "load":
            slot_js = f"""<script>
              window.parent.postMessage({{type:'fta_slot_load',name:{json.dumps(name)}}},'*');
            </script>"""
            components.html(slot_js, height=0)
            st.toast(f"📂 Loading slot '{name}'…", icon="📂")
        elif cmd == "delete":
            slot_js = f"""<script>
              window.parent.postMessage({{type:'fta_slot_delete',name:{json.dumps(name)}}},'*');
            </script>"""
            components.html(slot_js, height=0)
            st.toast(f"🗑 Deleted slot '{name}'", icon="🗑")
    except Exception:
        pass

# ── TAB 1: VIZ ───────────────────────────────────────────────
with tab_viz:
    if not nodes:
        st.info("👈 Start by adding a Hazard in the sidebar, then add SF → FF → IF nodes.")
    else:
        st.caption("**Left-click** = highlight path to root · **Right-click** = full info + inline edit · **▼** = collapse · **Search** = highlight + show path to root")

        # Flash IDs from last cascade
        flash_ids = set(st.session_state.get("flash_ids", []))

        # Cascade summary popup (shown above viz when shared cascade happened)
        cascade_summary = st.session_state.get("cascade_summary", [])
        if cascade_summary:
            with st.expander(f"🔄 Shared Cascade Summary — {len(cascade_summary)} node(s) updated", expanded=True):
                cols_cs = st.columns(4)
                cols_cs[0].markdown("**Label**"); cols_cs[1].markdown("**Old value**")
                cols_cs[2].markdown("**New value**"); cols_cs[3].markdown("**Reason**")
                for entry in cascade_summary:
                    cols_cs[0].markdown(f"`{entry['label']}`")
                    cols_cs[1].markdown(f"`{fmt(entry.get('old'))}`")
                    cols_cs[2].markdown(f"`{fmt(entry.get('new'))}`")
                    cols_cs[3].markdown(f"<span style='color:#8b949e;font-size:0.75rem'>{entry.get('reason','')}</span>", unsafe_allow_html=True)
                if st.button("✕ Dismiss", key="dismiss_cascade"):
                    st.session_state["cascade_summary"] = []
                    st.session_state["flash_ids"] = []
                    st.rerun()

        # Hidden relay for right-click inline edit postMessage
        relay_val = st.text_input("viz_relay", value="", key="viz_edit_relay",
                                   label_visibility="collapsed")
        if relay_val:
            try:
                msg = json.loads(relay_val)
                if msg.get("type") == "fta_edit":
                    edit_nid = msg["nid"]
                    edit_val = msg.get("value")
                    if edit_nid in nodes:
                        if edit_val is None:
                            nodes[edit_nid]["achieved"] = None
                            st.session_state.alloc_override.pop(edit_nid, None)
                            st.session_state.rebalanced_nodes.discard(edit_nid)
                            st.session_state["change_log"] = []
                            st.session_state["flash_ids"] = []
                            st.session_state["cascade_summary"] = []
                        else:
                            nodes[edit_nid]["achieved"] = edit_val
                            new_log, synced_ids = apply_shared_sync(nodes, edit_nid, edit_val)
                            st.session_state["change_log"] = new_log
                            st.session_state["flash_ids"] = list(set(synced_ids))
                            if len(synced_ids) > 1:
                                st.session_state["cascade_summary"] = new_log
                                st.toast(f"🔄 Shared sync: updated {len(synced_ids)} nodes with worst-case value", icon="🔄")
                            else:
                                st.session_state["cascade_summary"] = []
                        # Clear relay
                        st.session_state["viz_edit_relay"] = ""
                        st.rerun()
            except Exception:
                pass

        components.html(build_viz(nodes, alloc, rolled, hz_targets, rebal_set, flash_ids), height=730, scrolling=False)
        # Clear flash after render
        if flash_ids:
            st.session_state["flash_ids"] = []

# ── TAB 2: VALUES & REBALANCING ──────────────────────────────
with tab_vals:
    st.markdown("### ✏️ Achieved Values & Sibling Rebalancing")

    # Search/filter for this tab
    search_tab = st.text_input("🔍 Filter nodes", placeholder="Type label, name or type…", key="tab_search")

    # Change log display
    log = st.session_state.get("change_log",[])
    if log:
        with st.expander(f"📋 Change Log — last cascade affected {len(log)} node(s)", expanded=True):
            st.markdown('<div class="change-log"><div class="cl-title">🔄 Cascade Changes</div>', unsafe_allow_html=True)
            for entry in log[-20:]:
                old_s = fmt(entry.get("old")) if entry.get("old") is not None else "–"
                new_s = fmt(entry.get("new")) if entry.get("new") is not None else "–"
                reason = entry.get("reason","")
                st.markdown(f'<div class="cl-row">→ <span>{entry["label"]}</span>: {old_s} → {new_s} &nbsp;<span style="color:#555;font-size:0.7rem">({reason})</span></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            if st.button("🗑 Clear log"):
                st.session_state["change_log"] = []; st.rerun()

    st.markdown("""<div style="background:#161b22;border:1px solid #30363d;border-left:3px solid #58a6ff;border-radius:6px;padding:10px 16px;margin-bottom:10px;font-size:0.82rem;line-height:1.7"><b style="color:#58a6ff">How these columns work:</b><br>▶ <b>Allocated (T)</b> = auto top-down from HZ target (OR: T÷n · AND: T<sup>1/n</sup>) — <em>never</em> affected by achieved values.<br>▶ <b>Achieved (edit)</b> = failure rate you enter manually. Shared-label nodes auto-sync to worst-case (max).<br>▶ <b>Rolled-up (A)</b> = bottom-up result (OR: Σ · AND: Π). <span style="color:#3fb950">●</span> green = within budget · <span style="color:#f85149">●</span> red = exceeds.<br><span style="color:#8b949e;font-size:0.72rem">⚠ Shared failures: each instance keeps its <em>own</em> allocated budget — budgets may differ because each node’s parent has a different number of siblings.</span></div>""", unsafe_allow_html=True)

    for hz in hz_list:
        hid=hz["id"]
        st.markdown(f"#### 🔷 {hz.get('label',hid)} — {hz.get('name','')}")

        subtree_ids=[i for i in order if i in ([hid]+descendants(nodes,hid)) and i!=hid and i in nodes]
        if search_tab:
            q=search_tab.lower()
            subtree_ids=[i for i in subtree_ids if q in nodes[i].get("label","").lower() or q in nodes[i].get("name","").lower() or q in nodes[i]["type"].lower()]

        hdr=st.columns([0.35,1.1,2.0,0.6,1.8,2.0,1.6])
        for h,t in zip(hdr,["🔒","Label","Name","Type","Allocated (T)","Achieved (edit)","Rolled-up (A)"]):
            h.markdown(f"<span style='font-size:0.62rem;color:#8b949e;text-transform:uppercase'>{t}</span>",unsafe_allow_html=True)

        changed_nid=None; changed_val=None
        for nid in subtree_ids:
            if nid not in nodes: continue
            n=nodes[nid]; t=n["type"]
            alc=alloc.get(nid); ach=n.get("achieved"); roll=rolled.get(nid)
            depth=get_depth(nodes,nid)
            indent="　"*depth
            is_rebal=nid in rebal_set; is_locked=n.get("locked",False)
            same_label_nodes=nodes_by_label(nodes,n.get("label",""))
            is_shared=len(same_label_nodes)>1

            cols=st.columns([0.35,1.1,2.0,0.6,1.8,2.0,1.6])
            new_lock=cols[0].checkbox("",value=is_locked,key=f"lk_{nid}",label_visibility="collapsed",help="Lock: exclude from rebalancing")
            if new_lock!=is_locked:
                nodes[nid]["locked"]=new_lock; st.rerun()

            tags=""
            if is_shared:
                # Build tooltip showing all peer allocations for this shared label
                peer_allocs = [(p, fmt(alloc.get(p))) for p in same_label_nodes if p != nid]
                peer_info = " | ".join(f"{nodes[p].get('label','?')} T={a}" for p,a in peer_allocs) if peer_allocs else ""
                allocs_differ = len(set(fmt(alloc.get(p)) for p in same_label_nodes)) > 1
                warn_icon = " ⚠" if allocs_differ else ""
                tip_shared = _tip("🔄shared" + warn_icon,
                    f"<strong>Shared failure</strong> \u2014 all nodes with label <code>{n.get('label','')}</code> "
                    f"share the worst-case achieved value.<br>"
                    + (f"<strong style='color:#fbbf24'>Note: budgets differ across instances</strong> \u2014 "
                       f"each instance has its own parent with a different number of siblings.<br>" if allocs_differ else "")
                    + (f"Other instances: {peer_info}" if peer_info else "")
                )
                tags += tip_shared
            if is_rebal:  tags+='<span class="tag tag-rebal">🔵rebal</span>'
            if is_locked: tags+='<span class="tag tag-lock">🔒</span>'
            cols[1].markdown(f"`{indent}{n.get('label',nid)}`{tags}",unsafe_allow_html=True)
            cols[2].markdown(f"<span style='font-size:0.77rem;color:#c9d1d9'>{n.get('name','')}</span>",unsafe_allow_html=True)
            cols[3].markdown(f"<span class='badge b-{t}'>{t}</span>",unsafe_allow_html=True)

            _alc_cls = "col-alloc rebal" if is_rebal else "col-alloc"
            cols[4].markdown(f"<span class='{_alc_cls}'>{fmt(alc)}</span>", unsafe_allow_html=True)

            with cols[5]:
                s1,s2,s3=st.columns([1.8,1.2,0.8])
                if ach is not None and ach>0:
                    de=int(math.floor(math.log10(ach))); dm=round(ach/(10**de),2)
                else:
                    de=-3; dm=1.0
                m_in=s1.number_input("M",value=dm,min_value=0.0,max_value=9.99,step=0.01,format="%.2f",key=f"am_{nid}",label_visibility="collapsed")
                e_in=s2.number_input("E",value=de,min_value=-20,max_value=0,step=1,key=f"ae_{nid}",label_visibility="collapsed")
                clr=s3.button("✕",key=f"ac_{nid}",help="Clear")
                if clr:
                    nodes[nid]["achieved"]=None
                    for d in [nid]+descendants(nodes,nid):
                        st.session_state.alloc_override.pop(d,None); st.session_state.rebalanced_nodes.discard(d)
                    st.session_state["change_log"]=[]
                    st.rerun()
                else:
                    new_val=m_in*(10**e_in) if m_in>0 else None
                    if new_val!=ach:
                        changed_nid=nid; changed_val=new_val

            # Rolled-up: colour by comparison with allocated
            roll_col = "#3fb950" if (roll is not None and alc and roll <= alc) else ("#f85149" if (roll is not None and alc and roll > alc) else "#8b949e")
            cols[6].markdown(f"<span style='font-family:monospace;font-size:0.77rem;color:{roll_col}'>{fmt(roll)}</span>",unsafe_allow_html=True)

        if changed_nid is not None and changed_val is not None:
            nodes[changed_nid]["achieved"] = changed_val
            new_log, synced_ids = apply_shared_sync(nodes, changed_nid, changed_val)
            st.session_state["change_log"] = new_log
            st.session_state["flash_ids"] = list(set(synced_ids))
            if len(synced_ids) > 1:
                other_labels = [nodes[s].get("label","") for s in synced_ids if s != changed_nid]
                st.session_state["cascade_summary"] = new_log
                st.toast(f"🔄 Shared sync: worst-case propagated to {', '.join(set(other_labels))}", icon="🔄")
            else:
                st.session_state["cascade_summary"] = []
            st.rerun()

        st.markdown("---")

# ── TAB 3: TABLE ─────────────────────────────────────────────
with tab_table:
    st.markdown("#### Full Allocation Table")
    search_tbl=st.text_input("🔍 Filter",placeholder="Label / name / type…",key="tbl_search")
    rows_html=""
    for nid in order:
        if nid not in nodes: continue
        n=nodes[nid]; t=n["type"]; vc=VC.get(t,"sf")
        alc=alloc.get(nid); roll=rolled.get(nid)
        par=nodes[n["parent"]]["label"] if n.get("parent") and n["parent"] in nodes else "–"
        lvl=get_depth(nodes,nid); indent=lvl*16
        is_rebal=nid in rebal_set; is_locked=n.get("locked",False)
        is_shared=len(nodes_by_label(nodes,n.get("label","")))>1

        if search_tbl:
            q=search_tbl.lower()
            if not(q in n.get("label","").lower() or q in n.get("name","").lower() or q in t.lower()): continue

        tags=""
        if is_shared: tags+='<span class="tag tag-sync">🔄</span>'
        if is_rebal:  tags+='<span class="tag tag-rebal">🔵</span>'
        if is_locked: tags+='<span class="tag tag-lock">🔒</span>'
        roll_col="#3fb950" if (roll is not None and alc and roll<=alc) else ("#f85149" if (roll is not None and alc and roll>alc) else "#8b949e")
        rows_html+=f"""<tr>
          <td style="padding-left:{indent+8}px"><span class="badge b-{t}">{t}</span></td>
          <td style="padding-left:{indent+8}px"><span class="vm c-{vc}">{n.get('label',nid)}</span>{tags}</td>
          <td style="color:#c9d1d9;font-size:0.78rem">{n.get('name','')}</td>
          <td style="color:#8b949e;font-size:0.73rem;font-family:monospace">{par}</td>
          <td><span class="{'g-and' if n['gate']=='AND' else 'g-or' if n['gate']=='OR' else ''}">{n['gate']}</span></td>
          <td><span class="{'col-alloc rebal' if is_rebal else 'col-alloc'}">{fmt(alc)}</span></td>
          <td style="font-family:monospace;font-size:0.78rem;color:{roll_col}">{fmt(roll)}</td>
        </tr>"""
    if rows_html:
        st.markdown(f"""<table class="tree-table"><thead><tr>
          <th>Type</th><th>Label</th><th>Name</th><th>Parent</th><th>Gate</th>
          <th style='color:#58a6ff'>Allocated (T)</th><th>Achieved / Rolled-up (A)</th>
        </tr></thead><tbody>{rows_html}</tbody></table>""",unsafe_allow_html=True)
    else:
        st.info("No nodes match the filter." if search_tbl else "No nodes yet. Add nodes in the sidebar.")

# ── TAB 4: EDIT ──────────────────────────────────────────────
with tab_edit:
    st.markdown("#### 🔧 Edit Node")
    if nodes:
        cs,cf=st.columns([1,2])
        with cs:
            search_edit=st.text_input("🔍 Search",placeholder="Filter…",key="edit_search")
            edit_opts={k:f"{v.get('label',k)} ({v['type']})" for k,v in nodes.items()
                       if not search_edit or search_edit.lower() in v.get("label","").lower() or search_edit.lower() in v.get("name","").lower()}
            ek=st.selectbox("Node",list(edit_opts.keys()),format_func=lambda k:edit_opts[k],key="ek") if edit_opts else None
        with cf:
            if ek and ek in nodes:
                n=nodes[ek]; t=n["type"]
                el=st.text_input("Label",value=n.get("label",""),key="el2")
                en=st.text_input("Name",value=n.get("name",""),key="en3")
                ed=st.text_area("Desc",value=n.get("desc",""),key="ed3",height=60)
                if t not in ("HZ","IF"):
                    go=["OR","AND"]; cg=n.get("gate","OR")
                    eg=st.selectbox("Gate",go,index=go.index(cg) if cg in go else 0,key="eg3")
                else:
                    eg=n.get("gate","–"); st.info(f"Gate `{eg}` fixed for {t}")
                if t!="HZ":
                    ap=VALID_PARENTS.get(t,[]); vp={k:f"{v.get('label',k)} [{v['type']}]" for k,v in nodes.items() if v["type"] in ap and k!=ek and k not in descendants(nodes,ek)}
                    cpk=n.get("parent",""); pk=list(vp.keys()); pi=pk.index(cpk) if cpk in pk else 0
                    ep=st.selectbox("Parent",pk,index=pi,format_func=lambda k:vp[k],key="ep3") if pk else None
                else:
                    ep=None
                if st.button("💾 Save",use_container_width=True,key="sv3"):
                    nodes[ek].update({"label":el,"name":en,"desc":ed,"gate":eg})
                    if ep: nodes[ek]["parent"]=ep
                    # Recalculate after label change (may affect shared sync)
                    st.session_state.alloc_override.clear(); st.session_state.rebalanced_nodes.clear()
                    st.success("✅ Saved!"); st.rerun()
        st.markdown("---")
        rows_all=[]
        for nid in order:
            if nid not in nodes: continue
            n=nodes[nid]; par=nodes[n["parent"]]["label"] if n.get("parent") and n["parent"] in nodes else "–"
            rows_all.append({"Label":n.get("label",""),"Name":n.get("name",""),"Type":n["type"],
                "Gate":n["gate"],"Parent":par,"Depth":get_depth(nodes,nid),"Locked":n.get("locked",False),
                "Allocated":fmt(alloc.get(nid)),"Achieved":fmt(rolled.get(nid))})
        st.dataframe(pd.DataFrame(rows_all),use_container_width=True,hide_index=True)
    else:
        st.info("No nodes yet.")

# ── TAB 5: EXPORT ─────────────────────────────────────────────
with tab_export:
    cx,cj=st.columns(2)
    with cx:
        st.markdown("**Excel (.xlsx)**")
        def build_excel():
            wb=Workbook(); ws=wb.active; ws.title="FTA_v9"
            def fl(h): return PatternFill("solid",start_color=h,fgColor=h)
            def af(bold=False,color="000000",sz=10): return Font(name="Arial",bold=bold,color=color,size=sz)
            def tb(): s=Side(style="thin",color="BFBFBF"); return Border(left=s,right=s,top=s,bottom=s)
            for i,w in enumerate([6,10,12,24,30,12,10,16,16,10,10,8,8],1):
                ws.column_dimensions[get_column_letter(i)].width=w
            ws.merge_cells("A1:M1")
            ws["A1"]="FAULT TREE ANALYSIS v8 – Multi-Hazard | Auto-Calc | Rebalanced | Achieved Rollup"
            ws["A1"].font=af(bold=True,sz=12,color="FFFFFF"); ws["A1"].fill=fl("1F3864")
            ws["A1"].alignment=Alignment(horizontal="center",vertical="center"); ws.row_dimensions[1].height=28
            hdrs=["Type","Label","Name","Description","Parent","Gate","Allocated","Achieved","Rolled-up","Margin","Status","Locked","Shared"]
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
                is_shared=len(nodes_by_label(nodes,n.get("label","")))>1
                r=i+3
                vals=[t,n.get("label",""),n.get("name",""),n.get("desc",""),par,n["gate"],alc,n.get("achieved"),rol,margin,status,"YES" if n.get("locked") else "","YES" if is_shared else ""]
                for c2,v in enumerate(vals,1):
                    cell=ws.cell(row=r,column=c2,value=v); cell.border=tb()
                    cell.alignment=Alignment(horizontal="left" if c2 in(2,3,4) else "center",vertical="center",wrap_text=(c2 in(3,4)))
                    if c2==1:
                        cell.fill=fl(BG.get(t,"1F3864")); cell.font=af(bold=True,sz=9,color="FFFFFF")
                        cell.alignment=Alignment(horizontal="center",vertical="center")
                    elif c2 in(7,8,9):
                        cell.number_format="0.00E+00"
                        fc="375623" if status=="PASS" else ("C00000" if status=="EXCEEDS" else "000000")
                        cell.font=af(bold=(c2==9),sz=10,color=fc if c2==9 else "000000")
                    elif c2==10:
                        cell.number_format="0.000"
                        cell.font=af(sz=9,color="375623" if (margin and margin<=1) else ("C00000" if (margin and margin>1) else "595959"))
                    elif c2==11:
                        cell.font=af(bold=True,sz=9,color="375623" if status=="PASS" else ("C00000" if status=="EXCEEDS" else "595959"))
                    else:
                        cell.fill=fl(LT.get(t,"F2F2F2") if c2 in(2,6) else "FFFFFF"); cell.font=af(sz=9)
                ws.row_dimensions[r].height=16
            out=io.BytesIO(); wb.save(out); out.seek(0); return out.getvalue()
        if nodes:
            st.download_button("⬇️ Excel",data=build_excel(),file_name="FTA_v8.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
        else:
            st.info("Add nodes first.")
    with cj:
        st.markdown("**JSON – Save / Load**")
        if nodes:
            payload=json.dumps({"nodes":st.session_state.nodes,"hz_targets":st.session_state.hz_targets,
                "alloc_override":st.session_state.alloc_override,
                "rebalanced_nodes":list(st.session_state.rebalanced_nodes)},indent=2)
            st.download_button("⬇️ JSON",data=payload,file_name="fta_v8.json",mime="application/json",use_container_width=True)
        up=st.file_uploader("Load JSON",type="json",key="jup8")
        if up:
            try:
                d=json.load(up)
                if "nodes" in d and "hz_targets" in d:
                    st.session_state.nodes=d["nodes"]; st.session_state.hz_targets=d["hz_targets"]
                    st.session_state.alloc_override=d.get("alloc_override",{})
                    st.session_state.rebalanced_nodes=set(d.get("rebalanced_nodes",[]))
                    st.session_state.change_log=[]
                    st.success("✅ Loaded!"); st.rerun()
            except Exception as e: st.error(str(e))
    st.markdown("---")
    st.markdown("""
#### Logic Reference
| Gate | Allocation | Rollup | Rebalancing |
|------|-----------|--------|-------------|
| **OR** | Child = Parent ÷ n | Parent = Σ children | Remaining = Parent − fixed − Σlocked → free siblings share equally |
| **AND** | Child = Parent^(1/n) | Parent = Π children | x^n = Parent ÷ (fixed × Πlocked) → each free sibling gets x |

**Shared label rule:** All nodes with the same label are treated as duplicates. Editing one propagates the worst-case value to all, and each triggers its own sibling rebalance in its respective hazard tree.
    """)
