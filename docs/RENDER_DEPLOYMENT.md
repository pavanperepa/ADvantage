# Render deployment

The repository ships a Render Blueprint at `render.yaml`. It creates:

- `advantage-web`: the public Next.js owner UI;
- `advantage-api`: a private Docker service running FastAPI, Chromium,
  Remotion, and FFmpeg.

The UI sends browser requests to its own `/api` path. Next.js forwards those
requests to `advantage-api` over Render's private network using the injected
`BACKEND_INTERNAL_HOSTPORT`; no public API URL or CORS exception is required.

## Before the first deploy

1. Rotate any OAuth client secret that has been shared in chat or another
   non-secret channel. Never commit the replacement.
2. Run the local Drive authorization helper and keep the resulting refresh
   token private:

   ```powershell
   uv run python scripts/intake/google_drive_authorize.py
   ```

3. Push this repository to the Git provider account you will connect to
   Render.

## Create the Blueprint

1. In the Render Dashboard, choose **New > Blueprint**.
2. Connect the repository and keep the Blueprint path as `render.yaml`.
3. Enter these secret values when Render prompts for them:
   - `OPENAI_API_KEY`
   - `IDEOGRAM_API_KEY`
   - `GOOGLE_DRIVE_OAUTH_CLIENT_ID`
   - `GOOGLE_DRIVE_OAUTH_CLIENT_SECRET`
   - `GOOGLE_DRIVE_REFRESH_TOKEN`
4. Review the estimated monthly price, then apply the Blueprint.
5. Open `advantage-web` after both services report **Live**.

The Blueprint uses Ohio for both services so private traffic stays in one
region. A service's region cannot be changed in place after creation, so change
both `region` values before the first deploy if another region is preferred.
It deploys the repository's current `campaign-flow` branch; update both
`branch` values after merging the application into another long-lived branch.

## Optional Meta campaign connection

The deployed app can generate creatives without Meta credentials. To enable
the explicit **create paused campaign** action, add `META_ACCESS_TOKEN` and
`META_AD_ACCOUNT_ID` to the private `advantage-api` service in Render. Do not
add them to `advantage-web`, and do not activate campaigns from deployment
automation.

## Current persistence boundary

Campaign run metadata is currently held in process memory, and uploaded or
generated files are written to the service filesystem. A restart or redeploy
therefore removes active runs. This is suitable for the current test/demo but
not for production record retention. Adding a disk alone would preserve files
without rebuilding the in-memory run index, so durable run metadata and object
storage should be implemented together before relying on the service for
long-lived campaign history.

## Local production checks

```powershell
docker build -f Dockerfile.render -t advantage-render:test .
Set-Location frontend
npm run build
```
