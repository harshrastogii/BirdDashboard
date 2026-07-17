import { redirect } from "next/navigation";

// Multi-species analysis now lives inside the Recording workspace (Events &
// Labelling tab). This standalone route redirects there.
export default function Page() {
  redirect("/recordings");
}
