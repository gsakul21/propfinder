"use client";

import { useQuery } from "@tanstack/react-query";
import { fetchProperties } from "@/lib/api";
import { useAppStore } from "@/lib/store";
import { PropertyCard } from "./PropertyCard";
import type { Filters } from "@/types";

const PAGE_SIZE = 50;

export function PropertyList() {
  const { filters, page, setPage, selectedPropertyId, setSelectedPropertyId } = useAppStore();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["properties", filters, page],
    queryFn: () => fetchProperties({ ...(filters as Partial<Filters>), page, limit: PAGE_SIZE }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;

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
        {totalPages > 1 && (
          <span className="text-xs text-gray-500">
            page {page} of {totalPages}
          </span>
        )}
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

      {totalPages > 1 && (
        <div className="px-4 py-3 border-t border-gray-800 flex items-center justify-between gap-2">
          <button
            onClick={() => setPage(page - 1)}
            disabled={page <= 1}
            className="px-3 py-1 text-xs rounded bg-gray-800 text-gray-300 disabled:opacity-30 hover:bg-gray-700 disabled:cursor-not-allowed"
          >
            Previous
          </button>
          <span className="text-xs text-gray-500">{page} / {totalPages}</span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page >= totalPages}
            className="px-3 py-1 text-xs rounded bg-gray-800 text-gray-300 disabled:opacity-30 hover:bg-gray-700 disabled:cursor-not-allowed"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
