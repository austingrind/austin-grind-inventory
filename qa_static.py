"""
Austin Grind Inventory App — Static QA Checker
Run: python3 qa_static.py [path/to/index.html]
Checks the HTML file for known issues before deploying.
"""
import sys, re, json

path = sys.argv[1] if len(sys.argv) > 1 else 'AustinGrind_Inventory.html'
try:
    with open(path, encoding='utf-8') as f:
        html = f.read()
except FileNotFoundError:
    print(f"ERROR: File not found: {path}")
    sys.exit(1)

passed = []
failed = []
warned = []

def ok(msg):   passed.append(msg)
def fail(msg): failed.append(msg)
def warn(msg): warned.append(msg)

script_start = html.find('<script>')
script = html[script_start:] if script_start >= 0 else ''

# ── 1. Structure ─────────────────────────────────────────────────────────────
if '<html' in html and '</html>' in html:     ok("Valid HTML envelope")
else:                                          fail("Missing <html> tags")

if '<script>' in html and '</script>' in html: ok("Script block present")
else:                                          fail("Missing <script> block")

# ── 2. JS Syntax — nested backtick template literals ─────────────────────────
nested = re.findall(r'\$\{[^}]*`[^`]*`[^}]*\}', script)
if not nested:
    ok("No nested backtick template literals")
else:
    for n in nested:
        fail(f"Nested backtick: {n[:80]}")

# ── 3. Required constants ─────────────────────────────────────────────────────
for const in ['SUPABASE_URL', 'SUPABASE_KEY', 'PINS', 'MANAGER_TABS', 'INVENTORY', 'SKU_MAP']:
    if f'const {const}' in script:
        ok(f"Constant defined: {const}")
    else:
        fail(f"Missing constant: {const}")

# ── 4. Supabase placeholders ──────────────────────────────────────────────────
import re as _re
url_decl = (_re.search(r"const SUPABASE_URL\s*=\s*'([^']+)'", html) or [None,None])[1] or ''
key_decl = (_re.search(r"const SUPABASE_KEY\s*=\s*'([^']+)'", html) or [None,None])[1] or ''
if url_decl == 'YOUR_SUPABASE_URL':
    warn("SUPABASE_URL is still the placeholder — app will run in offline mode")
else:
    ok(f"SUPABASE_URL configured: {url_decl[:40]}")
if key_decl == 'YOUR_SUPABASE_ANON_KEY':
    warn("SUPABASE_KEY is still the placeholder — app will run in offline mode")
else:
    ok(f"SUPABASE_KEY configured (eyJ…{key_decl[-6:]})")

# ── 5. Required functions ─────────────────────────────────────────────────────
required_fns = [
    'submitPin', 'checkSession', 'applyRoleUI', 'signOut',
    'initApp', 'showTab', 'renderCount', 'renderPO', 'renderSummary',
    'loadHistory', 'loadCatalog', 'renderCatalog', 'saveCounts',
    'setCount', 'handleKey', 'sanitizeCount', 'pasteSanitize',
    'orderCases', 'buildUsageCols', 'loadRecentUsage',
    'moveItem', 'printCatalog', 'saveItem', 'toggleActive',
    'updateBadge', 'toast', 'supaHeaders',
]
for fn in required_fns:
    if f'function {fn}' in script:
        ok(f"Function defined: {fn}")
    else:
        fail(f"MISSING function: {fn}")

# ── 6. Required DOM element IDs ───────────────────────────────────────────────
required_ids = [
    'login-screen', 'pin-input', 'pin-err',
    'hdr-week', 'signout-btn', 'sync-badge', 'toast',
    'tab-bar', 'panel-count', 'panel-po', 'panel-summary',
    'panel-history', 'panel-catalog',
    'week-date', 'staff-name', 'search', 'count-list',
    'po-list', 'summary-body', 'history-body', 'catalog-body',
    'hist-from', 'hist-to', 'hist-item',
    'modal-overlay', 'm-name', 'm-cat', 'm-vendor', 'm-par',
    'm-uc', 'm-pack', 'm-price', 'm-active',
    'cnt-done', 'cnt-total',
]
for eid in required_ids:
    if f'id="{eid}"' in html:
        ok(f"Element ID present: #{eid}")
    else:
        fail(f"MISSING element ID: #{eid}")

