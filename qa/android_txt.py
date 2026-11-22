"""Check actual Chrome downloads and reopen them with Android's system file picker on a connected test device."""
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import websocket

SAMPLES = ("SP-FEST", "SP-MUS", "SP-BASE")
PUBLIC = "https://ticketguard-ai-demo.tart-hippo-0446.chatgpt.site"
FOLDER = "/sdcard/Download"
CHROME = "com.android.chrome"
SDK = os.getenv("ANDROID_HOME") or os.getenv("ANDROID_SDK_ROOT")
ADB_NAME = "adb.exe" if os.name == "nt" else "adb"
ADB = shutil.which(ADB_NAME) or (str(Path(SDK) / "platform-tools" / ADB_NAME) if SDK else ADB_NAME)


def adb(*args, binary=False):
    result = subprocess.check_output([ADB, *args], timeout=25)
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
    def __init__(self, url, port):
        self.port = port
        self.socket = websocket.create_connection(url, timeout=12, suppress_origin=True)
        self.seq = 0

    def evaluate(self, expr):
        self.seq += 1
        self.socket.send(json.dumps({"id": self.seq, "method": "Runtime.evaluate", "params": {
            "expression": expr, "returnByValue": True, "userGesture": True, "awaitPromise": True}}))
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
            page = next((t for t in tabs if t.get("url") == url and t.get("type") == "page"), None)
            if page:
                tab = ChromeTab(page["webSocketDebuggerUrl"], port)
                if tab.evaluate("Boolean(document.querySelector('#download'))"):
                    return tab
                tab.socket.close()
        except (OSError, ValueError, websocket.WebSocketException):
            pass
        tap(ui_nodes(), ["Use without an account", "Use Chrome without an account", "Continue without an account",
                         "Continue without signing in", "No thanks", "No, thanks", "Accept & continue", "Got it"])
        time.sleep(.5)
    adb("forward", "--remove", "tcp:" + port)
    raise RuntimeError("Android Chrome에서 모바일 확인 페이지를 열지 못했습니다.")


def list_reports(sample):
    prefix = "TicketGuard_AI_"+sample
    # Inspect only this project's synthetic report filenames.
    cmd = "find "+FOLDER+" -maxdepth 1 -type f -name "+shlex.quote(prefix+"*.txt")
    return set(filter(None, adb("shell", cmd).splitlines()))


def browser_reference(tab):
    return tab.evaluate("""(async () => {
        const response = await fetch(document.querySelector('#download').href, {cache: 'no-store'});
        if (!response.ok) return null;
        const bytes = await response.arrayBuffer();
        const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', bytes));
        const sha256 = Array.from(digest, byte => byte.toString(16).padStart(2, '0')).join('');
        return {bytes: bytes.byteLength, sha256};
    })()""")


def saved_file_info(remote_path, expected_size):
    with tempfile.TemporaryDirectory(prefix="ticketguard-txt-") as staging:
        local_path = Path(staging) / "saved.txt"
        deadline = time.monotonic() + 12
        while True:
            adb("pull", remote_path, str(local_path))
            data = local_path.read_bytes()
            if len(data) == expected_size or time.monotonic() >= deadline:
                return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            time.sleep(.5)


def verify_sample(base, sample, expected):
    tab = open_page(base + "/mobile-check?sample=" + sample)
    try:
        tab.wait("document.querySelector('#download')?.href.includes(" + json.dumps(sample) + ")")
        published = browser_reference(tab)
        if not published:
            raise RuntimeError(sample + " 배포된 원본 TXT를 읽을 수 없습니다.")
        before = list_reports(sample)
        tab.evaluate("document.querySelector('#download').click()")
        file = None
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            found = list_reports(sample) - before
            if len(found) == 1:
                file = found.pop()
                break
            tap(ui_nodes(), ["Download", "Download again", "Allow"])
            time.sleep(.4)
        if not file:
            raise RuntimeError(sample + " Android 다운로드 폴더에서 새 TXT가 확인되지 않았습니다.")

        saved = saved_file_info(file, published["bytes"])
        if saved != published:
            raise RuntimeError(f"{sample} 저장본 {saved}, 배포 응답 {published}, 빌드 기준 {expected}")

        tab.evaluate("document.querySelector('#pick').click()")
        filename = file.rsplit("/", 1)[-1]
        deadline = time.monotonic() + 35
        while time.monotonic() < deadline:
            nodes = ui_nodes()
            if tap(nodes, [filename]):
                break
            tap(nodes, ["Downloads", "Show roots", "Show more options", "Files", "Browse files"])
            time.sleep(.4)
        else:
            raise RuntimeError(sample + " Android 파일 선택창에서 재열기 실패")
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            proof = tab.evaluate("document.querySelector('#proof')?.hidden === false && document.querySelector('#details').textContent")
            if proof:
                break
            chooser = [node for node in ui_nodes() if node.get("package", "").endswith(".documentsui")]
            tap(chooser, ["SELECT", "Select", "OPEN", "Open", "선택", "열기"])
            time.sleep(.4)
        else:
            status = tab.evaluate("document.querySelector('#status')?.textContent")
            raise RuntimeError(f"{sample} 선택한 파일의 재열기 결과를 확인하지 못했습니다. {status}")
        return {"sample": sample, **saved, "published": published, "build": expected,
                "matches_build": saved == expected, "reopened": True, "browser_proof": proof}
    finally:
        try:
            tab.socket.close()
        finally:
            adb("forward", "--remove", "tcp:" + tab.port)


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
    for sample in SAMPLES:
        try:
            row = verify_sample(args.origin.rstrip("/"), sample, golden[sample])
        except (RuntimeError, OSError, subprocess.SubprocessError, websocket.WebSocketException) as error:
            row = {"sample": sample, "reopened": False, "error": str(error)}
            if emulator and os.getenv("GITHUB_ACTIONS") == "true":
                row["test_screen"] = list(dict.fromkeys(
                    node.get("text") or node.get("content-desc") for node in ui_nodes()
                    if node.get("text") or node.get("content-desc")
                ))[:24]
        evidence["rows"].append(row)
        result = json.dumps(evidence, ensure_ascii=False, indent=2)
        args.output.write_text(result + "\n", encoding="utf-8")
        print(json.dumps(row, ensure_ascii=False), flush=True)
    print(result, flush=True)
    if not all(row.get("reopened") and row.get("matches_build") for row in evidence["rows"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
