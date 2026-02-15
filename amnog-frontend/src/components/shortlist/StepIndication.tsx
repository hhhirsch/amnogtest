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
        <label className="mb-1 block text-sm font-medium">Anwendungsgebiet</label>
        <Textarea value={values.indication_text ?? ""} onChange={(e) => onChange({ indication_text: e.target.value })} />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium">Population (optional)</label>
        <Textarea value={values.population_text ?? ""} onChange={(e) => onChange({ population_text: e.target.value })} />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium">Comparator Text (optional)</label>
        <Textarea value={values.comparator_text ?? ""} onChange={(e) => onChange({ comparator_text: e.target.value })} />
      </div>
    </div>
  );
}
