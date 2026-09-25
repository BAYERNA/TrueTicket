// ticket-service 응답과 매칭되는 스키마 (backend/ticket-service DTO 참고).
// TypeScript는 컴파일 타임에만 타입을 보장하고, 백엔드가 실제로 이 계약을 지키는지는
// 검증하지 않는다 — 스키마를 단일 소스로 두고 타입은 여기서 유도해, api-client가 응답을
// 런타임에 그대로 검증할 수 있게 한다.
import { z } from "zod";

export const EventCategorySchema = z.enum(["KBO", "CONCERT", "MUSICAL", "ETC"]);
export type EventCategory = z.infer<typeof EventCategorySchema>;

export const AuthResponseSchema = z.object({
  accessToken: z.string(),
  tokenType: z.literal("Bearer"),
  expiresAt: z.string(),
  userId: z.string(),
  email: z.string(),
  role: z.string(),
});
export type AuthResponse = z.infer<typeof AuthResponseSchema>;

export const TrueTicketEventSchema = z.object({
  id: z.string(),
  title: z.string(),
  category: EventCategorySchema,
  venue: z.string(),
  eventDatetime: z.string(),
  basePrice: z.number(),
});
export type TrueTicketEvent = z.infer<typeof TrueTicketEventSchema>;

export const SeatStatusSchema = z.enum(["AVAILABLE", "HELD", "RESERVED", "SOLD"]);
export type SeatStatus = z.infer<typeof SeatStatusSchema>;

export const SeatSchema = z.object({
  id: z.string(),
  eventId: z.string(),
  seatSection: z.string(),
  seatRow: z.string(),
  seatNumber: z.number(),
  price: z.number(),
  status: SeatStatusSchema,
});
export type Seat = z.infer<typeof SeatSchema>;
export const SeatListSchema = z.array(SeatSchema);

export const ReservationStatusSchema = z.enum(["PENDING", "CONFIRMED", "CANCELLED"]);
export type ReservationStatus = z.infer<typeof ReservationStatusSchema>;

export const ReservationResponseSchema = z.object({
  reservationId: z.string(),
  userId: z.string(),
  eventId: z.string(),
  seatId: z.string(),
  status: ReservationStatusSchema,
  qrCode: z.string().nullable(),
  reservedAt: z.string(),
  expiresAt: z.string(),
});
export type ReservationResponse = z.infer<typeof ReservationResponseSchema>;
export const ReservationListSchema = z.array(ReservationResponseSchema);

export const PaymentStatusSchema = z.enum(["PENDING", "PAID", "FAILED", "REFUNDED"]);
export type PaymentStatus = z.infer<typeof PaymentStatusSchema>;

export const PaymentResponseSchema = z.object({
  paymentId: z.string(),
  reservationId: z.string(),
  providerPaymentId: z.string(),
  amount: z.number(),
  status: PaymentStatusSchema,
  reservationExpiresAt: z.string(),
  mockCheckoutToken: z.string(),
});
export type PaymentResponse = z.infer<typeof PaymentResponseSchema>;

// queue-service 응답
export const QueueStatusResponseSchema = z.object({
  eventId: z.string(),
  userId: z.string(),
  rank: z.number(),
  waitingCount: z.number(),
  admitted: z.boolean(),
});
export type QueueStatusResponse = z.infer<typeof QueueStatusResponseSchema>;

// resale-monitor-service 응답
export const ResaleListingSchema = z.object({
  listingId: z.string(),
  sellerId: z.string(),
  platformName: z.string(),
  eventTitleMatched: z.string(),
  listedPrice: z.number(),
  priceAnomalyScore: z.number(),
});
export type ResaleListing = z.infer<typeof ResaleListingSchema>;
export const ResaleListingListSchema = z.array(ResaleListingSchema);

export const SellerProfileSchema = z.object({
  sellerId: z.string(),
  platformName: z.string(),
  externalSellerId: z.string(),
  listingCount: z.number(),
  habitualScore: z.number(),
});
export type SellerProfile = z.infer<typeof SellerProfileSchema>;
