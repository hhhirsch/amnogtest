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
        <label className="text-[11px] font-medium tracking-[0.07em] uppercase text-ink-soft mb-2 flex items-center justify-between">Therapiegebiet</label>
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
        <label className="text-[11px] font-medium tracking-[0.07em] uppercase text-ink-soft mb-2 flex items-center justify-between">
          Projektname
          <span className="text-[10px] normal-case tracking-normal font-normal text-ink-muted bg-bg2 rounded px-1.5 py-0.5">optional</span>
        </label>
        <Input value={values.project_name ?? ""} onChange={(e) => onChange({ project_name: e.target.value })} />
      </div>
    </div>
  );
}
