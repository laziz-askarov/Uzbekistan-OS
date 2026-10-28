import { z } from "zod";

export type Option = { value: string; label: string };

export const INTERESTS: readonly Option[] = [
  { value: "architecture", label: "Architecture and history" },
  { value: "food", label: "Food, markets and home cooking" },
  { value: "crafts", label: "Crafts, textiles and ceramics" },
  { value: "trains", label: "Trains and slow travel" },
  { value: "photography", label: "Photography" },
  { value: "nature", label: "Mountains, desert and the Aral Sea" },
  { value: "culture", label: "People, music and everyday life" },
];

export const COMFORT_LEVELS: readonly Option[] = [
  { value: "simple", label: "Simple: guesthouses, shared trains, lower cost" },
  {
    value: "comfortable",
    label: "Comfortable: good hotels and private transfers",
  },
  { value: "premium", label: "Premium: the best available in each city" },
];

export const BUDGET_BANDS: readonly Option[] = [
  { value: "under-120", label: "Under $120 per person per day" },
  { value: "120-200", label: "$120 to $200 per person per day" },
  { value: "200-350", label: "$200 to $350 per person per day" },
  { value: "350-plus", label: "More than $350 per person per day" },
  { value: "not-sure", label: "Not sure yet" },
];

const values = (options: readonly Option[]) =>
  options.map((option) => option.value) as [string, ...string[]];

export const MESSAGE_MAX_LENGTH = 2000;

const tripInquirySchema = z.object({
  name: z.string().trim().min(1).max(120),
  email: z
    .string()
    .trim()
    .toLowerCase()
    .pipe(z.email())
    .pipe(z.string().max(200)),
  travelMonth: z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/),
  nights: z.coerce.number().int().min(1).max(60),
  travellers: z.coerce.number().int().min(1).max(20),
  interests: z
    .array(z.enum(values(INTERESTS)))
    .max(INTERESTS.length)
    .default([]),
  comfort: z.enum(values(COMFORT_LEVELS)),
  budget: z.enum(values(BUDGET_BANDS)),
  message: z.string().trim().max(MESSAGE_MAX_LENGTH).default(""),
  sourcePath: z
    .string()
    .regex(/^\/[A-Za-z0-9/_-]{0,200}$/)
    .optional(),
  // Honeypot: real visitors never see this field, so it must stay empty.
  website: z.literal(""),
});

export type TripInquiry = z.infer<typeof tripInquirySchema>;

export type ParsedTripInquiry =
  { ok: true; data: TripInquiry } | { ok: false; issues: string[] };

export function parseTripInquiry(input: unknown): ParsedTripInquiry {
  const result = tripInquirySchema.safeParse(input);
  if (result.success) return { ok: true, data: result.data };
  return {
    ok: false,
    issues: result.error.issues.map((issue) => issue.path.join(".") || "body"),
  };
}

export function travelMonthOptions(from = new Date(), count = 18) {
  const options: Option[] = [];
  const cursor = new Date(
    Date.UTC(from.getUTCFullYear(), from.getUTCMonth(), 1),
  );
  for (let index = 0; index < count; index += 1) {
    const value = `${cursor.getUTCFullYear()}-${String(cursor.getUTCMonth() + 1).padStart(2, "0")}`;
    options.push({
      value,
      label: new Intl.DateTimeFormat("en", {
        month: "long",
        year: "numeric",
        timeZone: "UTC",
      }).format(cursor),
    });
    cursor.setUTCMonth(cursor.getUTCMonth() + 1);
  }
  return options;
}
