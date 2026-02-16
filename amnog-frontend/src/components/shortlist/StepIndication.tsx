import { Textarea } from "@/components/ui/textarea";
import type { ShortlistRequestInput } from "@/lib/validators";

type Props = {
  values: Partial<ShortlistRequestInput>;
  onChange: (patch: Partial<ShortlistRequestInput>) => void;
};

export function StepIndication({ values, onChange }: Props) {
  return (
    <div className="space-y-4">
      <div>
        <label className="text-[11px] font-medium tracking-[0.07em] uppercase text-ink-soft mb-2 flex items-center justify-between">Anwendungsgebiet</label>
        <Textarea value={values.indication_text ?? ""} onChange={(e) => onChange({ indication_text: e.target.value })} />
      </div>
      <div>
        <label className="text-[11px] font-medium tracking-[0.07em] uppercase text-ink-soft mb-2 flex items-center justify-between">
          Population
          <span className="text-[10px] normal-case tracking-normal font-normal text-ink-muted bg-bg2 rounded px-1.5 py-0.5">optional</span>
        </label>
        <Textarea value={values.population_text ?? ""} onChange={(e) => onChange({ population_text: e.target.value })} />
      </div>
      <div>
        <label className="text-[11px] font-medium tracking-[0.07em] uppercase text-ink-soft mb-2 flex items-center justify-between">
          Comparator Text
          <span className="text-[10px] normal-case tracking-normal font-normal text-ink-muted bg-bg2 rounded px-1.5 py-0.5">optional</span>
        </label>
        <Textarea value={values.comparator_text ?? ""} onChange={(e) => onChange({ comparator_text: e.target.value })} />
      </div>
    </div>
  );
}
