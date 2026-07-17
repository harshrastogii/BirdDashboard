"use client";

import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/layout/page-header";
import { AudioPlayer } from "@/components/audio/audio-player";
import { RecordingOverview } from "@/components/domain/recording-overview";
import { ModelComparisonPanel } from "@/components/domain/model-comparison-panel";
import { EventsLabelling } from "@/components/domain/events-labelling";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useRecording } from "@/lib/api/hooks";
import { API_BASE } from "@/lib/config";
import { prettyRecordingName } from "@/lib/utils";

export default function RecordingDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [minConf, setMinConf] = useState(0.25);
  const recording = useRecording(id);
  const audioSrc = `${API_BASE}/api/v1/recordings/${id}/audio`;

  return (
    <div className="space-y-6">
      <Button asChild variant="ghost" size="sm" className="-ml-2">
        <Link href="/recordings"><ArrowLeft /> Recordings</Link>
      </Button>

      <PageHeader
        title={recording.data ? prettyRecordingName(recording.data.filename) : "Recording"}
        description={recording.data?.filename}
      />

      <Card>
        <CardContent className="py-4">
          <AudioPlayer src={audioSrc} />
        </CardContent>
      </Card>

      <Tabs defaultValue="overview">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="compare">Model Comparison</TabsTrigger>
            <TabsTrigger value="events">Events &amp; Labelling</TabsTrigger>
          </TabsList>

          <label className="flex items-center gap-2 text-sm text-muted-foreground">
            Min confidence
            <input type="range" min={0} max={0.9} step={0.05} value={minConf}
              onChange={(e) => setMinConf(Number(e.target.value))} className="accent-[var(--primary)]" />
            <span className="w-9 tabular-nums">{(minConf * 100).toFixed(0)}%</span>
          </label>
        </div>

        <TabsContent value="overview">
          <RecordingOverview recording={recording.data} recordingId={id} minConfidence={minConf} />
        </TabsContent>
        <TabsContent value="compare">
          <ModelComparisonPanel recordingId={id} recording={recording.data} minConfidence={minConf} />
        </TabsContent>
        <TabsContent value="events">
          <EventsLabelling recordingId={id} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
