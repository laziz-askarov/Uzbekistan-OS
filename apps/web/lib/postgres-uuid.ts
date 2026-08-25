import { z } from "zod";

// PostgreSQL accepts UUID-shaped identifiers without requiring RFC version or
// variant bits. The source registry intentionally uses deterministic IDs in
// that domain, so z.string().uuid() is too strict at this API boundary.
export const postgresUuidSchema = z.guid();
