"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchProperties } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { PropertyCard } from "./PropertyCard";
import type { Filters } from "@/types";

export function PropertyList() {
  const { filters, selectedPropertyId, setSelectedPropertyId } = useAppStore();

  const queryKey = ["properties", filters];
  const { data, isLoading, isError } = useQuery({
    queryKey,
    queryFn: () => fetchProperties(filters as Partial<Filters>),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-500 text-sm">
        Loading...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center h-40 text-red-400 text-sm">
        Failed to load properties.
      </div>
    );
  }

  const properties = data?.results ?? [];

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
        <span className="text-sm text-gray-400">
          {data?.total ?? 0} properties
        </span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {properties.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">
            No properties match your filters.
          </div>
        ) : (
          properties.map((p) => (
            <PropertyCard
              key={p.id}
              property={p}
              selected={selectedPropertyId === p.id}
              onSelect={() => setSelectedPropertyId(p.id)}
            />
          ))
        )}
      </div>
    </div>
  );
}
