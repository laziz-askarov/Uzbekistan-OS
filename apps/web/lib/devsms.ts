import { z } from "zod";

const devSmsResponseSchema = z.object({
  success: z.boolean(),
  message: z.string().optional(),
  data: z
    .object({
      sms_id: z.union([z.string(), z.number()]).optional(),
      request_id: z.string().optional(),
      status: z.string().optional(),
      parts_count: z.number().int().positive().optional(),
      total_cost: z.union([z.string(), z.number()]).optional(),
    })
    .optional(),
});

export type DevSmsResult = z.infer<typeof devSmsResponseSchema>;

function requiredEnvironmentVariable(name: string) {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

export function normalizePhoneForDevSms(phone: string) {
  const compact = phone.trim().replace(/[\s().-]/g, "");
  const digits = compact.startsWith("+") ? compact.slice(1) : compact;
  if (!/^[1-9]\d{7,14}$/.test(digits)) {
    throw new Error("A valid international phone number is required");
  }
  return digits;
}

export async function sendDevSmsOtp(
  phone: string,
  otp: string,
  options: { signal?: AbortSignal } = {},
): Promise<DevSmsResult> {
  if (!/^\d{4,8}$/.test(otp)) throw new Error("Invalid OTP format");

  const apiUrl =
    process.env.DEVSMS_API_URL?.trim() || "https://devsms.uz/api/send_sms.php";
  const response = await fetch(apiUrl, {
    method: "POST",
    headers: {
      authorization: `Bearer ${requiredEnvironmentVariable("DEVSMS_API_TOKEN")}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({
      phone: normalizePhoneForDevSms(phone),
      type: "universal_otp",
      template_type: 3,
      service_name: process.env.DEVSMS_SERVICE_NAME?.trim() || "UzOS",
      otp_code: otp,
    }),
    cache: "no-store",
    signal: options.signal,
  });

  const body: unknown = await response.json().catch(() => null);
  const parsed = devSmsResponseSchema.safeParse(body);
  if (!response.ok || !parsed.success || !parsed.data.success) {
    throw new Error(`DevSMS rejected the OTP request (${response.status})`);
  }
  return parsed.data;
}
