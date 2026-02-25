# -*- coding: utf-8 -*-
from __future__ import annotations

from src.constraints.scorer import score_qijue7, as_dict

# ✅ 合规示例（4句、每句7字、2/4句同韵：光/霜 这里不一定同韵，仅做示例，你可以换成“乡/霜”这种更可能同韵的末字）
poem_ok = """春风拂柳入新塘，
月照孤舟夜未央。
远客凭栏思故里，
寒星点点落清霜。"""

# ❌ 句数错误
poem_bad_lines = """春风拂柳入新塘，
月照孤舟夜未央。
远客凭栏思故里。"""

# ❌ 字数错误（第二句太短）
poem_bad_len = """春风拂柳入新塘，
月照孤舟夜央。
远客凭栏思故里，
寒星点点落清霜。"""

tests = [
    ("ok-ish", poem_ok),
    ("bad_lines", poem_bad_lines),
    ("bad_len", poem_bad_len),
]

if __name__ == "__main__":
    for name, text in tests:
        res = score_qijue7(text, rhyme_mode="strict")
        res2 = score_qijue7(text, rhyme_mode="loose")
        d = as_dict(res)
        d2 = as_dict(res2)
        print("STRICT:", d)
        print("LOOSE :", d2)