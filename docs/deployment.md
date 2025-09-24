# MCP Learning Server Deployment Guide

This guide covers various deployment scenarios for the MCP Learning Server, from local development to production environments.

## Table of Contents

- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Remote Server Setup](#remote-server-setup)
- [Claude Desktop Integration](#claude-desktop-integration)
- [Monitoring and Logging](#monitoring-and-logging)
- [Security Considerations](#security-considerations)
- [Troubleshooting](#troubleshooting)

## Local Development

### Prerequisites

- Python 3.10 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd mcp_learn_py
   ```

2. **Install dependencies**
   ```bash
   # Using uv (recommended)
   uv sync --dev

   # Or using pip
   pip install -r requirements-dev.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your preferred settings
   ```

4. **Run the server**
   ```bash
   # STDIO transport (for local MCP clients)
   uv run python scripts/start_server.py

   # HTTP transport (for remote access)
   uv run python scripts/start_server.py --transport http --port 8000
   ```

### Development Workflow

1. **Code formatting**
   ```bash
   uv run black src/ tests/
   uv run isort src/ tests/
   ```

2. **Linting**
   ```bash
   uv run flake8 src/ tests/
   uv run mypy src/
   ```

3. **Testing**
   ```bash
   # Run unit tests
   uv run pytest

   # Run with coverage
   uv run pytest --cov=src --cov-report=html

   # Test the server
   uv run python scripts/test_client.py --interactive
   ```

## Production Deployment

### System Requirements

- **CPU**: 1+ cores
- **RAM**: 512MB+ (1GB+ recommended)
- **Storage**: 1GB+ free space
- **Network**: Outbound internet access (for web scraping)
- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)

### Production Installation

1. **System setup**
   ```bash
   # Update system
   sudo apt update && sudo apt upgrade -y

   # Install Python 3.10+
   sudo apt install python3.10 python3.10-venv python3-pip -y

   # Install uv
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source $HOME/.cargo/env
   ```

2. **Create application user**
   ```bash
   sudo useradd --system --create-home --shell /bin/bash mcp-server
   sudo su - mcp-server
   ```

3. **Deploy application**
   ```bash
   # Clone repository
   git clone <your-repo-url> mcp-learning-server
   cd mcp-learning-server

   # Install dependencies
   uv sync --frozen

   # Configure environment
   cp .env.example .env
   nano .env  # Configure production settings
   ```

4. **Configure production environment**
   ```bash
   # .env production settings
   ENVIRONMENT=production
   DEBUG=false
   LOG_LEVEL=INFO
   MCP_SERVER_HOST=0.0.0.0
   MCP_SERVER_PORT=8000
   SECRET_KEY=your-secure-secret-key-here
   ALLOWED_HOSTS=your-domain.com,your-server-ip
   ```

### Systemd Service

1. **Create service file**
   ```bash
   sudo nano /etc/systemd/system/mcp-learning-server.service
   ```

   ```ini
   [Unit]
   Description=MCP Learning Server
   After=network.target

   [Service]
   Type=exec
   User=mcp-server
   Group=mcp-server
   WorkingDirectory=/home/mcp-server/mcp-learning-server
   Environment=PATH=/home/mcp-server/mcp-learning-server/.venv/bin
   ExecStart=/home/mcp-server/.cargo/bin/uv run python scripts/start_server.py --transport http
   Restart=always
   RestartSec=10
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=multi-user.target
   ```

2. **Enable and start service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable mcp-learning-server
   sudo systemctl start mcp-learning-server
   sudo systemctl status mcp-learning-server
   ```

### Reverse Proxy (Nginx)

1. **Install Nginx**
   ```bash
   sudo apt install nginx -y
   ```

2. **Configure Nginx**
   ```bash
   sudo nano /etc/nginx/sites-available/mcp-learning-server
   ```

   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;

           # Timeout settings
           proxy_connect_timeout 60s;
           proxy_send_timeout 60s;
           proxy_read_timeout 60s;
       }

       # Health check endpoint
       location /health {
           proxy_pass http://localhost:8000/health;
           access_log off;
       }
   }
   ```

3. **Enable site**
   ```bash
   sudo ln -s /etc/nginx/sites-available/mcp-learning-server /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

### SSL Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (already configured by certbot)
sudo systemctl status certbot.timer
```

## Docker Deployment

### Docker Compose (Recommended)

1. **Create docker-compose.yml**
   ```yaml
   version: '3.8'

   services:
     mcp-server:
       build: .
       ports:
         - "8000:8000"
       environment:
         - ENVIRONMENT=production
         - DEBUG=false
         - MCP_SERVER_HOST=0.0.0.0
         - MCP_SERVER_PORT=8000
       volumes:
         - ./logs:/app/logs
         - ./data:/app/data
       restart: unless-stopped
       healthcheck:
         test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
         interval: 30s
         timeout: 10s
         retries: 3

     nginx:
       image: nginx:alpine
       ports:
         - "80:80"
         - "443:443"
       volumes:
         - ./nginx.conf:/etc/nginx/nginx.conf
         - ./ssl:/etc/nginx/ssl
       depends_on:
         - mcp-server
       restart: unless-stopped
   ```

2. **Deploy with Docker Compose**
   ```bash
   docker-compose up -d
   docker-compose logs -f mcp-server
   ```

### Standalone Docker

```bash
# Build image
docker build -t mcp-learning-server .

# Run container
docker run -d \\
  --name mcp-server \\
  -p 8000:8000 \\
  -e ENVIRONMENT=production \\
  -e DEBUG=false \\
  --restart unless-stopped \\
  mcp-learning-server
```

## Remote Server Setup

### Cloud Provider Examples

#### AWS EC2

1. **Launch EC2 instance**
   - Instance type: t3.micro (1 vCPU, 1GB RAM) or larger
   - OS: Ubuntu 22.04 LTS
   - Security group: Allow inbound TCP 80, 443, 22

2. **Connect and deploy**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   # Follow production installation steps
   ```

#### Google Cloud Platform

```bash
# Create VM instance
gcloud compute instances create mcp-server \\
  --image-family=ubuntu-2204-lts \\
  --image-project=ubuntu-os-cloud \\
  --machine-type=e2-micro \\
  --boot-disk-size=20GB \\
  --tags=http-server,https-server

# SSH and deploy
gcloud compute ssh mcp-server
```

#### DigitalOcean

```bash
# Create droplet using doctl
doctl compute droplet create mcp-server \\
  --image ubuntu-22-04-x64 \\
  --size s-1vcpu-1gb \\
  --region nyc1 \\
  --ssh-keys your-ssh-key-id

# SSH and deploy
ssh root@your-droplet-ip
```

### Firewall Configuration

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

## Claude Desktop Integration

### Local Integration

1. **Create MCP configuration**
   ```bash
   # macOS
   mkdir -p ~/Library/Application\\ Support/Claude/
   nano ~/Library/Application\\ Support/Claude/claude_desktop_config.json

   # Windows
   mkdir %APPDATA%\\Claude
   notepad %APPDATA%\\Claude\\claude_desktop_config.json
   ```

2. **Configuration for STDIO transport**
   ```json
   {
     "mcpServers": {
       "mcp-learning-server": {
         "command": "uv",
         "args": ["run", "python", "/path/to/mcp_learn_py/scripts/start_server.py"],
         "env": {
           "UV_PROJECT_ENVIRONMENT": "/path/to/mcp_learn_py/.venv"
         }
       }
     }
   }
   ```

### Remote Integration

1. **Configuration for HTTP transport**
   ```json
   {
     "mcpServers": {
       "mcp-learning-server-remote": {
         "transport": {
           "type": "http",
           "url": "https://your-domain.com/mcp"
         }
       }
     }
   }
   ```

## Monitoring and Logging

### Log Management

1. **Configure structured logging**
   ```bash
   # .env
   LOG_LEVEL=INFO
   ENABLE_METRICS=true
   ```

2. **Log rotation with logrotate**
   ```bash
   sudo nano /etc/logrotate.d/mcp-learning-server
   ```

   ```
   /var/log/mcp-learning-server/*.log {
       daily
       rotate 30
       compress
       delaycompress
       missingok
       notifempty
       sharedscripts
       postrotate
           systemctl reload mcp-learning-server
       endscript
   }
   ```

### Health Monitoring

1. **Health check script**
   ```bash
   #!/bin/bash
   # /usr/local/bin/check-mcp-health.sh

   HEALTH_URL="http://localhost:8000/health"
   RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

   if [ $RESPONSE -eq 200 ]; then
       echo "OK: MCP server is healthy"
       exit 0
   else
       echo "CRITICAL: MCP server health check failed (HTTP $RESPONSE)"
       exit 2
   fi
   ```

2. **Cron monitoring**
   ```bash
   # Add to crontab
   */5 * * * * /usr/local/bin/check-mcp-health.sh
   ```

### Metrics Collection

```bash
# Access metrics endpoint
curl http://localhost:8000/metrics

# Example Prometheus configuration
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'mcp-learning-server'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

## Security Considerations

### Network Security

1. **Firewall rules**
   ```bash
   # Only allow necessary ports
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

2. **Fail2ban for SSH protection**
   ```bash
   sudo apt install fail2ban -y
   sudo systemctl enable fail2ban
   ```

### Application Security

1. **Environment variables**
   ```bash
   # Use strong secrets
   SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

   # Restrict file permissions
   chmod 600 .env
   ```

2. **File system restrictions**
   ```python
   # In production, restrict file operations to specific directories
   ALLOWED_PATHS=["/app/data", "/tmp/mcp-uploads"]
   ```

3. **Rate limiting (nginx)**
   ```nginx
   # Add to nginx configuration
   limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

   location /mcp {
       limit_req zone=api burst=20 nodelay;
       proxy_pass http://localhost:8000;
   }
   ```

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check service logs
   sudo journalctl -u mcp-learning-server -f

   # Check if port is in use
   sudo netstat -tlnp | grep :8000

   # Check file permissions
   sudo -u mcp-server ls -la /home/mcp-server/mcp-learning-server
   ```

2. **Connection refused**
   ```bash
   # Check if service is running
   sudo systemctl status mcp-learning-server

   # Check firewall
   sudo ufw status

   # Test local connection
   curl http://localhost:8000/health
   ```

3. **High memory usage**
   ```bash
   # Monitor memory usage
   htop

   # Check for memory leaks in logs
   sudo journalctl -u mcp-learning-server | grep -i memory

   # Restart service
   sudo systemctl restart mcp-learning-server
   ```

### Log Analysis

```bash
# View recent logs
sudo journalctl -u mcp-learning-server --since "1 hour ago"

# Follow logs in real-time
sudo journalctl -u mcp-learning-server -f

# Filter error logs
sudo journalctl -u mcp-learning-server | grep ERROR

# View startup logs
sudo journalctl -u mcp-learning-server --since today | head -50
```

### Performance Tuning

1. **Optimize Python**
   ```bash
   # Use production WSGI server for HTTP transport
   pip install gunicorn

   # Run with gunicorn
   gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.http_server:app
   ```

2. **System optimization**
   ```bash
   # Increase file descriptor limits
   echo "mcp-server soft nofile 4096" | sudo tee -a /etc/security/limits.conf
   echo "mcp-server hard nofile 8192" | sudo tee -a /etc/security/limits.conf

   # Optimize network settings
   echo "net.core.somaxconn = 1000" | sudo tee -a /etc/sysctl.conf
   sudo sysctl -p
   ```

### Backup and Recovery

```bash
# Backup configuration
tar -czf mcp-backup-$(date +%Y%m%d).tar.gz .env logs/ data/

# Automated backup script
#!/bin/bash
BACKUP_DIR="/backup/mcp-learning-server"
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf "$BACKUP_DIR/mcp-backup-$DATE.tar.gz" \\
    /home/mcp-server/mcp-learning-server/.env \\
    /home/mcp-server/mcp-learning-server/logs/ \\
    /home/mcp-server/mcp-learning-server/data/
```

For additional support or questions, please check the project issues on GitHub or consult the main README.md file.