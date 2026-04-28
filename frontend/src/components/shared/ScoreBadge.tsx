import clsx from "clsx";
import type { Tier } from "@/types";

interface Props {
  score: number;
  tier: Tier;
  size?: "sm" | "lg";
}

const TIER_STYLES: Record<Tier, string> = {
  hot: "bg-red-500 text-white",
  warm: "bg-orange-500 text-white",
  cold: "bg-gray-600 text-gray-200",
};

export function ScoreBadge({ score, tier, size = "sm" }: Props) {
  return (
    <span
      className={clsx(
        "inline-flex items-center justify-center font-bold rounded-full",
        TIER_STYLES[tier],
        size === "sm" ? "w-9 h-9 text-sm" : "w-16 h-16 text-2xl"
      )}
    >
      {score}
    </span>
  );
}
