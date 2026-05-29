import { create } from "zustand";

interface OnboardingState {
  step: number;
  done: boolean;
  needsOnboarding: boolean;
  next: () => void;
  skip: () => void;
  reset: () => void;
  finish: () => void;
  startOnboarding: () => void;
}

export const useOnboardingStore = create<OnboardingState>((set) => ({
  step: 0,
  done: false,
  needsOnboarding: false,
  next: () => set((s) => ({ step: s.step + 1 })),
  skip: () => set({ done: true, step: 0 }),
  reset: () => set({ step: 0, done: false }),
  finish: () => set({ done: true, step: 0, needsOnboarding: false }),
  startOnboarding: () => set({ needsOnboarding: true, step: 1 }),
}));