# ── 7. Broken element references ─────────────────────────────────────────────
# Check that every getElementById in JS has a matching id in HTML
# Exclude dynamic references (those ending with - or + which are concatenated)
js_refs = set(re.findall(r"getElementById\(['\"](\w[\w-]*)['\"]", script))
js_refs = {r for r in js_refs if not r.endswith('-')}  # skip dynamic concat like 'panel-' + tab
for ref in sorted(js_refs):
    if f'id="{ref}"' in html or f"id='{ref}'" in html:
        pass  # ok - don't clutter output with 40 passing checks
    else:
        fail(f"getElementById('{ref}') has no matching element in HTML")

# ── 8. Manager tabs defined correctly ────────────────────────────────────────
if "MANAGER_TABS = new Set(['history', 'catalog'])" in html:
    ok("MANAGER_TABS correctly defined")
else:
    warn("MANAGER_TABS definition may have changed — verify history/catalog are protected")

# ── 9. Logo present ───────────────────────────────────────────────────────────
if 'data:image/png;base64' in html:
    ok("Logo image embedded")
else:
    warn("No embedded logo found")

# ── 10. INVENTORY array valid JSON ────────────────────────────────────────────
try:
    inv_start = html.find('const INVENTORY = [')
    inv_end   = html.find('];', inv_start) + 2
    arr = json.loads(html[inv_start:inv_end].replace('const INVENTORY = ', '').rstrip(';'))
    ok(f"INVENTORY array valid JSON: {len(arr)} items")
    if len(arr) < 190:
        warn(f"INVENTORY has only {len(arr)} items — expected ~202")
except Exception as e:
    fail(f"INVENTORY array JSON parse error: {e}")

# ── 11. SKU_MAP present and valid ─────────────────────────────────────────────
try:
    sku_start = html.find('const SKU_MAP = {')
    sku_end   = html.find('};', sku_start) + 2
    sku_obj   = json.loads(html[sku_start:sku_end].replace('const SKU_MAP = ', '').rstrip(';'))
    ok(f"SKU_MAP valid: {len(sku_obj)} entries")
    if len(sku_obj) < 190:
        warn(f"SKU_MAP has only {len(sku_obj)} entries — expected ~202")
except Exception as e:
    fail(f"SKU_MAP JSON parse error: {e}")

# ── 12. No stale element references ──────────────────────────────────────────
stale_refs = ['hdr-sub', 'hdr-title']
for ref in stale_refs:
    if f"getElementById('{ref}')" in html or f'getElementById("{ref}")' in html:
        fail(f"Stale element reference: getElementById('{ref}') — element was renamed")
    else:
        ok(f"No stale reference to #{ref}")

# ── 13. Auth flow integrity ───────────────────────────────────────────────────
if 'btoa(pin)' in html and 'atob(savedHash)' in html:
    ok("PIN hashing uses btoa/atob consistently")
else:
    fail("PIN hash/unhash functions missing or mismatched")

if "localStorage.setItem('ag_role'" in html and "localStorage.getItem('ag_role')" in html:
    ok("Role persistence uses localStorage correctly")
else:
    fail("Role persistence localStorage keys mismatched")

# ── 14. Tab guard present ─────────────────────────────────────────────────────
if 'MANAGER_TABS.has(tab)' in html:
    ok("Manager tab access guard present in showTab")
else:
    fail("showTab is missing the MANAGER_TABS access guard")

# ── 15. Print title rows set ─────────────────────────────────────────────────
if 'printTitleRows' in html or 'PrintTitleRows' in html:
    ok("Print title rows configured")
else:
    warn("printTitleRows not set — headers may not repeat when printing")


# ── Filter / sort checks ──────────────────────────────────────────────────────
filter_ids = ['cnt-cat-filter','cnt-sort','cnt-uncounted','cnt-low',
              'hist-filter-bar','hist-cat-filter','hist-vendor-filter',
              'hist-sort','hist-shortage-only','cat-cat-filter','cat-sort']
