# -*- coding: utf-8 -*-
"""
MIDAS CIVIL NX Open API 얇은 래퍼.
- MAPI-Key / 서버 주소를 레지스트리(CIVIL NX가 API Settings > Connect 시 기록) 또는
  환경변수 MIDAS_MAPI_KEY / MIDAS_MAPI_URL 에서 읽는다.
- 키 값은 절대 출력하지 않는다.
"""
import os, sys, json, winreg
import requests

_REG_PATHS = [
    r"Software\MIDAS\CVLwNX_KR_HYPER_S\CONNECTION",   # 이 PC의 제품 키
    r"Software\MIDAS\CVLwNX_KR\CONNECTION",
    r"Software\MIDAS\CVLwNX_US\CONNECTION",
]

def _reg_read(path):
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ)
    except OSError:
        return None
    out = {}
    for name in ("Key", "URI", "PORT"):
        try:
            out[name] = winreg.QueryValueEx(k, name)[0]
        except OSError:
            pass
    return out or None

def load_config():
    key = os.environ.get("MIDAS_MAPI_KEY", "")
    url = os.environ.get("MIDAS_MAPI_URL", "")
    src = "env"
    if not (key and url):
        for p in _REG_PATHS:
            r = _reg_read(p)
            if r and r.get("Key"):
                key = key or r["Key"]
                if not url and r.get("URI"):
                    port = r.get("PORT", 443)
                    scheme = "http" if str(r["URI"]).startswith(("127.", "localhost")) else "https"
                    url = f"{scheme}://{r['URI']}:{port}/civil"
                src = f"registry:{p}"
                break
    if not key:
        raise RuntimeError("MAPI-Key 없음. CIVIL NX에서 Apps > API Settings > Connect 를 먼저 켜야 함.")
    if not url:
        url = "https://moa-engineers-kr.midasit.com:443/civil"
    return key, url.rstrip("/"), src

class Civil:
    def __init__(self, timeout=120):
        self.key, self.base, self.src = load_config()
        self.timeout = timeout
        self.h = {"Content-Type": "application/json", "MAPI-Key": self.key}

    def call(self, method, endpoint, body=None):
        r = requests.request(method, self.base + endpoint, headers=self.h,
                             json=body, timeout=self.timeout)
        try:
            data = r.json()
        except ValueError:
            data = {"_raw": r.text[:500]}
        if r.status_code != 200:
            raise RuntimeError(f"{method} {endpoint} -> HTTP {r.status_code}: {json.dumps(data, ensure_ascii=False)[:500]}")
        return data

    def get(self, ep):            return self.call("GET", ep)
    def put(self, ep, body):      return self.call("PUT", ep, body)
    def post(self, ep, body):     return self.call("POST", ep, body)
    def delete(self, ep):         return self.call("DELETE", ep)

    # 자주 쓰는 것
    def version(self):   return self.get("/config/ver")
    def units(self):     return self.get("/db/UNIT")
    def node_count(self):
        d = self.get("/db/NODE"); return len(d.get("NODE", {}))
    def elem_count(self):
        d = self.get("/db/ELEM"); return len(d.get("ELEM", {}))

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        c = Civil(timeout=30)
    except Exception as e:
        print("연결 설정 실패:", e); sys.exit(2)
    print("설정 출처:", c.src, "| 서버:", c.base, "| 키 길이:", len(c.key))
    try:
        print("버전:", json.dumps(c.version(), ensure_ascii=False))
        print("단위:", json.dumps(c.units(), ensure_ascii=False))
        print("절점 수:", c.node_count(), "| 요소 수:", c.elem_count())
        print("API 연결 OK")
    except Exception as e:
        print("API 호출 실패:", e); sys.exit(1)
