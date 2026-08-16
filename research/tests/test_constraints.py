# -*- coding: utf-8 -*-
"""constraints 模块单元测试。

运行方式（WSL, research/ 目录下）：
    .venv/bin/python -m pytest tests/ -q
"""
import pytest

from src.constraints.meter import check_qijue7, check_qilv7
from src.constraints.rhyme import (
    check_qijue7_rhyme,
    check_qilv7_rhyme,
    is_ping_sheng,
)
from src.constraints.parallel import check_pair, check_qilv7_parallelism
from src.constraints.scorer import score_qijue7, score_qilv7, score_poem


# ── 测试语料 ──────────────────────────────────────────────────────────

# 七绝：2/4 句末字同为 iang（香/湘）
QIJUE_STRICT_OK = """春风拂柳入回廊，
月照孤舟夜未央。
远客凭栏思故里，
寒星点点落寒江。"""
# 末字 廊(lang)/央(yang)/里/江(jiang)：strict 下 ang≠iang≠yang，
# xinyun 下同属十唐
QIJUE_XINYUN_OK = QIJUE_STRICT_OK

QIJUE_3LINES = """春风拂柳入回廊，
月照孤舟夜未央。
远客凭栏思故里。"""

QIJUE_SHORT_LINE = """春风拂柳入回廊，
月照孤舟未央。
远客凭栏思故里，
寒星点点落寒江。"""

# 崔颢《黄鹤楼》：七律名篇，韵脚 楼/悠/洲/愁（新韵七尤，全平声）
QILV_OK = """昔人已乘黄鹤去，
此地空余黄鹤楼。
黄鹤一去不复返，
白云千载空悠悠。
晴川历历汉阳树，
芳草萋萋鹦鹉洲。
日暮乡关何处是，
烟波江上使人愁。"""

# 杜甫《登高》：韵脚 回/来/台/杯 平水韵同属十灰，
# 但普通话分属 五微(ui/ei) 与 四开(ai)，xinyun 下应得部分分
QILV_DENGGAO = """风急天高猿啸哀，
渚清沙白鸟飞回。
无边落木萧萧下，
不尽长江滚滚来。
万里悲秋常作客，
百年多病独登台。
艰难苦恨繁霜鬓，
潦倒新停浊酒杯。"""

QILV_6LINES = """\n""".join(QILV_OK.splitlines()[:6])


# ── meter ────────────────────────────────────────────────────────────

class TestMeter:
    def test_qijue_ok(self):
        r = check_qijue7(QIJUE_STRICT_OK)
        assert r.ok and r.score == 1.0

    def test_qijue_wrong_line_count(self):
        r = check_qijue7(QIJUE_3LINES)
        assert not r.ok and r.score == 0.0
        assert "Expected 4 lines, got 3" in r.details

    def test_qijue_wrong_length_partial_score(self):
        r = check_qijue7(QIJUE_SHORT_LINE)
        assert not r.ok
        assert 0.0 < r.score < 1.0  # 部分分

    def test_qilv_ok(self):
        r = check_qilv7(QILV_OK)
        assert r.ok and r.score == 1.0

    def test_qilv_wrong_line_count(self):
        r = check_qilv7(QILV_6LINES)
        assert not r.ok and r.score == 0.0
        assert "Expected 8 lines, got 6" in r.details

    def test_empty(self):
        assert not check_qijue7("").ok
        assert not check_qilv7("   \n  ").ok


# ── rhyme ────────────────────────────────────────────────────────────

class TestRhyme:
    def test_qijue_strict_mismatch(self):
        # 廊(ang) vs 江(iang)：strict 不通过
        r = check_qijue7_rhyme(QIJUE_STRICT_OK, mode="strict")
        assert not r.ok

    def test_qijue_xinyun_match(self):
        # 廊/江 同属新韵十唐
        r = check_qijue7_rhyme(QIJUE_XINYUN_OK, mode="xinyun")
        assert r.ok and r.score == 1.0

    def test_qilv_xinyun_ok_and_ping(self):
        r = check_qilv7_rhyme(QILV_OK, mode="xinyun", require_ping=True)
        assert r.ok and r.score == 1.0 and r.ping_ok

    def test_denggao_partial_score(self):
        # 平水韵同韵但普通话不同组：2/4 同分得 0.5 部分分
        r = check_qilv7_rhyme(QILV_DENGGAO, mode="xinyun")
        assert not r.ok
        assert r.score == pytest.approx(0.5)
        assert r.ping_ok  # 韵脚仍全是平声

    def test_too_few_lines(self):
        r = check_qilv7_rhyme(QILV_6LINES, mode="xinyun")
        assert not r.ok and r.score == 0.0

    def test_ping_sheng(self):
        assert is_ping_sheng("楼") is True   # lóu
        assert is_ping_sheng("去") is False  # qù


# ── parallel ────────────────────────────────────────────────────────

class TestParallel:
    def test_pair_same_chars_fail(self):
        r = check_pair("白日依山尽", "白日依山尽")
        assert not r.ok and r.diff_score == 0.0

    def test_pair_differing_chars_pass(self):
        r = check_pair("晴川历历汉阳树", "芳草萋萋鹦鹉洲")
        assert r.diff_score == 1.0
        assert r.score >= 0.6

    def test_qilv_parallelism_ok(self):
        r = check_qilv7_parallelism(QILV_OK)
        assert r.ok
        assert "颔联" in r.pairs and "颈联" in r.pairs

    def test_qilv_parallelism_too_few_lines(self):
        # 对仗检查最少需要 6 行（颔联 3-4 + 颈联 5-6）
        lines5 = "\n".join(QILV_OK.splitlines()[:5])
        r = check_qilv7_parallelism(lines5)
        assert not r.ok and r.score == 0.0

    def test_parallelism_same_couplets_fail(self):
        # 颔联两句完全相同 → 对仗失败
        lines = QILV_OK.splitlines()
        lines[2] = lines[3]
        r = check_qilv7_parallelism("\n".join(lines))
        assert not r.ok


# ── scorer ───────────────────────────────────────────────────────────

class TestScorer:
    def test_qijue_regression_rhyme_mode_param(self):
        # 回归：历史上 score_qijue7 内部引用未定义的 rhyme_mode 会 NameError
        res = score_qijue7(QIJUE_XINYUN_OK, rhyme_mode="xinyun")
        assert res.rhyme_score == 1.0

    def test_qilv_full_score(self):
        res = score_qilv7(QILV_OK, rhyme_mode="xinyun")
        assert res.ok
        assert res.total == pytest.approx(1.0)
        assert res.meter_score == 1.0
        assert res.rhyme_score == 1.0
        assert res.parallel_score >= 0.6

    def test_qilv_denggao_meter_ok_but_rhyme_partial(self):
        res = score_qilv7(QILV_DENGGAO, rhyme_mode="xinyun")
        assert res.meter_score == 1.0
        assert res.rhyme_score == pytest.approx(0.5)
        assert 0.0 < res.total < 1.0

    def test_score_poem_dispatch(self):
        d = score_poem(QILV_OK, form="qilv7", rhyme_mode="xinyun")
        assert d["ok"] is True
        d2 = score_poem(QIJUE_XINYUN_OK, form="qijue7", rhyme_mode="xinyun")
        assert d2["ok"] is True

    def test_score_poem_unknown_form(self):
        with pytest.raises(ValueError):
            score_poem("x", form="cifu")
