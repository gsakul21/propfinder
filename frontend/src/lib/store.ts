import { create } from "zustand";
import type { Filters, SignalType } from "@/types";

interface AppState {
  filters: Filters;
  page: number;
  selectedPropertyId: string | null;
  mapBounds: [number, number, number, number] | null;

  setFilter: <K extends keyof Filters>(key: K, value: Filters[K]) => void;
  resetFilters: () => void;
  setPage: (page: number) => void;
  setSelectedPropertyId: (id: string | null) => void;
  setMapBounds: (bounds: [number, number, number, number] | null) => void;
}

const DEFAULT_FILTERS: Filters = {
  min_score: null,
  county: null,
  property_type: null,
  distress_types: [],
  bbox: null,
};

export const useAppStore = create<AppState>((set) => ({
  filters: DEFAULT_FILTERS,
  page: 1,
  selectedPropertyId: null,
  mapBounds: null,

  setFilter: (key, value) =>
    set((s) => ({ filters: { ...s.filters, [key]: value }, page: 1 })),

  resetFilters: () => set({ filters: DEFAULT_FILTERS, page: 1 }),

  setPage: (page) => set({ page }),

  setSelectedPropertyId: (id) => set({ selectedPropertyId: id }),

  setMapBounds: (bounds) => set({ mapBounds: bounds }),
}));
