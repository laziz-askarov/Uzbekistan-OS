"use client";

import { useEffect, useSyncExternalStore } from "react";

const STORAGE_KEY = "uzbekistan-os-theme";
const THEME_CHANGE_EVENT = "uzbekistan-os-theme-change";

type Theme = "dark" | "light";
let inMemoryTheme: Theme | null = null;

function preferredTheme(): Theme {
  let savedTheme: string | null = null;
  try {
    savedTheme = window.localStorage.getItem(STORAGE_KEY);
  } catch {
    // The system preference remains available when storage is unavailable.
  }
  if (savedTheme === "dark" || savedTheme === "light") {
    return savedTheme;
  }
  if (inMemoryTheme !== null) {
    return inMemoryTheme;
  }
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
}

function serverTheme(): Theme {
  return "light";
}

function subscribeToTheme(onStoreChange: () => void) {
  const colorScheme = window.matchMedia("(prefers-color-scheme: dark)");
  const notifyWhenFollowingSystem = () => {
    let hasExplicitPreference = false;
    try {
      hasExplicitPreference =
        inMemoryTheme !== null ||
        window.localStorage.getItem(STORAGE_KEY) !== null;
    } catch {
      // A blocked storage API means the system preference is authoritative.
    }
    if (!hasExplicitPreference) {
      onStoreChange();
    }
  };
  const notify = () => onStoreChange();

  colorScheme.addEventListener("change", notifyWhenFollowingSystem);
  window.addEventListener("storage", notify);
  window.addEventListener(THEME_CHANGE_EVENT, notify);
  return () => {
    colorScheme.removeEventListener("change", notifyWhenFollowingSystem);
    window.removeEventListener("storage", notify);
    window.removeEventListener(THEME_CHANGE_EVENT, notify);
  };
}

export function ThemeToggle({ className }: { className: string }) {
  const theme = useSyncExternalStore(
    subscribeToTheme,
    preferredTheme,
    serverTheme,
  );

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const nextTheme = theme === "dark" ? "light" : "dark";

  return (
    <button
      aria-label={`Switch to ${nextTheme} mode`}
      aria-pressed={theme === "dark"}
      className={className}
      onClick={() => {
        inMemoryTheme = nextTheme;
        applyTheme(nextTheme);
        try {
          window.localStorage.setItem(STORAGE_KEY, nextTheme);
        } catch {
          // The current page still applies the preference when storage is blocked.
        }
        window.dispatchEvent(new Event(THEME_CHANGE_EVENT));
      }}
      type="button"
    >
      <span aria-hidden="true">{theme === "dark" ? "☀" : "◐"}</span>
      <span>{theme === "dark" ? "Light" : "Dark"}</span>
    </button>
  );
}
