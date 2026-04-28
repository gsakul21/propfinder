"use client";

import { useAppStore } from "@/lib/store";
import type { SignalType } from "@/types";

const SIGNAL_OPTIONS: { value: SignalType; label: string }[] = [
  { value: "tax_delinquency", label: "Tax Delinquency" },
  { value: "foreclosure", label: "Foreclosure" },
  { value: "absentee", label: "Absentee Owner" },
];

const PROPERTY_TYPES = ["residential", "commercial", "multi_family", "land"];

export function FilterSidebar() {
  const { filters, setFilter, resetFilters } = useAppStore();

  function toggleSignal(type: SignalType) {
    const current = filters.distress_types;
    const next = current.includes(type)
      ? current.filter((t) => t !== type)
      : [...current, type];
    setFilter("distress_types", next);
  }

  return (
    <aside className="w-64 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col h-full overflow-y-auto">
      <div className="p-4 border-b border-gray-800">
        <h2 className="text-lg font-semibold text-white">Filters</h2>
      </div>

      <div className="p-4 space-y-6 flex-1">
        {/* Min Score */}
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Min Score: <span className="text-white">{filters.min_score ?? 0}</span>
          </label>
          <input
            type="range"
            min={0}
            max={100}
            step={5}
            value={filters.min_score ?? 0}
            onChange={(e) => setFilter("min_score", Number(e.target.value) || null)}
            className="w-full accent-orange-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0</span><span>50</span><span>100</span>
          </div>
        </div>

        {/* Distress Signals */}
        <div>
          <p className="text-sm font-medium text-gray-400 mb-2">Distress Signals</p>
          <div className="space-y-2">
            {SIGNAL_OPTIONS.map(({ value, label }) => (
              <label key={value} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.distress_types.includes(value)}
                  onChange={() => toggleSignal(value)}
                  className="accent-orange-500"
                />
                <span className="text-sm text-gray-300">{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Property Type */}
        <div>
          <label className="block text-sm font-medium text-gray-400 mb-2">Property Type</label>
          <select
            value={filters.property_type ?? ""}
            onChange={(e) => setFilter("property_type", e.target.value || null)}
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm text-gray-100 focus:outline-none focus:border-orange-500"
          >
            <option value="">All Types</option>
            {PROPERTY_TYPES.map((t) => (
              <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1).replace("_", " ")}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="p-4 border-t border-gray-800">
        <button
          onClick={resetFilters}
          className="w-full py-2 text-sm text-gray-400 hover:text-white border border-gray-700 hover:border-gray-500 rounded transition-colors"
        >
          Reset Filters
        </button>
      </div>
    </aside>
  );
}
