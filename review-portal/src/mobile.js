const sample = document.querySelector("#sample");
const picker = document.querySelector("#pick");
const download = document.querySelector("#download");
const status = document.querySelector("#status");
const details = document.querySelector("#details");
const proof = document.querySelector("#proof");
const browser = document.querySelector("#browser");
const initial = new URLSearchParams(location.search).get("sample");
if (Array.from(sample.options).some(option => option.value === initial)) sample.value = initial;
let revision = 0;
let proofText = "";

function reset() {
  revision += 1;
  picker.value = "";
  proof.hidden = true;
  proofText = "";
  status.textContent = "파일 선택 대기";
  download.href = "/reports/" + sample.value + ".txt";
}
sample.addEventListener("change", reset);
reset();

async function digest(bytes) {
  const hash = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return Array.from(hash, byte => byte.toString(16).padStart(2, "0")).join("");
}

picker.addEventListener("change", async () => {
  const round = ++revision;
  const file = picker.files[0];
  const id = sample.value;
  proof.hidden = true;
  proofText = "";
  if (!file) {status.textContent = "파일 선택 대기"; return;}
  if (file.size > 64 * 1024) {status.textContent = "이 시연에서 다운로드한 작은 TXT 파일을 선택하세요."; return;}
  status.textContent = "파일 내용을 대조하고 있습니다.";
  try {
    const response = await fetch(download.href, {cache: "no-store"});
    if (!response.ok) throw new Error("원본을 불러올 수 없습니다. 연결을 확인하고 다시 선택하세요.");
    const [expected, saved] = await Promise.all([response.arrayBuffer(), file.arrayBuffer()]);
    const [expectedHash, fileHash] = await Promise.all([digest(expected), digest(saved)]);
    if (fileHash !== expectedHash) throw new Error("선택한 사례의 원본과 다릅니다. 파일과 사례를 다시 확인하세요.");
    const text = new TextDecoder("utf-8", {fatal:true}).decode(saved);
    const parts = ["확인된 사실","의심 정황","확인 불가","권고 행동"];
    const price = {"SP-FEST":"300,000원","SP-MUS":"110,000원","SP-BASE":"60,000원"}[id];
    if (!parts.every(part => text.includes("["+part+"]")) || !text.includes(price)) throw new Error("파일의 한글 항목 또는 사례 금액을 확인할 수 없습니다.");
    if (round !== revision) return;
    details.textContent = sample.selectedOptions[0].text + " · " + file.size.toLocaleString("ko-KR") + "바이트 · 장당 제시액 " + price + " · 한글 4개 구획 일치";
    browser.textContent = "브라우저가 보고한 환경　" + navigator.userAgent;
    proofText = "TicketGuard AI | TXT 재열기\n"+details.textContent+"\nSHA-256 "+fileHash+"\n"+browser.textContent+"\n"+new Date().toISOString();
    status.textContent = "저장 후 다시 연 파일이 원본과 일치합니다.";
    proof.hidden = false;
  } catch (error) {
    if (round === revision) status.textContent = error.message || "파일을 다시 선택하세요.";
  }
});
document.querySelector("#copy").addEventListener("click", async () => {
  if (!proofText) return;
  try {await navigator.clipboard.writeText(proofText); status.textContent = "확인 결과를 복사했습니다.";}
  catch {status.textContent = proofText;}
});
