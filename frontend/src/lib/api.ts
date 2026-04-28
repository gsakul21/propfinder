import type { Filters, PropertyDetail, PropertyListResponse } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function buildParams(filters: Partial<Filters> & { page?: number; limit?: number }): URLSearchParams {
  const p = new URLSearchParams();
  if (filters.min_score != null) p.set("min_score", String(filters.min_score));
  if (filters.county) p.set("county", filters.county);
  if (filters.property_type) p.set("property_type", filters.property_type);
  if (filters.distress_types?.length) {
    filters.distress_types.forEach((t) => p.append("distress_types", t));
  }
  if (filters.bbox) p.set("bbox", filters.bbox.join(","));
  if (filters.page) p.set("page", String(filters.page));
  if (filters.limit) p.set("limit", String(filters.limit));
  return p;
}

export async function fetchProperties(
  filters: Partial<Filters> & { page?: number; limit?: number }
): Promise<PropertyListResponse> {
  const params = buildParams(filters);
  const res = await fetch(`${BASE}/api/v1/properties?${params}`);
  if (!res.ok) throw new Error("Failed to fetch properties");
  return res.json();
}

export async function fetchProperty(id: string): Promise<PropertyDetail> {
  const res = await fetch(`${BASE}/api/v1/properties/${id}`);
  if (!res.ok) throw new Error("Property not found");
  return res.json();
}

export function exportCsvUrl(filters: Partial<Filters>): string {
  const params = buildParams(filters);
  return `${BASE}/api/v1/exports?${params}`;
}
