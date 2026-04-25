# redisco (RepoRescue modernized)

A Redis-backed ORM and container library for Python. Define `Model` classes the
Django way, get indexed lookups, references, counters, and list fields stored
natively in Redis — plus thin wrappers (`Hash`, `List`, `Set`, `SortedSet`)
over the underlying Redis data structures.

The original [`redisco`](https://pypi.org/project/redisco/) was abandoned in
2014 (last release `0.1.4`) and does not import on Python 3, let alone 3.13. It
is also incompatible with `redis-py` 4.x and later, where several core methods
changed signature. **This fork is the rescued version: it runs on Python 3.13
and `redis-py` 7.x, with no API changes visible to user code.**

If you have an old project that depended on redisco — or you want a small,
no-dependency Redis ORM and you don't need a maintained one — this fork lets
you keep using it. For new projects, you should probably reach for `redis-om`
or write directly against `redis-py`.

> Part of the [RepoRescue](https://github.com/RepoRescue) benchmark: a study of
> whether AI coding agents can revive abandoned Python libraries. This rescue
> was produced by GLM. See the disclaimer at the bottom.

---

## Install

```bash
pip install git+https://github.com/RepoRescue/redisco.git
```

Requires Python 3.10+ (tested on 3.13) and a running Redis server (or
`redislite` for an in-process Redis).

## Quick start

```python
import redisco
from redisco import models, containers

redisco.connection_setup(host="localhost", port=6379, db=0,
                         decode_responses=True)

class Author(models.Model):
    name        = models.Attribute(required=True, indexed=True)
    book_count  = models.Counter()
    tags        = models.ListField(str)

class Book(models.Model):
    title  = models.Attribute(required=True, indexed=True)
    isbn   = models.Attribute(indexed=True)
    pages  = models.IntegerField()
    author = models.ReferenceField(Author)

alice = Author(name="Alice", tags=["scifi", "hugo-winner"]); alice.save()
Book(title="Dune", isbn="978-0441013593", pages=688, author=alice).save()

alice.incr("book_count")                                  # atomic INCR
dune = Book.objects.filter(isbn="978-0441013593").first() # indexed lookup
print(dune.author.name)                                   # ReferenceField deref → "Alice"

board = containers.SortedSet("leaderboard")               # raw Redis ZSET
board.add({"alice": 100, "bob": 80})
print(board.zrevrange(0, 0))                              # → ["alice"]

dune.delete()
```

That is the complete surface — `Model` + indexed `Attribute` + `Counter` +
`ListField` + `ReferenceField` + `Manager.filter / get_by_id / save / delete`,
plus `Hash` / `List` / `Set` / `SortedSet` wrappers.

## What was fixed

The original codebase was Python 2 throughout. Python 3.13 plus `redis-py` 7.x
broke it in roughly ten different ways. The rescue patch is **733 lines** —
unusually deep for this benchmark, which is why we keep this entry around as a
case study. Surfaces touched:

| Category | Specifics |
|---|---|
| Removed Py2 builtins | `unicode`, `basestring`, `xrange` (`containers.py`, `models/attributes.py`, `models/base.py`) |
| Dict API changes | `dict.iteritems` (7 call sites in `models/base.py`, 3 in `models/modelset.py`), `dict.has_key` |
| Class machinery | `__metaclass__ = X` rewritten to `class Foo(..., metaclass=X)` |
| `collections` reorg (3.10+) | `collections.MutableMapping` → `collections.abc.MutableMapping` |
| Iterator-vs-list semantics | `dict.values() + dict.values()` no longer concatenates; `map`/`filter` return iterators — wrapped in `list(...)` at all call sites |
| Import system | Implicit relative imports rewritten to explicit (`from base import ...` → `from .base import ...`) |
| `redis-py` 7.x | `zadd(key, member, score)` → `zadd(key, mapping={...})`; `lrem` and `zincrby` argument order swap; `hmset` deprecated → `hset(name, mapping=...)` |

User-visible API is unchanged. If your old code worked against
`redisco==0.1.4`, it should work against this fork.

## Validation

We didn't just run the existing test suite. The fork was put through three
extra checks beyond unit tests:

- **Smoke** (`usability_validate.py`) — fresh venv outside the source tree,
  defines `Author`/`Book` with `ReferenceField`, exercises indexed `filter`,
  `Counter.incr`, `ListField` round-trip, raw `Hash`/`List`/`SortedSet`, then
  deletes. Backed by `redislite` so it goes over the real Redis wire protocol,
  not a mock.
- **Scenario** (`scenario_validate.py`) — an 80-line user-login store: register
  users, stream eight login events (mixed success/failure), auto-lock accounts
  on three consecutive failures, maintain a "recent logins" sorted-set
  leaderboard, and assert event counts and lock state.
- **Bug hunt** (`bug_hunt.py`) — six adversarial probes: mixed-Unicode
  (`emoji + CJK + RTL`) indexed lookup, repeated `save()` of the same object,
  8-thread × 50-iteration concurrent `Counter.incr` (4000 increments, expects
  no lost updates), `ListField(int)` 500-element round-trip, missing-key
  `filter`, and `Hash` `MutableMapping` protocol (`del` / `keys` / `len`).
  All six pass.

Reproduce:

```bash
python artifacts/redisco/usability_validate.py    # → "USABLE"
python artifacts/redisco/scenario_validate.py     # → "USABLE"
python artifacts/redisco/bug_hunt.py              # → "No bugs found in 6 probes."
```

## Notes

- We ran the same rescue task across four agents (Sonnet, Kimi, MiniMax, GLM).
  **GLM is the only model whose patch passes T2** — the others either left
  Python 2 idioms in or used the wrong `redis-py` 7.x signatures. This is one
  of the few entries in the benchmark where GLM produced a noticeably more
  thorough fix than Sonnet, which is itself an interesting data point.
- We skipped the "downstream consumer" validation path because redisco has no
  active reverse dependencies on PyPI — its last release predates most of its
  potential consumers' end-of-life. The scenario script above stands in for it.

## Disclaimer

This is a research artifact. The patch was generated by an AI agent (GLM) and
hand-validated against the criteria above; it is not a maintained release. We
don't run a CI matrix, we don't promise semver, and we won't ship security
fixes. Use it to unblock legacy code, not to start a new project.

## License

Original redisco is MIT-licensed (see `LICENSE`). This fork retains the same
license.
