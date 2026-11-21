"""Check actual Chrome downloads and reopen them with Android's system file picker on a connected test device."""
import argparse
import hashlib
import json
import re
import shlex
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import websocket

SAMPLES = ("SP-FEST", "SP-MUS", "SP-BASE")
PUBLIC = "https://ticketguard-ai-demo.tart-hippo-0446.chatgpt.site"
FOLDER = "/sdcard/Download"
CHROME = "com.android.chrome"


def adb(*args, binary=False):
    result = subprocess.check_output(["adb", *args], timeout=25)
    return result if binary else result.decode("utf-8", errors="replace").strip()


def command(*args):
    return adb("shell", shlex.join(args))


def ui_nodes():
    try:
        command("uiautomator", "dump", "/data/local/tmp/ticketguard-qa-ui.xml")
        return list(ET.fromstring(command("cat", "/data/local/tmp/ticketguard-qa-ui.xml")).iter("node"))
    except (ET.ParseError, subprocess.SubprocessError):
        return []


def tap(nodes, labels):
    for label in labels:
        for node in nodes:
            if label not in (node.get("text"), node.get("content-desc")):
                continue
            coords = [int(n) for n in re.findall(r"\d+", node.get("bounds", ""))]
            if len(coords) == 4:
                x, y, right, bottom = coords
                command("input", "tap", str((x + right)//2), str((y + bottom)//2))
                return True
    return False


class ChromeTab:
    def __init__(self, url):
        self.socket = websocket.create_connection(url, timeout=12, suppress_origin=True)
        self.seq = 0

    def evaluate(self, expr):
        self.seq += 1
        self.socket.send(json.dumps({"id": self.seq, "method": "Runtime.evaluate", "params": {
            "expression": expr, "returnByValue": True, "userGesture": True}}))
        while True:
            msg = json.loads(self.socket.recv())
            if msg.get("id") == self.seq:
                return msg.get("result", {}).get("result", {}).get("value")

    def wait(self, expr, seconds=18):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            result = self.evaluate(expr)
            if result:
                return result
            time.sleep(.4)
        raise RuntimeError("Chrome가 요청한 화면 상태에 도달하지 못했습니다.")


def open_page(url):
    command("am", "start", "-a", "android.intent.action.VIEW", "-d", url, "-p", CHROME)
    port = adb("forward", "tcp:0", "localabstract:chrome_devtools_remote")
    deadline = time.monotonic() + 80
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=2) as r:
                tabs = json.load(r)
            page = next((t for t in tabs if t.get("url", "").startswith(url.split("?")[0]) and t.get("type")=="page"), None)
            if page:
                tab = ChromeTab(page["webSocketDebuggerUrl"])
                if tab.evaluate("Boolean(document.querySelector('#download'))"):
                    return tab
                tab.socket.close()
        except (OSError, ValueError, websocket.WebSocketException):
            pass
        tap(ui_nodes(), ["Use without an account", "Continue without an account", "No thanks", "Accept & continue", "Got it"])
        time.sleep(.5)
    raise RuntimeError("Android Chrome에서 모바일 확인 페이지를 열지 못했습니다.")


def list_reports(sample):
    prefix = "TicketGuard_AI_"+sample
    # Inspect only this project's synthetic report filenames.
    cmd = "find "+FOLDER+" -maxdepth 1 -type f -name "+shlex.quote(prefix+"*.txt")
    return set(filter(None, adb("shell", cmd).splitlines()))


def verify_sample(base, sample, expected):
    tab = open_page(base+"/mobile-check?sample="+sample)
    try:
        before = list_reports(sample)
        tab.wait("document.querySelector('#download')?.href.includes("+json.dumps(sample)+")")
        tab.evaluate("document.querySelector('#download').click()")
        file = None
        end=time.monotonic()+45
        while time.monotonic()<end:
            found=list_reports(sample)-before
            if len(found)==1:
                file=found.pop()
                break
            tap(ui_nodes(), ["Download", "Download again", "Allow"])
            time.sleep(.4)
        if not file: raise RuntimeError(sample+" Android 다운로드 폴더에서 새 TXT가 확인되지 않았습니다.")
        data=adb("exec-out","sh","-c",shlex.quote("cat "+shlex.quote(file)),binary=True)
        digest=hashlib.sha256(data).hexdigest()
        if digest!=expected["sha256"] or len(data)!=expected["bytes"]:
            raise RuntimeError(sample+" 다운로드 파일이 배포 소스의 기준 바이트와 다릅니다.")
        tab.evaluate("document.querySelector('#pick').click()")
        filename = file.rsplit("/",1)[-1]
        end=time.monotonic()+35
        selected=False
        while time.monotonic()<end:
            nodes=ui_nodes()
            if tap(nodes,[filename]):
                selected=True
                break
            tap(nodes,["Downloads","Show roots","Show more options","Files","Browse files"])
            time.sleep(.4)
        if not selected: raise RuntimeError(sample+" Android 파일 선택창에서 재열기 실패")
        proof=tab.wait("document.querySelector('#proof')?.hidden===false && document.querySelector('#details').textContent")
        return {"sample":sample,"bytes":len(data),"sha256":digest,"reopened":True,"browser_proof":proof}
    finally:
        tab.socket.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--origin",default=PUBLIC)
    parser.add_argument("--golden",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    golden=json.loads(args.golden.read_text())
    emulator=command("getprop","ro.kernel.qemu")=="1" or command("getprop","ro.boot.qemu")=="1"
    version=command("dumpsys","package",CHROME)
    match=re.search(r"versionName=([^\s]+)",version)
    evidence={"origin":args.origin,"environment":"emulator" if emulator else "attached_device",
              "device":command("getprop","ro.product.model"),"android":command("getprop","ro.build.version.release"),
              "chrome":match.group(1) if match else None,"rows":[]}
    if not evidence["chrome"]: raise RuntimeError("연결된 테스트 기기에 Android Chrome이 필요합니다.")
    try:
        for sample in SAMPLES:
            evidence["rows"].append(verify_sample(args.origin.rstrip("/"),sample,golden[sample]))
    finally:
        args.output.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(evidence,ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
