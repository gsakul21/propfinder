import clsx from "clsx";
import type { SignalType } from "@/types";

interface Props {
  type: SignalType;
}

const LABELS: Record<SignalType, string> = {
  tax_delinquency: "Tax Delinquent",
  foreclosure: "Foreclosure",
  absentee: "Absentee Owner",
};

const STYLES: Record<SignalType, string> = {
  tax_delinquency: "bg-yellow-900/70 text-yellow-300 border-yellow-700",
  foreclosure: "bg-red-900/70 text-red-300 border-red-700",
  absentee: "bg-blue-900/70 text-blue-300 border-blue-700",
};

export function SignalBadge({ type }: Props) {
  return (
    <span className={clsx("text-xs px-2 py-0.5 rounded border font-medium", STYLES[type])}>
      {LABELS[type]}
    </span>
  );
}
