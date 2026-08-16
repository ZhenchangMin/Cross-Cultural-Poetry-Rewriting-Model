# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Sequence, Tuple

from pypinyin import pinyin, Style

_PUNCT_RE = re.compile(r"[，。！？；：、,.!?;:\s\"'“”‘’（）()\[\]{}《》<>…—\-]+")


def _clean_line(line: str) -> str:
    return re.sub(_PUNCT_RE, "", line.strip())


def _last_char(clean_line: str) -> Optional[str]:
    clean_line = clean_line.strip()
    if not clean_line:
        return None
    return clean_line[-1]


def _finals_of_char(ch: str) -> Optional[str]:
    if not ch:
        return None
    py = pinyin(ch, style=Style.FINALS, strict=False)
    if not py or not py[0] or not py[0][0]:
        return None
    return py[0][0]


def _normalize_finals(finals: str, mode: str = "strict") -> str:
    """
    mode:
      - strict: no normalization
      - loose: light normalization to approximate rhyme groups
      - xinyun: 中华新韵（十四韵）分组，适用于现代读音的押韵判断
    """
    finals = finals.strip().lower()
    if mode == "strict":
        return finals

    if mode == "loose":
        # loose normalization (heuristic):
        # - merge uang -> ang (霜/光/乡 often rhyme-ish in modern ear)
        # - merge iang -> ang (强/香/凉 may rhyme-ish with ang group)
        # - merge eng/ing/ong? 先不乱合并，避免过宽
        mapping = {
            "uang": "ang",
            "iang": "ang",
            # 你也可以逐步扩展：
            # "iong": "ong",
        }
        return mapping.get(finals, finals)

    if mode == "xinyun":
        return _xinyun_group(finals)

    # 未知 mode 按 strict 处理
    return finals


# ── 中华新韵（十四韵）分组 ──────────────────────────────────────────────
# 依据《中华新韵（十四韵）简表》：按普通话韵母归组。
# 注意：平水韵（唐宋实际用韵）与普通话分组并不一致，如杜甫《登高》
# 的"哀/回/来/台/杯"同属平水韵十灰，但普通话分属"四开/五微"两组。
# 校验真实唐诗语料时建议后续引入平水韵韵部表。
_XINYUN_GROUPS: Dict[str, str] = {
    # 一麻
    "a": "1麻", "ia": "1麻", "ua": "1麻",
    # 二波
    "o": "2波", "e": "2波", "uo": "2波",
    # 三皆
    "ie": "3皆", "üe": "3皆", "ve": "3皆",
    # 四开
    "ai": "4开", "uai": "4开",
    # 五微
    "ei": "5微", "ui": "5微", "uei": "5微",
    # 六豪
    "ao": "6豪", "iao": "6豪",
    # 七尤
    "ou": "7尤", "iu": "7尤", "iou": "7尤",
    # 八寒
    "an": "8寒", "ian": "8寒", "uan": "8寒", "üan": "8寒", "van": "8寒",
    # 九文
    "en": "9文", "in": "9文", "un": "9文", "ün": "9文", "vn": "9文",
    # 十唐
    "ang": "10唐", "iang": "10唐", "uang": "10唐",
    # 十一庚
    "eng": "11庚", "ing": "11庚", "ong": "11庚", "iong": "11庚", "ueng": "11庚",
    # 十二齐
    "i": "12齐", "er": "12齐", "ü": "12齐", "v": "12齐",
    # 十四姑
    "u": "14姑",
}

# 十三支：zi/ci/si/zhi/chi/shi/ri 的韵母 pypinyin 记作 "i"，
# 需要结合声母判断，见 _xinyun_group。
_ZHI_CSI_INITIALS = ("zh", "ch", "sh", "r", "z", "c", "s")


def _syllable_of_char(ch: str) -> Optional[str]:
    py = pinyin(ch, style=Style.NORMAL, strict=False)
    if not py or not py[0] or not py[0][0]:
        return None
    return py[0][0].lower()


