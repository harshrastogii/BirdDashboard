import { redirect } from "next/navigation";

// Listen & Label now lives inside the Recording workspace (Events & Labelling
// tab). This standalone route redirects there to avoid duplicate entry points.
export default function Page() {
  redirect("/recordings");
}
