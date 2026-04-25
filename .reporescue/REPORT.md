# redisco — Usability Validation

**Selected rescue**: glm (T2 PASS, srconly PASS) — 唯一 PASS 模型
**Scenario type**: B (end-user library API — Redis ORM)
**Real-world use**: 把 Python 对象（含外键、Counter、List 字段）持久化到 Redis，
通过 indexed Attribute 做 ORM 风格的 filter / get_by_id / save / delete；同时直接用
`containers.Hash / List / SortedSet` 操作底层 Redis 数据结构。

## Step 0: Import sanity
repos/rescue_glm/redisco/venv-t2/bin/python -c "import redisco; from redisco import models, containers" → OK

## Step 1: 模型选择
- glm: T2 PASS + srconly PASS（源码修复独立有效）
- sonnet / minimax / kimi: T2 FAIL → 不可选

## Step 4: Install + core feature (clean venv)
- python3.13 -m venv /tmp/redisco-clean
- pip install -e <rescue_glm/redisco> → OK
- pip install redislite（运行依赖） → OK
- 离开 rescue 树（cd /tmp）后跑 validate → "USABLE"
- 后端：redislite（进程内 fork 真 redis-server，走真 Redis 协议）

## Hard constraint 6: Py3.13 surface stressed (审计 redisco.src.patch)

| Surface | Evidence |
|---|---|
| collections.MutableMapping → collections.abc.MutableMapping (3.10+) | containers.py:1, 1183 |
| unicode 移除 (Py3) | containers.py:264-327, models/attributes.py 多处 |
| basestring 移除 (Py3) | containers.py:710, models/attributes.py:65,99,326,353, models/base.py:48,397 |
| xrange 移除 (Py3) | containers.py:766, containerstests.py:347,353 |
| dict.iteritems 移除 (Py3) | models/base.py 7处, models/modelset.py 3处 |
| dict.has_key 移除 (Py3) | models/attributes.py:498 |
| __metaclass__ → metaclass= | models/base.py:230 |
| dict_values + dict_values 不可加 (Py3) | models/base.py:308,492 |
| map/filter 迭代器 (Py3) | containers.py:734, models/attributes.py:339, models/modelset.py:33,46 |
| 相对 import (Py3 必须) | containers.py:710,712 等 |
| redis-py 7.x API (zadd mapping / lrem 参数序 / hmset → hset / zincrby 参数序) | containers.py:607, 931-934, 975, 1295 |

→ ≥10 类不同破坏面被实际触动，远超 TRIVIAL 阈值。

## Beyond unit tests (constraint 3)
redisco/tests/ 仅有空 __init__.py。原 unit test 在 containerstests.py / models/basetests.py。
我们 validate 用了 tests 没覆盖的组合：Author+Book ReferenceField 反向 filter、
"leaderboard"/"user:42:profile" 业务级 key、登录失败锁定策略 + recent_login zset。

## Step 6: Downstream / Scenario
- Path A: skipped (redisco PyPI 最新仍是 0.1.4 abandoned，无 star≥100 近 2y commit 下游)
- Path B: ✅ scenario_validate.py 80+ 行真业务（注册→8 登录事件→自动锁定→排行榜→断言）

## Step 7: Bug-hunt
6 个探针：Unicode 边界(emoji/CJK/RTL)、重复 save、并发 INCR (8 线程×50)、
ListField(int) 500 元素 round-trip、missing-key filter、Hash MutableMapping (del/keys/len)。
Found: none. 全过。

## Verdict
STATUS: USABLE

Reason: glm 的 rescue patch 触动了 10+ 类 Py3/Py3.13/redis-py 7.x 真实破坏面
（unicode/basestring/xrange/iteritems/has_key/__metaclass__/MutableMapping/
dict_values 加法/map filter 迭代器/相对 import），不是 dep pin 调整。在干净 venv 里
pip install -e 后离开 rescue 树仍能完整使用 ORM 招牌功能（Model + ReferenceField
+ Counter + Manager.filter + SortedSet 排行榜），bug-hunt 6 个边界 probe 全过。
Path A 跳过原因是 redisco 已废弃无活跃下游；Path B 用 80 行真业务替代，断言全过。
