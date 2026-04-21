# Getting Started with Gnosis

Deploy and manage AI agents in 5 minutes.

## One-Minute Local Setup

```bash
# Clone
git clone https://github.com/example/gnosis.git
cd gnosis

# Start everything (Docker Compose)
docker-compose up -d

# Wait for services to initialize (~30 seconds)
sleep 30

# Create first agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer test-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Hello World Agent",
    "description": "Responds with hello",
    "system_prompt": "You are a helpful assistant.",
    "model": "claude-3.5-sonnet"
  }'

# Access dashboard: http://localhost:3000
```

## What You Get

✅ **Backend** (FastAPI): http://localhost:8000/docs  
✅ **Frontend** (Next.js): http://localhost:3000  
✅ **Database** (PostgreSQL): Auto-initialized  
✅ **Cache** (Redis): 128MB in-memory  
✅ **Monitoring** (Prometheus): http://localhost:9090  
✅ **Metrics** (Grafana): http://localhost:3001 (admin/gnosis)  

## Your First Agent

### 1. Sign Up (if not already)
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure-password-123",
    "full_name": "Your Name"
  }'
```

### 2. Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secure-password-123"
  }' | jq '.access_token'
# Copy the token, use in next requests as: -H "Authorization: Bearer TOKEN"
```

### 3. Create Your Agent
```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Email Classifier",
    "description": "Classifies emails by priority",
    "system_prompt": "You are an email classification expert. Classify emails into: URGENT, HIGH, MEDIUM, LOW priority.",
    "model": "claude-3.5-sonnet"
  }' | jq .
```

### 4. Run Your Agent
```bash
export AGENT_ID="..."  # From previous response
curl -X POST "http://localhost:8000/api/v1/agents/$AGENT_ID/execute" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Classify this email: Subject: URGENT - Server down in production"
  }' | jq '.output'
```

### 5. Check Results
```bash
# View all your executions
curl "http://localhost:8000/api/v1/agents/$AGENT_ID/executions" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.items[0]'
```

## Frontend Usage

1. **Open**: http://localhost:3000
2. **Login**: With credentials from step 2 above
3. **Create Agent**: Click "New Agent" button
4. **Configure**: Name, description, system prompt, model selection
5. **Execute**: Chat interface to test your agent
6. **Monitor**: View execution logs, tokens used, costs

## API Documentation

Interactive docs available at: http://localhost:8000/docs

Key endpoints:
- `POST /api/v1/auth/register` — Create account
- `POST /api/v1/auth/login` — Get auth token
- `POST /api/v1/agents` — Create agent
- `POST /api/v1/agents/{id}/execute` — Run agent
- `GET /api/v1/agents` — List your agents
- `POST /api/v1/webhooks` — Register webhook for execution results
- `GET /api/v1/billing/usage` — Check usage & costs

## Common Tasks

### Add Tools to Your Agent
```bash
curl -X PATCH "http://localhost:8000/api/v1/agents/$AGENT_ID" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tools": [
      {
        "name": "web_search",
        "description": "Search the web for recent information"
      }
    ]
  }'
```

### Set Up Webhook Notifications
```bash
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-domain.com/webhooks/gnosis",
    "event_types": ["execution.completed", "execution.failed"],
    "secret": "your-webhook-secret"
  }'
```

### Stream Execution Results (WebSocket)
```bash
# Use WebSocket to receive real-time execution updates
ws://localhost:8000/ws/executions?token=YOUR_TOKEN
```

## Monitoring & Logs

### View Application Logs
```bash
# Backend
docker-compose logs -f backend

# Frontend
docker-compose logs -f frontend

# Database
docker-compose logs -f postgres
```

### Check Health Status
```bash
curl http://localhost:8000/api/v1/health/detailed | jq .
```

### View Metrics
- Prometheus: http://localhost:9090/graph
- Grafana: http://localhost:3001

## Troubleshooting

### "Connection refused" error
```bash
# Services might not be ready yet, wait and retry
docker-compose ps  # Check all services are "Up"
docker-compose logs postgres  # Check database initialized
```

### "Invalid token" error
```bash
# Token might have expired (30 min default), login again
curl -X POST http://localhost:8000/api/v1/auth/login ...
```

### "Agent not found" error
```bash
# Verify agent ID is correct
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/agents | jq '.items[0].id'
```

### Rate limited (429 error)
```bash
# Default: 100 requests/minute per user
# Wait 1 minute and retry, or adjust RATE_LIMIT_PER_MINUTE in .env
```

## Production Deployment

For production use, follow [DEPLOYMENT.md](DEPLOYMENT.md)

Key steps:
1. Configure secrets (env vars or AWS Secrets Manager)
2. Build Docker images and push to ECR
3. Run Terraform to create AWS infrastructure
4. Run database migrations on production database
5. Deploy to ECS with load balancer

## Next Steps

- **Learn**: Read [ARCHITECTURE.md](ARCHITECTURE.md)
- **Configure**: Set up OAuth (Google/GitHub) in [backend/.env](backend/.env.example)
- **Integrate**: Build workflows combining multiple agents
- **Deploy**: Follow [DEPLOYMENT.md](DEPLOYMENT.md) for production

## Support

- **Documentation**: [README.md](README.md)
- **Issues**: https://github.com/example/gnosis/issues
- **API Docs**: http://localhost:8000/docs (live)

Happy agent building! 🚀
