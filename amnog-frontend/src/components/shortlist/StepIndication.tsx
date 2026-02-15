import { Textarea } from "@/components/ui/textarea";
import type { ShortlistRequestInput } from "@/lib/validators";

type Props = {
  values: Partial<ShortlistRequestInput>;
  onChange: (patch: Partial<ShortlistRequestInput>) => void;
};

export function StepIndication({ values, onChange }: Props) {
  return (
    <div className="space-y-5">
      <div>
        <label className="mb-2 block text-sm font-semibold text-slate-900">
          Anwendungsgebiet <span className="text-red-500">*</span>
        </label>
        <Textarea 
          value={values.indication_text ?? ""} 
          onChange={(e) => onChange({ indication_text: e.target.value })} 
          placeholder="Beschreiben Sie das Anwendungsgebiet..."
        />
      </div>
      <div>
        <label className="mb-2 block text-sm font-semibold text-slate-900">
          Population <span className="text-sm font-normal text-slate-500">(optional)</span>
        </label>
        <Textarea 
          value={values.population_text ?? ""} 
          onChange={(e) => onChange({ population_text: e.target.value })} 
          placeholder="Beschreiben Sie die Zielpopulation..."
        />
      </div>
      <div>
        <label className="mb-2 block text-sm font-semibold text-slate-900">
          Comparator Text <span className="text-sm font-normal text-slate-500">(optional)</span>
        </label>
        <Textarea 
          value={values.comparator_text ?? ""} 
          onChange={(e) => onChange({ comparator_text: e.target.value })} 
          placeholder="Zusätzliche Informationen zum Vergleicher..."
        />
      </div>
    </div>
  );
}
