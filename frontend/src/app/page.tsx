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
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Turn a rough brief into an ad
        </h1>
        <p className="max-w-xl text-muted-foreground">
          {
            "Describe the business and what you're promoting. We'll generate a ready-to-review poster or reel, plus a Meta ad preview if you set a budget."
          }
        </p>
      </PageSection>

      <PageSection delay={0.1}>
        <Card>
          <CardHeader>
            <CardTitle>New campaign</CardTitle>
            <CardDescription>
              A poster is ready in seconds. A reel needs your own footage and
              takes a minute or two to render.
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
