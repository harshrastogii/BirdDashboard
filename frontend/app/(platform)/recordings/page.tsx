"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AudioLines, ChevronRight, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState, ErrorState } from "@/components/data/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useRecordings, useUploadRecording } from "@/lib/api/hooks";
import { formatDuration, prettyRecordingName } from "@/lib/utils";

export default function RecordingsPage() {
  const { data, isLoading, isError, refetch } = useRecordings(200);
  const upload = useUploadRecording();
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  const onPick = (file?: File) => {
    if (!file) return;
    setError(null);
    upload.mutate(file, {
      onSuccess: (rec) => router.push(`/recordings/${rec.id}`),
      onError: (e) => setError(e instanceof Error ? e.message : "Upload failed"),
    });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recording Explorer"
        description="Browse the acoustic library. Open a recording to listen, view its spectrogram, and analyse detected species."
        actions={
          <>
            <input ref={inputRef} type="file" accept=".mp3,.wav,.flac,.ogg" hidden
              onChange={(e) => onPick(e.target.files?.[0])} />
            <Button onClick={() => inputRef.current?.click()} disabled={upload.isPending}>
              <Upload /> {upload.isPending ? "Analysing…" : "Upload recording"}
            </Button>
          </>
        }
      />

      {error && <p className="text-sm text-destructive">{error}</p>}
      {upload.isPending && (
        <Card className="p-4 text-sm text-muted-foreground">Uploading and analysing with BirdNET — this can take a few seconds…</Card>
      )}

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
        </div>
      )}

      {isError && <ErrorState onRetry={() => refetch()} />}

      {data && data.items.length === 0 && (
        <EmptyState icon={AudioLines} title="No recordings yet"
          description="Upload an audio file to analyse it with BirdNET and the NT model." />
      )}

      {data && data.items.length > 0 && (
        <Card className="divide-y divide-border">
          {data.items.map((r) => (
            <Link key={r.id} href={`/recordings/${r.id}`}
              className="flex items-center gap-4 p-4 transition-colors hover:bg-secondary/60">
              <span className="grid size-10 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
                <AudioLines className="size-5" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{prettyRecordingName(r.filename)}</p>
                <p className="specimen-label truncate">{r.filename}</p>
              </div>
              <div className="hidden sm:block text-right">
                <p className="text-sm tabular-nums">{formatDuration(r.duration_seconds)}</p>
                <p className="specimen-label">{r.size_bytes ? `${Math.round(r.size_bytes / 1024)} KB` : "—"}</p>
              </div>
              <ChevronRight className="size-4 text-muted-foreground" />
            </Link>
          ))}
        </Card>
      )}
    </div>
  );
}
