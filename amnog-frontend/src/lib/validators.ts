import { z } from "zod";
import { COMPARATOR_TYPES, LINES, ROLES, SETTINGS, THERAPY_AREAS } from "./types";

export const ShortlistRequestSchema = z.object({
  therapy_area: z.enum(THERAPY_AREAS),
  project_name: z.string().optional(),
  indication_text: z.string().min(50).max(6000),
  population_text: z.string().optional(),
  setting: z.enum(SETTINGS),
  role: z.enum(ROLES),
  line: z.enum(LINES).optional(),
  comparator_type: z.enum(COMPARATOR_TYPES).optional(),
  comparator_text: z.string().optional(),
});

export type ShortlistRequestInput = z.infer<typeof ShortlistRequestSchema>;
