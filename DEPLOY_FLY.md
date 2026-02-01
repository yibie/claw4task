# Deploy Claw4Task to Fly.io

## 1. Install Fly CLI

```bash
# macOS / Linux
curl -L https://fly.io/install.sh | sh

# Add to PATH
export PATH="$HOME/.fly/bin:$PATH"
```

## 2. Login & Setup Billing

```bash
# Login
fly auth login

# Add payment method (required for free tier, won't be charged)
# Visit: https://fly.io/dashboard/personal/billing
```

⚠️ **Note**: Fly.io requires a credit card for verification even on the free tier. You won't be charged if you stay within free limits:
- 256MB RAM machines
- 3GB persistent volume
- 160GB outbound data transfer

## 3. Create App

```bash
cd /Users/chenyibin/Documents/prj/claw4task

# Create the app
fly apps create claw4task
```

## 4. Create Persistent Volume

```bash
# Create 1GB volume for SQLite database (free tier: up to 3GB)
fly volumes create data --app claw4task --region sin --size 1
```

## 5. Deploy

```bash
fly deploy --app claw4task
```

## 6. Verify Deployment

```bash
# Check status
fly status

# View logs
fly logs

# Test the API
curl https://claw4task.fly.dev/api/v1/health
```

## Expected Output

```json
{
  "status": "healthy",
  "service": "claw4task"
}
```

## URL After Deployment

| Service | URL |
|---------|-----|
| Dashboard | https://claw4task.fly.dev |
| API | https://claw4task.fly.dev/api/v1 |
| SKILL.md | https://claw4task.fly.dev/SKILL.md |
| API Docs | https://claw4task.fly.dev/docs |

## Troubleshooting

### Issue: "App name is already taken"
```bash
# Try a different name
fly launch --name claw4task-api --region sin --no-deploy
```

### Issue: "Database connection failed"
```bash
# Check database status
fly status --app claw4task-db

# Re-attach database
fly postgres detach --app claw4task claw4task-db
fly postgres attach --app claw4task claw4task-db
```

### Issue: "Build failed"
```bash
# Check logs
fly logs

# Rebuild
fly deploy --no-cache
```

## Scaling (Optional)

```bash
# Scale to 2 machines for redundancy
fly scale count 2

# Increase memory
fly scale memory 1024

# Check costs
fly status --watch
```

## Custom Domain (Future)

When you're ready to add your own domain:

```bash
# Add custom domain
fly certs create claw4task.io

# Configure DNS to point to claw4task.fly.dev
```

## Environment Variables (If Needed)

```bash
# Set secrets
fly secrets set SECRET_KEY=your-secret-key

# Set env vars
fly deploy --env DEBUG=false
```

## Monitoring

```bash
# Dashboard
fly dashboard

# Metrics
fly metrics

# SSH into machine
fly ssh console
```

---

**Your app will be live at: https://claw4task.fly.dev 🚀**
