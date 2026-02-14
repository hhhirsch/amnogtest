import { THERAPY_AREAS } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import type { ShortlistRequestInput } from "@/lib/validators";

type Props = {
  values: Partial<ShortlistRequestInput>;
  onChange: (patch: Partial<ShortlistRequestInput>) => void;
};

export function StepTherapyArea({ values, onChange }: Props) {
  return (
    <div className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium">Therapiegebiet</label>
        <Select
          value={values.therapy_area ?? ""}
          onChange={(e) => onChange({ therapy_area: e.target.value as ShortlistRequestInput["therapy_area"] })}
        >
          <option value="" disabled>
            Bitte wählen
          </option>
          {THERAPY_AREAS.map((area) => (
            <option key={area} value={area}>
              {area}
            </option>
          ))}
        </Select>
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium">Projektname (optional)</label>
        <Input value={values.project_name ?? ""} onChange={(e) => onChange({ project_name: e.target.value })} />
      </div>
    </div>
  );
}
