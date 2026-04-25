"""
scenario_validate (Path B) — 一个完全独立的下游开发者场景。

业务：用户登录历史 store。
- User Model：username（唯一）、email（indexed）、login_count（Counter）、failed_attempts（Counter）
- LoginEvent Model：user（外键）、ip、ua、ts（DateTimeField）、success（BooleanField）
- 需求：注册用户 → 模拟一系列登录事件（成功 + 失败）→ 查询某用户的所有事件 →
  统计成功率 → 锁定连续失败 ≥3 次的账号 → 用 SortedSet 维护"最近登录排行榜"。

约束：≥30 行真业务（无 toy demo）；用 README 文档化的 ORM 用法；不 import
内部私有 API。
"""
import os
import sys
import tempfile
import time
import datetime

# 1. 真 redis（redislite，本进程内启动 redis-server）
import redislite
RDB_DIR = tempfile.mkdtemp(prefix="redisco-scen-")
_r = redislite.Redis(os.path.join(RDB_DIR, "redis.db"))
SOCK = _r.socket_file

# 2. 把 redisco 接到这个 redis
import redisco
redisco.connection_setup(unix_socket_path=SOCK, db=0, decode_responses=True)
from redisco import models, containers
redisco.get_client().flushdb()


# ---- Domain models（README 文档化用法） ----
class User(models.Model):
    username = models.Attribute(required=True, unique=True, indexed=True)
    email = models.Attribute(indexed=True)
    login_count = models.Counter()
    failed_attempts = models.Counter()
    locked = models.BooleanField(default=False)


class LoginEvent(models.Model):
    user = models.ReferenceField(User)
    ip = models.Attribute()
    ua = models.Attribute()
    ts = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField()


# ---- 注册三个用户 ----
alice = User.objects.create(username="alice", email="alice@example.com")
bob = User.objects.create(username="bob", email="bob@example.com")
carol = User.objects.create(username="carol", email="carol@example.com")
assert alice and bob and carol
assert User.objects.filter(username="alice").first().id == alice.id

# ---- 模拟登录事件流（混合成功/失败）----
EVENTS = [
    ("alice", "10.0.0.1", "Mozilla/5.0", True),
    ("alice", "10.0.0.1", "Mozilla/5.0", True),
    ("bob",   "10.0.0.2", "curl/8.0",     True),
    ("carol", "10.0.0.3", "Chrome",       False),
    ("carol", "10.0.0.3", "Chrome",       False),
    ("carol", "10.0.0.3", "Chrome",       False),  # 第三次失败 → 锁定
    ("alice", "10.0.0.1", "Mozilla/5.0", True),
    ("bob",   "10.0.0.4", "curl/8.0",     False),
]

# 排行榜（按最后登录时间）
recent = containers.SortedSet("recent_login_zset")

for username, ip, ua, ok in EVENTS:
    u = User.objects.filter(username=username).first()
    assert u is not None, username
    ev = LoginEvent(user=u, ip=ip, ua=ua, success=ok)
    assert ev.save(), ev.errors
    if ok:
        u.incr("login_count")
        # 重置 failed_attempts：直接用 incr(-N) 把它清回 0
        if u.failed_attempts > 0:
            u.incr("failed_attempts", -u.failed_attempts)
        recent.zadd({u.username: time.time()})
    else:
        u.incr("failed_attempts")
        if u.failed_attempts >= 3:
            u.locked = True
            u.save()

# ---- 查询：每个用户的事件 ----
alice_events = list(LoginEvent.objects.filter(user_id=alice.id))
assert len(alice_events) == 3, f"alice events: {len(alice_events)}"
assert all(e.success for e in alice_events), "alice all should be success"

carol_events = list(LoginEvent.objects.filter(user_id=carol.id))
assert len(carol_events) == 3
assert all(not e.success for e in carol_events), "carol all should be failures"

# ---- 业务断言：carol 应已锁定 ----
carol_now = User.objects.get_by_id(carol.id)
assert carol_now.locked is True, f"carol locked={carol_now.locked}"
assert carol_now.failed_attempts == 3

# ---- 业务断言：alice 成功 3 次，failed_attempts=0 ----
alice_now = User.objects.get_by_id(alice.id)
assert alice_now.login_count == 3, f"alice login_count={alice_now.login_count}"
assert alice_now.failed_attempts == 0
assert alice_now.locked is False

# ---- bob：1 成功 + 1 失败 ----
bob_now = User.objects.get_by_id(bob.id)
assert bob_now.login_count == 1
assert bob_now.failed_attempts == 1
assert bob_now.locked is False

# ---- 排行榜：最近登录第一名 ----
top = recent.zrevrange(0, 0)
assert top, top
# 最后一次成功登录是 alice（在 EVENTS 里 idx=6），bob 的成功在 idx=2
assert top[0] == "alice", f"recent top should be alice, got {top}"

# ---- 总体事件数 ----
total = len(list(LoginEvent.objects.all()))
assert total == 8, f"total events={total}"

# ---- Filter by indexed email ----
found = User.objects.filter(email="bob@example.com").first()
assert found.id == bob.id

print(f"OK: 8 events stored, alice login_count=3, carol locked={carol_now.locked}, top={top[0]}")
print("USABLE")
