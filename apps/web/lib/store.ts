import { create } from "zustand";
import type { Report } from "./report";
// Memory only. Sensitive names are never put in localStorage or sent automatically.
export const useReports = create<{
  reports: Report[];
  active: string | null;
  add: (r: Report) => void;
  select: (id: string) => void;
  clear: () => void;
}>((set) => ({
  reports: [],
  active: null,
  add: (r) =>
    set((s) => ({
      reports: [r, ...s.reports.filter((x) => x.scan.id !== r.scan.id)].slice(
        0,
        10,
      ),
      active: r.scan.id,
    })),
  select: (active) => set({ active }),
  clear: () => set({ reports: [], active: null }),
}));
