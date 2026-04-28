"use client";

import clsx from "clsx";
import { ScoreBadge } from "@/components/shared/ScoreBadge";
import { SignalBadge } from "@/components/shared/SignalBadge";
import type { PropertySummary, SignalType } from "@/types";

interface Props {
  property: PropertySummary;
  selected: boolean;
  onSelect: () => void;
}

export function PropertyCard({ property, selected, onSelect }: Props) {
  const { address, city, state, zip_code, score, tier, signals, property_type, assessed_value } = property;

  return (
    <button
      onClick={onSelect}
      className={clsx(
        "w-full text-left p-4 border-b border-gray-800 hover:bg-gray-800/60 transition-colors",
        selected && "bg-gray-800 border-l-2 border-l-orange-500"
      )}
    >
      <div className="flex gap-3 items-start">
        <ScoreBadge score={score} tier={tier} />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-gray-100 truncate">{address}</p>
          <p className="text-sm text-gray-400">
            {[city, state, zip_code].filter(Boolean).join(", ")}
          </p>
          <div className="flex flex-wrap gap-1 mt-2">
            {(signals as SignalType[]).map((s) => (
              <SignalBadge key={s} type={s} />
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-1 capitalize">
            {property_type.replace("_", " ")}
            {assessed_value != null && ` · $${assessed_value.toLocaleString()}`}
          </p>
        </div>
      </div>
    </button>
  );
}
