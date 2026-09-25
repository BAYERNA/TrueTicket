import { SellerProfileView } from "./seller-profile-view";

// SCR-09: 특정 판매자의 게시 이력과 상습성 지표를 확인한다.
export default async function SellerProfilePage({ params }: PageProps<"/admin/sellers/[sellerId]">) {
  const { sellerId } = await params;
  return <SellerProfileView sellerId={sellerId} />;
}
