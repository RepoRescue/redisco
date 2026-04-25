"""
redisco usability_validate — Type B (end-user library API).

招牌用法：定义 Model 类（继承 redisco.models.Model）+ Indexed Attribute /
Counter / ListField / ReferenceField 字段；通过 Manager.save / filter / get_by_id /
delete 完成 ORM 风格的 CRUD；用 Container（Hash / List / SortedSet）直接操作底层
Redis 数据结构。

后端：用 redislite（在进程内启动真 redis-server，走真 redis 协议）。
"""
import os
import sys
import tempfile

# 1. 启动 in-process 真 redis（走 redis 协议，不是 mock）
import redislite
RDB_DIR = tempfile.mkdtemp(prefix="redisco-usab-")
RDB = os.path.join(RDB_DIR, "redis.db")  # let redislite create it
_r = redislite.Redis(RDB)
SOCK = _r.socket_file
print(f"[setup] redislite socket={SOCK}")

# 2. 把 redisco 的连接指向这个真 redis
import redisco
redisco.connection_setup(unix_socket_path=SOCK, db=0, decode_responses=True)

# Sub-module 1: redisco.models (Model + ModelBase metaclass)
from redisco import models
# Sub-module 2: redisco.containers (Hash / SortedSet / List)
from redisco import containers
# Sub-module 3: redisco.models.attributes (Attribute / Counter / ListField / ReferenceField)
from redisco.models import attributes as redisco_attributes
# Sub-module 4: redisco.models.managers (Manager + ManagerDescriptor)
from redisco.models import managers as redisco_managers

# ---------------- 定义两个 Model 类（含外键 + indexed field + Counter + List） ----------------

class Author(models.Model):
    name = models.Attribute(required=True, indexed=True)
    bio = models.Attribute()
    book_count = models.Counter()           # Counter 字段
    tags = models.ListField(str)            # ListField(str)


class Book(models.Model):
    title = models.Attribute(required=True, indexed=True)
    isbn = models.Attribute(indexed=True)
    pages = models.IntegerField()
    author = models.ReferenceField(Author)  # 外键


# ---------------- 清场（防止 redislite 文件复用残留） ----------------
client = redisco.get_client()
client.flushdb()

# ---------------- INSERT：写两个作者 + 三本书 ----------------
alice = Author(name="Alice", bio="Sci-fi novelist", tags=["scifi", "hugo-winner"])
assert alice.is_valid(), alice.errors
assert alice.save() is True

bob = Author(name="Bob")
assert bob.save() is True

book1 = Book(title="Dune", isbn="978-0441013593", pages=688, author=alice)
assert book1.save() is True
book2 = Book(title="Foundation", isbn="978-0553293357", pages=255, author=alice)
assert book2.save() is True
book3 = Book(title="Snow Crash", isbn="978-0553380958", pages=480, author=bob)
assert book3.save() is True

# Counter incr (走 redisco.models.attributes.Counter + 真 INCR 命令)
alice.incr("book_count")
alice.incr("book_count")
alice.incr("book_count")  # = 3
bob.incr("book_count")    # = 1

# ---------------- QUERY：通过 Manager.filter on indexed field ----------------
found_alice = Author.objects.filter(name="Alice").first()
assert found_alice is not None, "filter by indexed name failed"
assert found_alice.id == alice.id, f"id mismatch: {found_alice.id} vs {alice.id}"
assert found_alice.name == "Alice", found_alice.name

# Counter 读回（直接走属性访问，redisco 把 counter 存为 hash field）
alice_reloaded = Author.objects.get_by_id(alice.id)
assert alice_reloaded.book_count == 3, f"book_count={alice_reloaded.book_count}"

# ListField 读回
assert "scifi" in alice_reloaded.tags, alice_reloaded.tags
assert "hugo-winner" in alice_reloaded.tags

# Filter Book by indexed isbn
dune = Book.objects.filter(isbn="978-0441013593").first()
assert dune is not None
assert dune.title == "Dune"
assert dune.pages == 688

# ReferenceField dereference（这条直接走 redisco/models/attributes.py 的
# ReferenceField + Manager.get_by_id，是 ORM 招牌路径）
assert dune.author.id == alice.id
assert dune.author.name == "Alice"

# all() — 三本书
all_books = list(Book.objects.all())
assert len(all_books) == 3, f"expected 3 books, got {len(all_books)}"

# 按 author 过滤（reference field 的反向查询：alice 的 books）
alice_books = Book.objects.filter(author_id=alice.id).all()
assert len(list(alice_books)) == 2, f"alice should have 2 books"

# ---------------- CONTAINERS：直接用 Hash/SortedSet/List ----------------
h = containers.Hash("user:42:profile")
h["name"] = "Carol"
h["city"] = "Tokyo"
assert h["name"] == "Carol"
assert dict(h.hgetall()) == {"name": "Carol", "city": "Tokyo"}, dict(h.hgetall())

# SortedSet 走 redisco containers.SortedSet（zadd 有 redis-py API 适配）
ss = containers.SortedSet("leaderboard")
ss.add({"alice": 100, "bob": 80, "carol": 95})
top = ss.zrevrange(0, 0)
assert top[0] == "alice", f"top: {top}"
assert ss.zscore("bob") == 80

# List
lst = containers.List("notes")
lst.append("first")
lst.append("second")
assert len(lst) == 2
assert lst[0] == "first"

# ---------------- DELETE ----------------
book3_id = book3.id
assert Book.objects.get_by_id(book3_id) is not None
book3.delete()
assert Book.objects.get_by_id(book3_id) is None, "book3 not deleted"
remaining = list(Book.objects.all())
assert len(remaining) == 2, f"after delete: {len(remaining)}"

# 子模块 path 覆盖断言（硬约束 5：≥3 path）
assert models is not None and models.Model is not None
assert containers is not None and containers.Hash is not None
assert redisco_attributes.Counter is not None and redisco_attributes.ReferenceField is not None
assert redisco_managers.Manager is not None
assert redisco.get_client() is not None

print("USABLE")