def _xinyun_group(finals: str, ch: Optional[str] = None) -> str:
    finals = finals.strip().lower()
    # 区分十二齐(i)与十三支(-i)：之/资类音节，声母恰为 zh/ch/sh/r/z/c/s
    if finals == "i" and ch:
        syl = _syllable_of_char(ch) or ""
        for ini in _ZHI_CSI_INITIALS:
            if syl.startswith(ini) and len(syl) == len(ini) + 1:
                return "13支"
    return _XINYUN_GROUPS.get(finals, finals)


def _tone_of_char(ch: str) -> Optional[int]:
    """返回 0-5 的声调数字：1/2=平声，3/4=仄声，0/5=轻声或未知。"""
    if not ch:
        return None
    py = pinyin(ch, style=Style.TONE3, strict=False)
    if not py or not py[0] or not py[0][0]:
        return None
    syl = py[0][0]
    for c in reversed(syl):
        if c.isdigit():
            return int(c)
    return 0


def is_ping_sheng(ch: str) -> Optional[bool]:
    """普通话一、二声视为平声（近似古四声中的平声）。"""
    t = _tone_of_char(ch)
    if t is None:
        return None
    return t in (1, 2)


@dataclass
class RhymeResult:
    ok: bool
    score: float
    finals_2: Optional[str]
    finals_4: Optional[str]
    last_2: Optional[str]
    last_4: Optional[str]
    details: str


def check_qijue7_rhyme(text: str, mode: str = "strict") -> RhymeResult:
    lines_raw = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lines_clean = [_clean_line(ln) for ln in lines_raw]

    if len(lines_clean) < 4:
        return RhymeResult(
            ok=False,
            score=0.0,
            finals_2=None,
            finals_4=None,
            last_2=None,
            last_4=None,
            details=f"Need >=4 lines for rhyme check, got {len(lines_clean)}",
        )

    last2 = _last_char(lines_clean[1])
    last4 = _last_char(lines_clean[3])

    if not last2 or not last4:
        return RhymeResult(
            ok=False,
            score=0.0,
            finals_2=None,
            finals_4=None,
            last_2=last2,
            last_4=last4,
            details="Empty last char in line 2 or 4",
        )

    f2 = _finals_of_char(last2)
    f4 = _finals_of_char(last4)

    if not f2 or not f4:
        return RhymeResult(
            ok=False,
            score=0.0,
            finals_2=f2,
            finals_4=f4,
            last_2=last2,
            last_4=last4,
            details="Failed to get finals for last chars",
        )

    nf2 = _normalize_finals(f2, mode=mode)
    nf4 = _normalize_finals(f4, mode=mode)

    ok = (nf2 == nf4)

    return RhymeResult(
        ok=ok,
        score=1.0 if ok else 0.0,
        finals_2=f"{f2}->{nf2}" if mode != "strict" else f2,
        finals_4=f"{f4}->{nf4}" if mode != "strict" else f4,
        last_2=last2,
        last_4=last4,
        details="OK" if ok else f"Rhyme mismatch: line2({last2}:{nf2}) vs line4({last4}:{nf4})",
    )


# ── 通用多韵位检查（七律等） ─────────────────────────────────────────────

@dataclass
class RhymePositionsResult:
    """对若干指定句位的末字做同韵检查（1-based 句号）。"""
    ok: bool
    score: float
    positions: List[int]
    last_chars: Dict[int, Optional[str]] = field(default_factory=dict)
    finals: Dict[int, Optional[str]] = field(default_factory=dict)
    norm_finals: Dict[int, Optional[str]] = field(default_factory=dict)
    tones: Dict[int, Optional[int]] = field(default_factory=dict)
    ping_ok: bool = False
    details: str = ""


