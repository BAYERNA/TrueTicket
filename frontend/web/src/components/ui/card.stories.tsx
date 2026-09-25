import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { Button } from "./button";
import { Card, CardContent, CardFooter, CardHeader } from "./card";

const meta = {
  title: "ui/Card",
  component: Card,
  tags: ["autodocs"],
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

// my-tickets 화면에서 실제로 쓰는 조합 — 예매 카드 하나.
export const ReservationCard: Story = {
  render: () => (
    <Card className="w-80">
      <CardHeader>
        <p className="text-muted-foreground text-xs">예매 확정</p>
        <p className="mt-1 font-mono text-sm">QR-9F2A-7B31</p>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground text-xs">예매 시각: 2026. 1. 1. 오후 8:00:00</p>
      </CardContent>
      <CardFooter>
        <Button variant="outline" size="sm">
          예매 취소
        </Button>
      </CardFooter>
    </Card>
  ),
};

export const CancelledReservationCard: Story = {
  render: () => (
    <Card className="w-80">
      <CardHeader>
        <p className="text-muted-foreground text-xs">취소됨</p>
      </CardHeader>
      <CardContent>
        <p className="text-muted-foreground text-xs">예매 시각: 2026. 1. 1. 오후 8:00:00</p>
      </CardContent>
    </Card>
  ),
};
