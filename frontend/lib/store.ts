import { create } from "zustand";
import { ProgressUpdate } from "./types";

interface Job {
  job_id: string;
  status: string;
}

interface JobState {
  job: Job | null;
  progress: ProgressUpdate | null;
  logs: string[];
  isRunning: boolean;
  setJob: (job: Job | null) => void;
  setProgress: (progress: ProgressUpdate | null) => void;
  addLog: (log: string) => void;
  clearLogs: () => void;
  setRunning: (isRunning: boolean) => void;
}

export const useJobStore = create<JobState>((set) => ({
  job: null,
  progress: null,
  logs: [],
  isRunning: false,
  setJob: (job) => set({ job }),
  setProgress: (progress) => set({ progress }),
  addLog: (log) => set((state) => ({ logs: [...state.logs, log] })),
  clearLogs: () => set({ logs: [] }),
  setRunning: (isRunning) => set({ isRunning }),
}));
