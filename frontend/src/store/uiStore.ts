import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeMode = "dark";

interface UiState {
  selectedJobId: string | null;
  statusFilter: string;
  languageFilter: string;
  searchText: string;
  sidebarOpen: boolean;
  themeMode: ThemeMode;
  setSelectedJobId: (jobId: string | null) => void;
  setFilters: (payload: { statusFilter?: string; languageFilter?: string; searchText?: string }) => void;
  toggleSidebar: () => void;
  closeSidebar: () => void;
}

export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      selectedJobId: null,
      statusFilter: "all",
      languageFilter: "all",
      searchText: "",
      sidebarOpen: false,
      themeMode: "dark",
      setSelectedJobId: (selectedJobId: string | null) => set({ selectedJobId }),
      setFilters: (payload: { statusFilter?: string; languageFilter?: string; searchText?: string }) =>
        set((state: UiState) => ({
          statusFilter: payload.statusFilter ?? state.statusFilter,
          languageFilter: payload.languageFilter ?? state.languageFilter,
          searchText: payload.searchText ?? state.searchText,
        })),
      toggleSidebar: () => set((state: UiState) => ({ sidebarOpen: !state.sidebarOpen })),
      closeSidebar: () => set({ sidebarOpen: false }),
    }),
    {
      name: "ui-store",
      partialize: (state: UiState) => ({
        selectedJobId: state.selectedJobId,
        statusFilter: state.statusFilter,
        languageFilter: state.languageFilter,
        searchText: state.searchText,
      }),
    },
  ),
);
