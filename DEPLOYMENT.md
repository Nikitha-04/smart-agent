# Deploying Smart Agent to Vercel

Use the repository root as the Vercel project root. The deployable serverless app is:

```text
api/index.py
requirements.txt
vercel.json
```

Do not set Vercel's Root Directory to the nested `smart-agent/` folder. That folder contains the Docker/local agent service files, not the Vercel dashboard function.

## Vercel Settings

- Framework Preset: Other
- Root Directory: `.`
- Build Command: leave empty
- Output Directory: leave empty
- Install Command: leave empty, or let Vercel install from `requirements.txt`

After deployment, open:

```text
https://your-vercel-domain.vercel.app/dashboard
```

## Local Verification

```bash
pip install -r requirements.txt
python -m uvicorn api.index:app --port 9000
```

Then visit:

```text
http://localhost:9000/dashboard
```
