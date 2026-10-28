import type { BrandSectionId } from "@/lib/brand-sections";

/**
 * The kit's four filled section icons on a 24-unit grid (passport, banknote,
 * metro carriage, house). "planning" is not in the kit; its pin follows the
 * same filled style until the kit adds one.
 */
const PATHS: Record<BrandSectionId, string> = {
  visas:
    "M7.5,2 H16.5 A3 3 0 0 1 19.5,5 V19 A3 3 0 0 1 16.5,22 H7.5 A3 3 0 0 1 4.5,19 V5 A3 3 0 0 1 7.5,2 Z M7.8,10 A4.2 4.2 0 1 0 16.2,10 A4.2 4.2 0 1 0 7.8,10 Z M9.8,10 A2.2 2.2 0 1 0 14.2,10 A2.2 2.2 0 1 0 9.8,10 Z M9,16 H15 A1 1 0 0 1 16,17 V17 A1 1 0 0 1 15,18 H9 A1 1 0 0 1 8,17 V17 A1 1 0 0 1 9,16 Z",
  money:
    "M5,6 H19 A3 3 0 0 1 22,9 V15 A3 3 0 0 1 19,18 H5 A3 3 0 0 1 2,15 V9 A3 3 0 0 1 5,6 Z M8.8,12 A3.2 3.2 0 1 0 15.2,12 A3.2 3.2 0 1 0 8.8,12 Z M4.9,12 A1.1 1.1 0 1 0 7.1,12 A1.1 1.1 0 1 0 4.9,12 Z M16.9,12 A1.1 1.1 0 1 0 19.1,12 A1.1 1.1 0 1 0 16.9,12 Z",
  transport:
    "M9,2.5 H15 A4 4 0 0 1 19,6.5 V14.5 A4 4 0 0 1 15,18.5 H9 A4 4 0 0 1 5,14.5 V6.5 A4 4 0 0 1 9,2.5 Z M9.1,5.5 H14.9 A1.6 1.6 0 0 1 16.5,7.1 V8.9 A1.6 1.6 0 0 1 14.9,10.5 H9.1 A1.6 1.6 0 0 1 7.5,8.9 V7.1 A1.6 1.6 0 0 1 9.1,5.5 Z M7.5,14.6 A1.3 1.3 0 1 0 10.1,14.6 A1.3 1.3 0 1 0 7.5,14.6 Z M13.9,14.6 A1.3 1.3 0 1 0 16.5,14.6 A1.3 1.3 0 1 0 13.9,14.6 Z M7,18 H9.6 L8.2,22 H5.6 Z M17,18 H14.4 L15.8,22 H18.4 Z",
  planning:
    "M12,2.2 A7.3 7.3 0 0 1 19.3,9.5 C19.3,14.6 12,22 12,22 C12,22 4.7,14.6 4.7,9.5 A7.3 7.3 0 0 1 12,2.2 Z M12,6.6 A2.9 2.9 0 1 0 12,12.4 A2.9 2.9 0 1 0 12,6.6 Z",
  living:
    "M12,2.4 L21.2,9.6 C21.7,10 22,10.6 22,11.2 V19.5 A2.5 2.5 0 0 1 19.5,22 H4.5 A2.5 2.5 0 0 1 2,19.5 V11.2 C2,10.6 2.3,10 2.8,9.6 Z M9.8,22 V16.6 C9.8,14.8 10.7,13.6 12,12.8 C13.3,13.6 14.2,14.8 14.2,16.6 V22 Z",
};

export function SectionIcon({
  id,
  className,
}: {
  id: BrandSectionId;
  className?: string;
}) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      width="24"
      height="24"
      aria-hidden="true"
      focusable="false"
    >
      <path fill="currentColor" fillRule="evenodd" d={PATHS[id]} />
    </svg>
  );
}
