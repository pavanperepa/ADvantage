import { CampaignForm } from "@/components/campaign-form";
import { PageSection } from "@/components/page-section";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function Home() {
  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6 sm:py-14">
      <PageSection delay={0} className="mb-8 space-y-2">
        <h1 className="text-lg font-semibold tracking-tight sm:text-xl">
          Turn a rough brief into an ad
        </h1>
        <p className="max-w-xl text-muted-foreground">
          {
            "Describe the business and what you're promoting. Generate a ready-to-review poster, reel, or text creative."
          }
        </p>
      </PageSection>

      <PageSection delay={0.1}>
        <Card>
          <CardHeader>
            <CardTitle>New campaign</CardTitle>
            <CardDescription>
              Choose a poster, reel, or marketing text. Reels need your own
              footage and take a minute or two to render.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CampaignForm />
          </CardContent>
        </Card>
      </PageSection>
    </div>
  );
}