def check_rhyme_at_positions(
    text: str,
    positions: Sequence[int] = (2, 4, 6, 8),
    mode: str = "strict",
    require_ping: bool = False,
) -> RhymePositionsResult:
    """
    检查 positions 各句末字是否同韵。
    - score = 与锚句（第一个句位）同韵的比例
    - require_ping=True 时，ok 还要求所有韵脚为普通话平声（一/二声）
    """
    lines_clean = [_clean_line(ln) for ln in text.splitlines() if ln.strip()]
    n = len(lines_clean)
    positions = list(positions)

    missing = [p for p in positions if p < 1 or p > n]
    if missing:
        return RhymePositionsResult(
            ok=False,
            score=0.0,
            positions=positions,
            details=f"Need lines at positions {missing}, but only {n} lines given",
        )

    last_chars: Dict[int, Optional[str]] = {}
    finals: Dict[int, Optional[str]] = {}
    norm_finals: Dict[int, Optional[str]] = {}
    tones: Dict[int, Optional[int]] = {}

    for p in positions:
        ch = _last_char(lines_clean[p - 1])
        last_chars[p] = ch
        finals[p] = _finals_of_char(ch) if ch else None
        # xinyun 分组需要原字来区分十二齐/十三支
        norm_finals[p] = (
            _xinyun_group(finals[p], ch) if (mode == "xinyun" and finals[p]) else
            (_normalize_finals(finals[p], mode=mode) if finals[p] else None)
        )
        tones[p] = _tone_of_char(ch) if ch else None

    if any(fv is None for fv in finals.values()):
        return RhymePositionsResult(
            ok=False,
            score=0.0,
            positions=positions,
            last_chars=last_chars,
            finals=finals,
            norm_finals=norm_finals,
            tones=tones,
            details="Failed to get finals for some last chars",
        )

    anchor = norm_finals[positions[0]]
    matches = sum(1 for p in positions if norm_finals[p] == anchor)
    score = matches / float(len(positions))

    ping_ok = all(t in (1, 2) for t in tones.values())
    all_match = (matches == len(positions))
    ok = all_match and (ping_ok or not require_ping)

    if not all_match:
        mismatch = [
            f"L{p}({last_chars[p]}:{norm_finals[p]})"
            for p in positions if norm_finals[p] != anchor
        ]
        details = f"Rhyme mismatch vs L{positions[0]}({last_chars[positions[0]]}:{anchor}): " + ", ".join(mismatch)
    elif require_ping and not ping_ok:
        ze = [f"L{p}({last_chars[p]}:tone{tones[p]})" for p in positions if tones[p] not in (1, 2)]
        details = "Rhyme ok but not all level-tone (平声): " + ", ".join(ze)
    else:
        details = "OK"

    return RhymePositionsResult(
        ok=ok,
        score=score,
        positions=positions,
        last_chars=last_chars,
        finals=finals,
        norm_finals=norm_finals,
        tones=tones,
        ping_ok=ping_ok,
        details=details,
    )


def check_qilv7_rhyme(text: str, mode: str = "strict", require_ping: bool = False) -> RhymePositionsResult:
    """七律押韵：第 2/4/6/8 句末字同韵（默认不强制平声判断）。"""
    return check_rhyme_at_positions(text, positions=(2, 4, 6, 8), mode=mode, require_ping=require_ping)


def as_dict(res: RhymeResult) -> Dict[str, Any]:
    return {
        "ok": res.ok,
        "score": res.score,
        "last_2": res.last_2,
        "finals_2": res.finals_2,
        "last_4": res.last_4,
        "finals_4": res.finals_4,
        "details": res.details,
    }


def positions_as_dict(res: RhymePositionsResult) -> Dict[str, Any]:
    return {
        "ok": res.ok,
        "score": res.score,
        "positions": res.positions,
        "last_chars": res.last_chars,
        "finals": res.finals,
        "norm_finals": res.norm_finals,
        "tones": res.tones,
        "ping_ok": res.ping_ok,
        "details": res.details,
    }
