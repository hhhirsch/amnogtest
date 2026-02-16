import { COMPARATOR_TYPES, LINES, ROLES, SETTINGS } from "@/lib/types";
import { Select } from "@/components/ui/select";
import type { ShortlistRequestInput } from "@/lib/validators";

type Props = {
  values: Partial<ShortlistRequestInput>;
  onChange: (patch: Partial<ShortlistRequestInput>) => void;
};

export function StepContext({ values, onChange }: Props) {
  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div>
        <label className="text-[11px] font-medium tracking-[0.07em] uppercase text-ink-soft mb-2 flex items-center justify-between">Setting</label>
        <Select value={values.setting ?? ""} onChange={(e) => onChange({ setting: e.target.value as ShortlistRequestInput["setting"] })}>
          <option value="" disabled>Bitte wählen</option>
          {SETTINGS.map((entry) => <option key={entry}>{entry}</option>)}
        </Select>
      </div>
      <div>
        <label className="text-[11px] font-medium tracking-[0.07em] uppercase text-ink-soft mb-2 flex items-center justify-between">Rolle</label>
        <Select value={values.role ?? ""} onChange={(e) => onChange({ role: e.target.value as ShortlistRequestInput["role"] })}>
          <option value="" disabled>Bitte wählen</option>
          {ROLES.map((entry) => <option key={entry}>{entry}</option>)}
        </Select>
      </div>
      <div>
        <label className="text-[11px] font-medium tracking-[0.07em] uppercase text-ink-soft mb-2 flex items-center justify-between">
          Linie
          <span className="text-[10px] normal-case tracking-normal font-normal text-ink-muted bg-bg2 rounded px-1.5 py-0.5">optional</span>
        </label>
        <Select value={values.line ?? ""} onChange={(e) => onChange({ line: (e.target.value || undefined) as ShortlistRequestInput["line"] })}>
          <option value="">Keine Angabe</option>
          {LINES.map((entry) => <option key={entry}>{entry}</option>)}
        </Select>
      </div>
      <div>
        <label className="text-[11px] font-medium tracking-[0.07em] uppercase text-ink-soft mb-2 flex items-center justify-between">
          Comparator Type
          <span className="text-[10px] normal-case tracking-normal font-normal text-ink-muted bg-bg2 rounded px-1.5 py-0.5">optional</span>
        </label>
        <Select
          value={values.comparator_type ?? ""}
          onChange={(e) => onChange({ comparator_type: (e.target.value || undefined) as ShortlistRequestInput["comparator_type"] })}
        >
          <option value="">Keine Angabe</option>
          {COMPARATOR_TYPES.map((entry) => <option key={entry}>{entry}</option>)}
        </Select>
      </div>
    </div>
  );
}