for fid in filter_ids:
    if f'id="{fid}"' in html:
        ok(f"Filter element present: #{fid}")
    else:
        fail(f"MISSING filter element: #{fid}")

filter_fns = ['populateCountCatFilter','populateHistoryFilters',
              'applyHistoryFilters','renderHistoryTable']
for fn in filter_fns:
    if f'function {fn}' in script:
        ok(f"Filter function defined: {fn}()")
    else:
        fail(f"MISSING filter function: {fn}()")

if "sortBy === 'shortage'" in script and "sortBy === 'name'" in script:
    ok("Count sort options implemented")
else:
    fail("Count sort options missing")

if "sortBy2 === 'par_desc'" in script and "sortBy2 === 'vendor'" in script:
    ok("Catalog sort options implemented")
else:
    fail("Catalog sort options missing")

if "sortBy === 'week_asc'" in script and "sortBy === 'shortage'" in script:
    ok("History sort options implemented")
else:
    fail("History sort options missing")



# ── Print / Orders / Count tab checks ────────────────────────────────────────
# Print: panel-po must not be hidden
import re as _re2
print_block = (_re2.search(r'@media print\s*\{.*?\}', html, _re2.DOTALL) or [''])[0]
if 'panel-po' in print_block and 'panel-po { display: block' not in html:
    fail("Print: #panel-po is hidden during print — Orders tab will show blank page")
else:
    ok("Print: Orders tab (panel-po) shows correctly when printing")

# Load saved counts
if 'function loadSavedCounts' in script:
    ok("loadSavedCounts() defined — week change loads DB counts")
else:
    fail("MISSING: loadSavedCounts() — changing week date won't load saved counts")

if 'loadSavedCounts(w)' in script:
    ok("onWeekChange calls loadSavedCounts")
else:
    fail("onWeekChange does not call loadSavedCounts")

# Tab rename
if 'Update Inventory' in html:
    ok('Count tab correctly labelled "Update Inventory"')
else:
    fail('Count tab still labelled "Count" — should be "Update Inventory"')

# Vendor filter on Orders
for eid in ['po-vendor-filter', 'po-filter-count']:
    if f'id="{eid}"' in html:
        ok(f"Orders filter element present: #{eid}")
    else:
        fail(f"MISSING Orders filter element: #{eid}")

if 'filteredByV' in script:
    ok("renderPO vendor filter logic present")
else:
    fail("renderPO missing vendor filter logic")

# ── Node.js syntax check ──────────────────────────────────────────────────────
import subprocess, tempfile, os as _os
script_block = html[html.find('<script>')+8:html.rfind('</script>')]
with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as tf:
    tf.write(script_block)
    tf_path = tf.name
try:
    result = subprocess.run(['node', '--check', tf_path],
                          capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        ok("JavaScript parses cleanly (node --check)")
    else:
        fail(f"JavaScript syntax error: {result.stderr.strip()[:120]}")
except FileNotFoundError:
    warn("node not available — skipping JS syntax check")
except Exception as e:
    warn(f"JS syntax check failed: {e}")
finally:
    _os.unlink(tf_path)

# ── Report ────────────────────────────────────────────────────────────────────
total = len(passed) + len(failed) + len(warned)
print(f"\n{'='*60}")
print(f"  Austin Grind QA — Static Analysis")
print(f"  File: {path}")
print(f"{'='*60}")
print(f"\n  ✅ PASSED:  {len(passed)}")
print(f"  ❌ FAILED:  {len(failed)}")
print(f"  ⚠️  WARNED:  {len(warned)}")
print(f"  Total checks: {total}")

if failed:
    print(f"\n{'─'*60}")
    print("  FAILURES (must fix before deploying):")
    for f in failed:
        print(f"    ❌ {f}")

if warned:
    print(f"\n{'─'*60}")
    print("  WARNINGS (review before deploying):")
    for w in warned:
        print(f"    ⚠️  {w}")

if not failed:
    print(f"\n  🚀 READY TO DEPLOY")
else:
    print(f"\n  🔴 DO NOT DEPLOY — fix failures first")

print(f"{'='*60}\n")
sys.exit(0 if not failed else 1)
