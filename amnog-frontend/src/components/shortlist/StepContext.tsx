import { COMPARATOR_TYPES, LINES, ROLES, SETTINGS } from "@/lib/types";
import { Select } from "@/components/ui/select";
import type { ShortlistRequestInput } from "@/lib/validators";

type Props = {
  values: Partial<ShortlistRequestInput>;
  onChange: (patch: Partial<ShortlistRequestInput>) => void;
};

export function StepContext({ values, onChange }: Props) {
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <div>
        <label className="mb-2 block text-sm font-semibold text-slate-900">
          Setting <span className="text-red-500">*</span>
        </label>
        <Select value={values.setting ?? ""} onChange={(e) => onChange({ setting: e.target.value as ShortlistRequestInput["setting"] })}>
          <option value="" disabled>Bitte wählen</option>
          {SETTINGS.map((entry) => <option key={entry}>{entry}</option>)}
        </Select>
      </div>
      <div>
        <label className="mb-2 block text-sm font-semibold text-slate-900">
          Rolle <span className="text-red-500">*</span>
        </label>
        <Select value={values.role ?? ""} onChange={(e) => onChange({ role: e.target.value as ShortlistRequestInput["role"] })}>
          <option value="" disabled>Bitte wählen</option>
          {ROLES.map((entry) => <option key={entry}>{entry}</option>)}
        </Select>
      </div>
      <div>
        <label className="mb-2 block text-sm font-semibold text-slate-900">
          Linie <span className="text-sm font-normal text-slate-500">(optional)</span>
        </label>
        <Select value={values.line ?? ""} onChange={(e) => onChange({ line: (e.target.value || undefined) as ShortlistRequestInput["line"] })}>
          <option value="">Keine Angabe</option>
          {LINES.map((entry) => <option key={entry}>{entry}</option>)}
        </Select>
      </div>
      <div>
        <label className="mb-2 block text-sm font-semibold text-slate-900">
          Comparator Type <span className="text-sm font-normal text-slate-500">(optional)</span>
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
