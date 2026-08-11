import { z } from "zod";

const eskizResponseSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  data: z
    .object({
      sms_id: z.union([z.string(), z.number()]).optional(),
      request_id: z.string().optional(),
      status: z.string().optional(),
      parts_count: z.number().int().positive().optional(),
      total_cost: z.string().optional(),
    })
    .optional(),
});

export type EskizSmsResult = z.infer<typeof eskizResponseSchema>;

function requiredEnvironmentVariable(name: string) {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

export function normalizePhoneForEskiz(phone: string) {
  const compact = phone.trim().replace(/[\s().-]/g, "");
  if (!/^\+[1-9]\d{7,14}$/.test(compact)) {
    throw new Error("A valid E.164 international phone number is required");
  }
  return compact.slice(1);
}

export async function sendEskizOtp(
  phone: string,
  otp: string,
  options: { signal?: AbortSignal } = {},
): Promise<EskizSmsResult> {
  if (!/^\d{4,8}$/.test(otp)) throw new Error("Invalid OTP format");

  const apiUrl =
    process.env.ESKIZ_SMS_API_URL?.trim() ||
    "https://devsms.uz/api/send_sms.php";
  const response = await fetch(apiUrl, {
    method: "POST",
    headers: {
      authorization: `Bearer ${requiredEnvironmentVariable("ESKIZ_SMS_API_TOKEN")}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      phone: normalizePhoneForEskiz(phone),
      type: "universal_otp",
      template_type: 1,
      service_name: process.env.ESKIZ_SMS_SERVICE_NAME?.trim() || "UzOS",
      otp_code: otp,
    }),
    cache: "no-store",
    signal: options.signal,
  });

  const body: unknown = await response.json().catch(() => null);
  const parsed = eskizResponseSchema.safeParse(body);
  if (!response.ok || !parsed.success || !parsed.data.success) {
    throw new Error("Eskiz rejected the OTP delivery request");
  }
  return parsed.data;
}
