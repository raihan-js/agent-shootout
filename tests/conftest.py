import os
from pathlib import Path

import pytest

os.environ["LANGSMITH_TRACING"] = "false"          # tests never call out
os.environ.pop("LANGSMITH_API_KEY", None)

ROOT = Path(__file__).parent.parent


def art(id_, title, caption, text):
    return {"id": id_, "title": title, "caption": caption, "text": text}


@pytest.fixture(scope="session")
def small_registry():
    """Two tiny laws with a branch article and a deleted article, enough to exercise every tool path."""
    long_text = "あ" * 1200
    return {"source": "test", "laws": [
        {"law_id": "L1", "title": "民法", "revision_id": "r1", "updated": "", "articles": [
            art("1", "第一条", "基本原則", "私権は、公共の福祉に適合しなければならない。"),
            art("2", "第二条", "解釈の基準", "この法律は、個人の尊厳と両性の本質的平等を旨として、解釈しなければならない。"),
            art("2-2", "第二条の二", "追加規定", "追加の規定について定める。これは枝番号の条文である。"),
            art("3", "第三条", "", "削除"),
            art("4", "第四条", "長い条文", long_text),
            art("5", "第五条", "契約の解除", "当事者の一方がその債務を履行しない場合において、相手方は契約の解除をすることができる。"),
        ]},
        {"law_id": "L2", "title": "会社法", "revision_id": "r2", "updated": "", "articles": [
            art("1", "第一条", "趣旨", "会社の設立、組織、運営及び管理については、他の法律に特別の定めがある場合を除くほか、この法律の定めるところによる。"),
            art("2", "第二条", "定義", "この法律において、次の各号に掲げる用語の意義は、当該各号に定めるところによる。"),
        ]},
    ]}


@pytest.fixture(scope="session")
def real_registry():
    from shootout import registry
    return registry.load(ROOT / "data" / "registry.json.gz")
