import { Compass } from "lucide-react";

import { PageHeader } from "./page-header";
import { Badge } from "@/components/ui/badge";

/** Placeholder for modules scheduled in later phases. Keeps navigation
 *  complete so future modules drop in without restructuring. */
export function ComingSoon({ title, description }: { title: string; description: string }) {
  return (
    <div className="space-y-6">
      <PageHeader title={title} description={description} actions={<Badge variant="accent">Planned</Badge>} />
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border py-24 text-center">
        <Compass className="size-8 text-muted-foreground" />
        <p className="mt-3 font-medium">This module is on the roadmap</p>
        <p className="mt-1 max-w-md text-sm text-muted-foreground">
          The platform shell, design system, and data contracts are in place — this module will be built
          in an upcoming phase and slot directly into this navigation.
        </p>
      </div>
    </div>
  );
}
