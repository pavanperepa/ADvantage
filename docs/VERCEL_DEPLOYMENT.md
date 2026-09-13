# Vercel deployment

The repository deploys as one Vercel project with two Vercel Services:

- `web`: the public Next.js owner UI;
- `api`: a container-image Function running FastAPI, Chromium, Remotion, and
  FFmpeg.

Top-level routing sends `/api/*` to the container and all other traffic to
Next.js. The container scales to zero when it is idle, so there is no
always-on server charge.

Vercel Services and container-image Functions are currently beta features.
The application is commercial, so use a Pro account; Vercel's free Hobby plan
is restricted to personal, non-commercial projects.

## Before the first deploy

1. Rotate any OAuth client secret that has been shared in chat or another
   non-secret channel. Never commit the replacement.
2. Run the local Drive authorization helper and keep the resulting refresh
   token private:

   ```powershell
   uv run python scripts/intake/google_drive_authorize.py
   ```

3. Push this repository to the Git provider account you will connect to
   Vercel.

## Import the project

1. In the Vercel dashboard, choose **Add New > Project** and import this
   repository.
2. Keep the project Root Directory at the repository root. Vercel reads the
   root `vercel.json` and builds both services from there.
3. Select `campaign-flow` as the production branch unless the deployment files
   have since been merged into the repository's default branch.
4. Open **Storage**, create a Vercel Blob store with **Public** access, and
   connect it to this project for Production and Preview. Vercel adds
   `BLOB_READ_WRITE_TOKEN` automatically. Public access lets browsers fetch
   generated videos directly without passing them through the 4.5 MB Function
   response limit.
5. Add these secrets for Production and Preview:
   - `OPENAI_API_KEY`
   - `IDEOGRAM_API_KEY`
   - `GOOGLE_DRIVE_OAUTH_CLIENT_ID`
   - `GOOGLE_DRIVE_OAUTH_CLIENT_SECRET`
   - `GOOGLE_DRIVE_REFRESH_TOKEN`
6. Set `VERCEL_SUPPORT_LARGE_FUNCTIONS=1`. The Chromium/FFmpeg container is
   intentionally larger than a normal web function.
7. Deploy, then verify `/healthz` and create one poster before testing a reel.

Do not add `PORT`: `Dockerfile.vercel` listens on Vercel's default port 80.
The non-secret defaults for `OPENAI_MODEL`, `META_API_VERSION`, and the Chromium
executable are built into the container.

## Media and persistence limits

Vercel Functions accept request and response bodies up to 4.5 MB. Select reel
footage from Google Drive instead of uploading large clips through the browser.
When `BLOB_READ_WRITE_TOKEN` is configured, generated artifacts, run metadata,
and the source files required for regeneration are copied to Blob before the
request completes. Without that token the local in-memory behavior remains,
which is suitable for development but not a Vercel deployment.

The Blob store is public because the password-free UI must deliver videos
directly from object storage. Blob URLs contain hard-to-guess paths, but anyone
who receives a URL can view that file.

Function duration is plan-dependent. The container uses the longest duration
allowed by the selected plan and accepts one render at a time. A typical reel
currently takes 200-240 seconds, so Pro provides materially safer headroom than
the five-minute Hobby ceiling.

## Optional Meta campaign connection

The deployed app can generate creatives without Meta credentials. To enable
the explicit **create paused campaign** action, add `META_ACCESS_TOKEN` and
`META_AD_ACCOUNT_ID` in Vercel. Do not activate campaigns from deployment
automation.

## Local production checks

```powershell
docker build -f Dockerfile.vercel -t advantage-vercel:test .
Set-Location frontend
npm run build
```
