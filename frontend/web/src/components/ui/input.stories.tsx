import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { Input } from "./input";

const meta = {
  title: "ui/Input",
  component: Input,
  tags: ["autodocs"],
  args: {
    placeholder: "이메일을 입력하세요",
  },
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Email: Story = {
  args: { type: "email", placeholder: "you@example.com" },
};

export const Password: Story = {
  args: { type: "password", placeholder: "비밀번호" },
};

export const Disabled: Story = {
  args: { disabled: true, value: "수정할 수 없음", readOnly: true },
};

export const Invalid: Story = {
  args: { "aria-invalid": true, defaultValue: "잘못된 값" },
};
