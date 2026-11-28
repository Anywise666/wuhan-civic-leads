#!/usr/bin/env python3
"""读取武汉城市留言板公开详情接口，输出关键字段（不入库，仅辅助核验）。"""
import json
import sys
import urllib.parse
import urllib.request

URL = "https://api1-liuyan.cjn.cn/messageboard/internetUserInterface/selectThreadsOne"


def fetch(tid):
    data = urllib.parse.urlencode({"tid": str(tid)}).encode()
    req = urllib.request.Request(
        URL, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Origin": "https://liuyan.cjn.cn",
                 "Referer": "https://liuyan.cjn.cn/",
                 "User-Agent": "Mozilla/5.0"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def brief(tid):
    try:
        j = fetch(tid)
    except Exception as e:
        return {"tid": tid, "error": str(e)}
    t = j.get("threadsObj") or {}
    ans = t.get("answersList") or []
    return {
        "tid": tid,
        "queryCode": t.get("queryCode"),
        "lybh": t.get("lybh"),
        "subject": t.get("subject"),
        "nickName": t.get("nickName"),
        "dateline": t.get("dateline"),
        "domainId_txt": t.get("domainId_txt"),
        "isReply": t.get("isReply"),
        "content": (t.get("content") or "")[:700],
        "isReplyStr": t.get("isReplyStr"),
        "handleState": t.get("handleState"),
        "answers": [{"time": a.get("dateline_txt"),
                     "org": (a.get("fid_txt") or {}).get("organization"),
                     "text": (a.get("asContent") or "")[:400]}
                    for a in ans],
    }


if __name__ == "__main__":
    for tid in sys.argv[1:]:
        print(json.dumps(brief(tid), ensure_ascii=False))
