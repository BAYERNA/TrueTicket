import { ListingDetailView } from "./listing-detail-view";

// SCR-08: 취득 부정성·상습 판매 스코어를 함께 확인해 암표 여부를 최종 판정한다.
export default async function ListingDetailPage({ params }: PageProps<"/admin/listings/[listingId]">) {
  const { listingId } = await params;
  return <ListingDetailView listingId={listingId} />;
}
