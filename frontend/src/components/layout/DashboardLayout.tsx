"use client";

import { FilterSidebar } from "@/components/filters/FilterSidebar";
import { PropertyMap } from "@/components/map/PropertyMap";
import { PropertyDrawer } from "@/components/properties/PropertyDrawer";
import { PropertyList } from "@/components/properties/PropertyList";
import { exportCsvUrl } from "@/lib/api";
import { useAppStore } from "@/lib/store";

export function DashboardLayout() {
  const { filters } = useAppStore();

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Top bar */}
      <header className="flex items-center justify-between px-5 py-3 bg-gray-900 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-orange-500 text-xl font-bold">PropFinder</span>
          <span className="text-gray-500 text-sm">Montgomery County · Distressed Deals</span>
        </div>
        <a
          href={exportCsvUrl(filters)}
          className="text-sm px-4 py-1.5 bg-orange-600 hover:bg-orange-500 text-white rounded font-medium transition-colors"
        >
          Export CSV
        </a>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        <FilterSidebar />

        {/* Property list */}
        <div className="w-80 flex-shrink-0 bg-gray-950 border-r border-gray-800 flex flex-col overflow-hidden">
          <PropertyList />
        </div>

        {/* Map */}
        <div className="flex-1 relative">
          <PropertyMap />
        </div>
      </div>

      <PropertyDrawer />
    </div>
  );
}
