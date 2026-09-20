// ticket-service 응답과 매칭되는 타입 (backend/ticket-service DTO 참고)

export type EventCategory = "KBO" | "CONCERT" | "MUSICAL" | "ETC";

export interface AuthResponse {
  accessToken: string;
  tokenType: "Bearer";
  expiresAt: string;
  userId: string;
  email: string;
  role: string;
}

export interface TrueTicketEvent {
  id: string;
  title: string;
  category: EventCategory;
  venue: string;
  eventDatetime: string;
  basePrice: number;
}

export type SeatStatus = "AVAILABLE" | "HELD" | "RESERVED" | "SOLD";

export interface Seat {
  id: string;
  eventId: string;
  seatSection: string;
  seatRow: string;
  seatNumber: number;
  price: number;
  status: SeatStatus;
}

export type ReservationStatus = "PENDING" | "CONFIRMED" | "CANCELLED";

export interface ReservationResponse {
  reservationId: string;
  userId: string;
  eventId: string;
  seatId: string;
  status: ReservationStatus;
  qrCode: string | null;
  reservedAt: string;
}

// queue-service 응답
export interface QueueStatusResponse {
  eventId: string;
  userId: string;
  rank: number;
  waitingCount: number;
  admitted: boolean;
}

// resale-monitor-service 응답
export interface ResaleListing {
  listingId: string;
  sellerId: string;
  platformName: string;
  eventTitleMatched: string;
  listedPrice: number;
  priceAnomalyScore: number;
}

export interface SellerProfile {
  sellerId: string;
  platformName: string;
  externalSellerId: string;
  listingCount: number;
  habitualScore: number;
}
