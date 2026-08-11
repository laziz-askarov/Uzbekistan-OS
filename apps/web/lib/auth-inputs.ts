export function normalizeEmail(input: string) {
  const email = input.trim().toLowerCase();
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? email : null;
}

export function normalizeInternationalPhone(input: string) {
  const compact = input.trim().replace(/[\s().-]/g, "");
  const candidate = compact.startsWith("+")
    ? compact
    : /^998\d{9}$/.test(compact)
      ? `+${compact}`
      : /^\d{9}$/.test(compact)
        ? `+998${compact}`
        : null;
  return candidate && /^\+[1-9]\d{7,14}$/.test(candidate) ? candidate : null;
}
