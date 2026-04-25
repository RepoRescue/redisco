"""
Step 7: bug hunt — 主动找漏洞。

探测：
1. 边界 Unicode：emoji + 非 ASCII path 作为 indexed Attribute
2. 重复 save / state leak（同一对象多次 save）
3. 并发：两个线程并发 incr Counter（验证 INCR 原子性）
4. 跨版本接缝：测 redisco 在 Py3.13 下用 ListField(int) 存大量数据时的 typecast
"""
import os, sys, tempfile, threading, time
import redislite
RDB_DIR = tempfile.mkdtemp(prefix="redisco-bug-")
_r = redislite.Redis(os.path.join(RDB_DIR, "redis.db"))
SOCK = _r.socket_file

import redisco
redisco.connection_setup(unix_socket_path=SOCK, db=0, decode_responses=True)
from redisco import models, containers
redisco.get_client().flushdb()

class Item(models.Model):
    name = models.Attribute(required=True, indexed=True)
    hits = models.Counter()


findings = []

# ---- (1) Unicode 边界：emoji + CJK + RTL ----
try:
    weird = Item(name="🐍 Niña العربية 漢字")
    assert weird.save()
    found = Item.objects.filter(name="🐍 Niña العربية 漢字").first()
    if found is None or found.id != weird.id:
        findings.append("BUG: indexed lookup fails for mixed-Unicode name")
    else:
        print("(1) Unicode boundary: OK")
except Exception as e:
    findings.append(f"BUG: Unicode boundary raised {type(e).__name__}: {e}")

# ---- (2) 重复 save（state leak / dup index）----
try:
    a = Item(name="dup-test")
    a.save()
    a.save()
    a.save()  # 三次 save 同一对象
    matches = list(Item.objects.filter(name="dup-test"))
    if len(matches) != 1:
        findings.append(f"BUG: repeated save creates {len(matches)} entries (expect 1)")
    else:
        print(f"(2) Repeated save: OK ({len(matches)} match)")
except Exception as e:
    findings.append(f"BUG: repeated save raised: {e}")

# ---- (3) 并发 Counter incr（INCR 是 redis 原子，应可靠）----
try:
    c = Item(name="counter-test")
    c.save()
    N_THREADS = 8
    PER_THREAD = 50
    def worker():
        x = Item.objects.filter(name="counter-test").first()
        for _ in range(PER_THREAD):
            x.incr("hits")
    ths = [threading.Thread(target=worker) for _ in range(N_THREADS)]
    for t in ths: t.start()
    for t in ths: t.join()
    c2 = Item.objects.filter(name="counter-test").first()
    expected = N_THREADS * PER_THREAD
    if c2.hits != expected:
        findings.append(f"BUG: concurrent incr lost updates (got {c2.hits}, expect {expected})")
    else:
        print(f"(3) Concurrent incr: OK ({c2.hits} == {expected})")
except Exception as e:
    findings.append(f"BUG: concurrent incr raised: {type(e).__name__}: {e}")

# ---- (4) ListField(int) 大量数据 typecast（之前 patch 改过 typecast_iter→list(filter(...))）----
class Bag(models.Model):
    label = models.Attribute(required=True)
    nums = models.ListField(int)

try:
    big = Bag(label="big", nums=list(range(500)))
    big.save()
    bag2 = Bag.objects.get_by_id(big.id)
    if list(bag2.nums) != list(range(500)):
        findings.append(f"BUG: ListField(int) round-trip lost data: len={len(list(bag2.nums))}")
    else:
        print("(4) ListField(int) 500-element round trip: OK")
except Exception as e:
    findings.append(f"BUG: ListField(int) raised: {type(e).__name__}: {e}")

# ---- (5) Empty filter / nonexistent indexed lookup ----
try:
    nothing = Item.objects.filter(name="does-not-exist").first()
    if nothing is not None:
        findings.append("BUG: filter on missing key returns non-None")
    else:
        print("(5) Missing-key filter: OK")
except Exception as e:
    findings.append(f"BUG: missing-key filter raised: {e}")

# ---- (6) Hash MutableMapping protocol（patch 改过 collections.abc.MutableMapping）----
try:
    h = containers.Hash("hash-mm-test")
    h["a"] = "1"
    h["b"] = "2"
    keys = sorted(list(h.keys()))
    if keys != ["a", "b"]:
        findings.append(f"BUG: Hash.keys() = {keys}")
    if len(h) != 2:
        findings.append(f"BUG: len(h) = {len(h)}")
    del h["a"]
    if "a" in h:
        findings.append("BUG: del did not remove key")
    print(f"(6) Hash MutableMapping: OK (len after del = {len(h)})")
except Exception as e:
    findings.append(f"BUG: Hash MutableMapping raised: {type(e).__name__}: {e}")

print("---")
if findings:
    print(f"FOUND {len(findings)} bug(s):")
    for f in findings:
        print(f"  - {f}")
    sys.exit(1)
else:
    print("No bugs found in 6 probes.")
