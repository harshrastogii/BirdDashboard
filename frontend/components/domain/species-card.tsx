import { Bird } from "lucide-react";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { Species } from "@/lib/api/types";

export function SpeciesCard({ species }: { species: Species }) {
  return (
    <Card className="p-4 transition-colors hover:border-primary/40">
      <div className="flex items-start gap-3">
        <span className="grid place-items-center size-10 shrink-0 rounded-md bg-primary/10 text-primary">
          <Bird className="size-5" />
        </span>
        <div className="min-w-0">
          <p className="font-medium leading-tight truncate">{species.common_name}</p>
          {species.scientific_name && (
            <p className="text-sm italic text-muted-foreground truncate">
              {species.scientific_name}
            </p>
          )}
          <div className="mt-2 flex flex-wrap gap-1.5">
            {species.class_index !== null && (
              <span className="specimen-label">NT-{String(species.class_index).padStart(2, "0")}</span>
            )}
            {species.conservation_status && (
              <Badge variant="warning">{species.conservation_status}</Badge>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
