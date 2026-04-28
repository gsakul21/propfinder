"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchProperty, exportCsvUrl } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { ScoreBadge } from "@/components/shared/ScoreBadge";
import { SignalBadge } from "@/components/shared/SignalBadge";
import type { SignalType } from "@/types";

const SIGNAL_EXPLANATIONS: Record<SignalType, string> = {
  tax_delinquency: "Owner has unpaid property taxes — financial stress signal.",
  foreclosure: "Active foreclosure case filed — owner may accept below-market offers.",
  absentee: "Owner does not reside at the property — higher motivation to sell.",
};

export function PropertyDrawer() {
  const { selectedPropertyId, setSelectedPropertyId, filters } = useAppStore();

  const { data: property, isLoading } = useQuery({
    queryKey: ["property", selectedPropertyId],
    queryFn: () => fetchProperty(selectedPropertyId!),
    enabled: !!selectedPropertyId,
  });

  if (!selectedPropertyId) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-96 bg-gray-900 border-l border-gray-800 z-50 flex flex-col shadow-2xl overflow-y-auto">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800 sticky top-0 bg-gray-900">
        <h2 className="text-base font-semibold text-white">Property Detail</h2>
        <button
          onClick={() => setSelectedPropertyId(null)}
          className="text-gray-500 hover:text-white text-xl leading-none"
          aria-label="Close"
        >
          ×
        </button>
      </div>

      {isLoading || !property ? (
        <div className="flex items-center justify-center flex-1 text-gray-500 text-sm">Loading...</div>
      ) : (
        <div className="p-5 space-y-6">
          {/* Address + score */}
          <div className="flex items-start gap-4">
            <ScoreBadge score={property.score} tier={property.tier} size="lg" />
            <div>
              <p className="font-semibold text-lg text-white leading-tight">{property.address}</p>
              <p className="text-sm text-gray-400">
                {[property.city, property.state, property.zip_code].filter(Boolean).join(", ")}
              </p>
              <p className="text-xs text-gray-500 mt-0.5 capitalize">{property.property_type.replace("_", " ")}</p>
            </div>
          </div>

          {/* Signals */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Distress Signals</h3>
            {property.signals.length === 0 ? (
              <p className="text-sm text-gray-500">No signals detected.</p>
            ) : (
              <div className="space-y-2">
                {(property.signals as SignalType[]).map((s) => (
                  <div key={s} className="rounded bg-gray-800 p-3">
                    <div className="mb-1"><SignalBadge type={s} /></div>
                    <p className="text-xs text-gray-400">{SIGNAL_EXPLANATIONS[s]}</p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Score Breakdown */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Score Breakdown</h3>
            <div className="bg-gray-800 rounded p-3 space-y-1 text-sm">
              {[
                ["Tax Delinquency", property.score_breakdown.tax],
                ["Foreclosure", property.score_breakdown.foreclosure],
                ["Absentee Owner", property.score_breakdown.absentee],
                ["Multi-Signal Bonus", property.score_breakdown.bonus],
                ["Conflict Penalty", -property.score_breakdown.penalty],
              ].map(([label, value]) => (
                <div key={label as string} className="flex justify-between">
                  <span className="text-gray-400">{label}</span>
                  <span className={Number(value) > 0 ? "text-green-400" : Number(value) < 0 ? "text-red-400" : "text-gray-500"}>
                    {Number(value) > 0 ? "+" : ""}{value}
                  </span>
                </div>
              ))}
              <div className="border-t border-gray-700 pt-1 flex justify-between font-semibold">
                <span className="text-gray-200">Total Score</span>
                <span className="text-white">{property.score}</span>
              </div>
            </div>
          </div>

          {/* Ownership */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Ownership</h3>
            <div className="bg-gray-800 rounded p-3 space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Owner</span>
                <span className="text-gray-200">{property.owner_name ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Mailing Address</span>
                <span className="text-gray-200 text-right max-w-[180px]">{property.owner_mailing_address ?? "—"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Absentee</span>
                <span className={property.is_absentee ? "text-yellow-400" : "text-gray-500"}>
                  {property.is_absentee ? "Yes" : "No"}
                </span>
              </div>
              {property.assessed_value != null && (
                <div className="flex justify-between">
                  <span className="text-gray-400">Assessed Value</span>
                  <span className="text-gray-200">${property.assessed_value.toLocaleString()}</span>
                </div>
              )}
            </div>
          </div>

          {/* Export */}
          <a
            href={exportCsvUrl(filters)}
            className="block w-full text-center py-2.5 bg-orange-600 hover:bg-orange-500 text-white text-sm font-semibold rounded transition-colors"
          >
            Export Lead List (CSV)
          </a>

          <p className="text-xs text-gray-600 text-center">Parcel ID: {property.parcel_id}</p>
        </div>
      )}
    </div>
  );
}
