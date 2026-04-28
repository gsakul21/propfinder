import { create } from "zustand";
import type { Filters, SignalType } from "@/types";

interface AppState {
  filters: Filters;
  selectedPropertyId: string | null;
  mapBounds: [number, number, number, number] | null;

  setFilter: <K extends keyof Filters>(key: K, value: Filters[K]) => void;
  resetFilters: () => void;
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
  selectedPropertyId: null,
  mapBounds: null,

  setFilter: (key, value) =>
    set((s) => ({ filters: { ...s.filters, [key]: value } })),

  resetFilters: () => set({ filters: DEFAULT_FILTERS }),

  setSelectedPropertyId: (id) => set({ selectedPropertyId: id }),

  setMapBounds: (bounds) => set({ mapBounds: bounds }),
}));
