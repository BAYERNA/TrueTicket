const SAMPLES = [
  {
    id: "SP-FEST",
    label: "페스티벌 · 고가 제시",
    name: "별빛 페스티벌",
    date: "2026-12-12",
    text: "2026-12-12 별빛 페스티벌 VIP 한 장 30만원. 여러 장 보유, 입금 우대.",
    report: {
      level: "CAUTION",
      facts: [
        "글에 적힌 문구  “VIP 한 장 30만원”",
        "글에 적힌 문구  “여러 장 보유”",
        "글에 적힌 문구  “입금 우대”",
        "가상 행사 목록  별빛 페스티벌 · 2026-12-12",
        "VIP석 기준가 120,000원 · SRC-DEMO",
        "장당 제시액 300,000원 · 기준가 대비 차액 +180,000원",
        "가상 기준가 대비 +150.0%",
        "등록 정책  양도 금지. 현장에서 예매자 신분증을 대조한다. · SRC-DEMO",
      ],
      signals: [
        "제시액이 VIP석 가상 기준가보다 180,000원 높습니다. 근거 SRC-DEMO.",
        "가상 정책상 양도가 제한되어 입장이 거절될 수 있습니다. 근거 SRC-DEMO.",
        "글의 “여러 장 보유” 문구는 보유 수량에 관한 작성자의 주장입니다.",
      ],
      unknowns: [
        "글쓴이의 실제 구입가와 할인 여부",
        "티켓 소유권, 판매처 동의, 상습·영업 여부",
      ],
      actions: [
        "송금 전에 주최사나 공식 예매처에서 양도 및 입장 조건을 확인하세요.",
      ],
      benchmark_source:
        "가상 시연 자료 · 가상 시연 가격표·양도 정책 · SRC-DEMO · 2026-11-20",
      policy_source:
        "가상 시연 자료 · 가상 시연 가격표·양도 정책 · SRC-DEMO · 2026-11-20",
      premium_pct_vs_list: 150.0,
      premium_krw: 180000,
      list_price_krw: 120000,
      asking_price_krw: 300000,
      legal_verdict: "NOT_DETERMINED",
      extraction_mode: "프리셋",
    },
  },
  {
    id: "SP-MUS",
    label: "뮤지컬 · 정가와 입장 조건",
    name: "뮤지컬 밤의 서약",
    date: "2026-12-19",
    text: "2026-12-19 뮤지컬 밤의 서약 R석 한 장 11만원. 모바일 티켓 캡처를 보내드립니다.",
    report: {
      level: "CAUTION",
      facts: [
        "글에 적힌 문구  “R석 한 장 11만원”",
        "글에 적힌 문구  “모바일 티켓 캡처”",
        "가상 행사 목록  뮤지컬 밤의 서약 · 2026-12-19",
        "R석 기준가 110,000원 · SRC-DEMO",
        "장당 제시액 110,000원 · 기준가 대비 차액 +0원",
        "가상 기준가 대비 +0.0%",
        "등록 정책  양도 금지. 모바일 티켓 캡처로 입장할 수 없다. · SRC-DEMO",
      ],
      signals: [
        "가상 정책상 양도가 제한되어 입장이 거절될 수 있습니다. 근거 SRC-DEMO.",
      ],
      unknowns: [
        "글쓴이의 실제 구입가와 할인 여부",
        "티켓 소유권, 판매처 동의, 상습·영업 여부",
      ],
      actions: [
        "송금 전에 주최사나 공식 예매처에서 양도 및 입장 조건을 확인하세요.",
      ],
      benchmark_source:
        "가상 시연 자료 · 가상 시연 가격표·양도 정책 · SRC-DEMO · 2026-11-20",
      policy_source:
        "가상 시연 자료 · 가상 시연 가격표·양도 정책 · SRC-DEMO · 2026-11-20",
      premium_pct_vs_list: 0.0,
      premium_krw: 0,
      list_price_krw: 110000,
      asking_price_krw: 110000,
      legal_verdict: "NOT_DETERMINED",
      extraction_mode: "프리셋",
    },
  },
  {
    id: "SP-BASE",
    label: "프로야구 · 공식 선물하기",
    name: "시티 블루스 vs 리버 레즈",
    date: "2027-04-03",
    text: "2027-04-03 시티 블루스 vs 리버 레즈 테이블석 한 장 6만원. 양도 방식은 문의 바랍니다.",
    report: {
      level: "REVIEW",
      facts: [
        "글에 적힌 문구  “테이블석 한 장 6만원”",
        "글에 적힌 문구  “양도 방식은 문의 바랍니다”",
        "가상 행사 목록  시티 블루스 vs 리버 레즈 · 2027-04-03",
        "TABLE석 기준가 60,000원 · SRC-DEMO",
        "장당 제시액 60,000원 · 기준가 대비 차액 +0원",
        "가상 기준가 대비 +0.0%",
        "등록 정책  공식 앱의 선물하기로 받은 티켓인지 확인해야 한다. · SRC-DEMO",
      ],
      signals: [],
      unknowns: [
        "글쓴이의 실제 구입가와 할인 여부",
        "티켓 소유권, 판매처 동의, 상습·영업 여부",
        "공식 앱의 선물하기 등 지정된 이전 절차를 거쳤는지 확인이 필요합니다.",
      ],
      actions: [
        "송금 전에 주최사나 공식 예매처에서 양도 및 입장 조건을 확인하세요.",
      ],
      benchmark_source:
        "가상 시연 자료 · 가상 시연 가격표·양도 정책 · SRC-DEMO · 2026-11-20",
      policy_source:
        "가상 시연 자료 · 가상 시연 가격표·양도 정책 · SRC-DEMO · 2026-11-20",
      premium_pct_vs_list: 0.0,
      premium_krw: 0,
      list_price_krw: 60000,
      asking_price_krw: 60000,
      legal_verdict: "NOT_DETERMINED",
      extraction_mode: "프리셋",
    },
  },
];
const HANBIT = {
  organizer: "한빛 콘서트 가상 운영팀",
  source: "post-017",
  name: "2026 한빛 겨울 콘서트",
  session: "1회차",
  sessionId: "event-001-session-01",
  date: "2026-12-12",
  seats: ["A-01-01", "A-01-02"],
  asking: 137000,
  listed: 110000,
  evidence: [
    "정가 장당 11만 원",
    "추가금 장당 27,000원",
    "두 장 합계 274,000원",
  ],
  text: "2026 한빛 겨울 콘서트 1회차. R석 A-01-01, A-01-02 2장. 정가 장당 11만 원, 추가금 장당 27,000원. 두 장 합계 274,000원. 아옮 가능. 채팅은 퇴근 뒤에 확인해요. 좌석 확인은 예매 화면으로 해요.",
};
const BOOKINGS = [
  {
    booking: "booking-0001",
    seat: "A-01-01",
    grade: "R",
    paid: 112000,
    score: 0.84,
  },
  {
    booking: "booking-0002",
    seat: "A-01-02",
    grade: "R",
    paid: 112000,
    score: 0.84,
  },
];
const WAITLIST = [
  {
    id: "fan-001",
    grade: "R",
    joined: "2026-11-16T12:00:00+09:00",
  },
  {
    id: "fan-002",
    grade: "S",
    joined: "2026-11-16T12:03:00+09:00",
  },
  {
    id: "fan-003",
    grade: "R",
    joined: "2026-11-16T12:06:00+09:00",
  },
  {
    id: "fan-004",
    grade: "S",
    joined: "2026-11-16T12:09:00+09:00",
  },
  {
    id: "fan-005",
    grade: "R",
    joined: "2026-11-16T12:12:00+09:00",
  },
  {
    id: "fan-006",
    grade: "S",
    joined: "2026-11-16T12:15:00+09:00",
  },
  {
    id: "fan-007",
    grade: "R",
    joined: "2026-11-16T12:18:00+09:00",
  },
  {
    id: "fan-008",
    grade: "S",
    joined: "2026-11-16T12:21:00+09:00",
  },
  {
    id: "fan-009",
    grade: "R",
    joined: "2026-11-16T12:24:00+09:00",
  },
  {
    id: "fan-010",
    grade: "S",
    joined: "2026-11-16T12:27:00+09:00",
  },
  {
    id: "fan-011",
    grade: "R",
    joined: "2026-11-16T12:30:00+09:00",
  },
  {
    id: "fan-012",
    grade: "S",
    joined: "2026-11-16T12:33:00+09:00",
  },
  {
    id: "fan-013",
    grade: "R",
    joined: "2026-11-16T12:36:00+09:00",
  },
  {
    id: "fan-014",
    grade: "S",
    joined: "2026-11-16T12:39:00+09:00",
  },
  {
    id: "fan-015",
    grade: "R",
    joined: "2026-11-16T12:42:00+09:00",
  },
  {
    id: "fan-016",
    grade: "S",
    joined: "2026-11-16T12:45:00+09:00",
  },
  {
    id: "fan-017",
    grade: "R",
    joined: "2026-11-16T12:48:00+09:00",
  },
  {
    id: "fan-018",
    grade: "S",
    joined: "2026-11-16T12:51:00+09:00",
  },
  {
    id: "fan-019",
    grade: "R",
    joined: "2026-11-16T12:54:00+09:00",
  },
  {
    id: "fan-020",
    grade: "S",
    joined: "2026-11-16T12:57:00+09:00",
  },
  {
    id: "fan-021",
    grade: "R",
    joined: "2026-11-16T13:00:00+09:00",
  },
  {
    id: "fan-022",
    grade: "S",
    joined: "2026-11-16T13:03:00+09:00",
  },
  {
    id: "fan-023",
    grade: "R",
    joined: "2026-11-16T13:06:00+09:00",
  },
  {
    id: "fan-024",
    grade: "S",
    joined: "2026-11-16T13:09:00+09:00",
  },
  {
    id: "fan-025",
    grade: "R",
    joined: "2026-11-16T13:12:00+09:00",
  },
];
