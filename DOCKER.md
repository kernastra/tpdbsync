# Docker Setup for TPDB Poster Sync

This guide explains how to run TPDB Poster Sync using Docker and Docker Compose.

## Quick Start with Docker Compose

### 1. Setup Configuration

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

### 2. Update docker-compose.yml

Edit the volume paths in `docker-compose.yml` to match your system:

```yaml
volumes:
  - /home/sean/posters:/app/posters:ro  # Your local poster path
  - ./config.yaml:/app/config.yaml:ro   # Your config file
  - ./logs:/app/logs                    # Log storage
```

### 3. Start the Service

```bash
# Start in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Configuration Options

### Environment Variables

You can override configuration values using environment variables (useful for Docker):

```bash
# In .env file or docker-compose.yml
REMOTE_SERVER=192.168.1.100
REMOTE_SHARE=media
REMOTE_USERNAME=your_username
REMOTE_PASSWORD=your_password
WATCH_FOLDERS=true
SYNC_INTERVAL=300
LOG_LEVEL=INFO
```

### Volume Mounts

Required volumes:
- **Posters**: Mount your local poster directory (read-only)
- **Config**: Mount your configuration file
- **Logs**: Persistent log storage

## Docker Commands

### Build and Run

```bash
# Build the image
docker build -t tpdb-poster-sync .

# Run interactively
docker run -it --rm \
  -v /home/sean/posters:/app/posters:ro \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/logs:/app/logs \
  --network host \
  tpdb-poster-sync

# Run with custom command
docker run -it --rm \
  -v /home/sean/posters:/app/posters:ro \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  --network host \
  tpdb-poster-sync python manage.py scan-local
```

### Management Commands

```bash
# Test configuration
docker-compose exec tpdb-poster-sync python manage.py validate-config

# Test connection
docker-compose exec tpdb-poster-sync python manage.py test-connection

# Scan local posters
docker-compose exec tpdb-poster-sync python manage.py scan-local

# Dry run
docker-compose exec tpdb-poster-sync python main.py --dry-run
```

## Docker Compose Examples

### Basic Setup

```yaml
version: '3.8'
services:
  tpdb-poster-sync:
    build: .
    volumes:
      - /home/sean/posters:/app/posters:ro
      - ./config.yaml:/app/config.yaml:ro
      - ./logs:/app/logs
    network_mode: host
    restart: unless-stopped
```

### With Environment Overrides

```yaml
version: '3.8'
services:
  tpdb-poster-sync:
    build: .
    environment:
      - REMOTE_SERVER=192.168.1.100
      - REMOTE_USERNAME=posteruser
      - REMOTE_PASSWORD=secretpassword
      - LOG_LEVEL=DEBUG
    volumes:
      - /home/sean/posters:/app/posters:ro
      - ./logs:/app/logs
    network_mode: host
    restart: unless-stopped
```

### One-time Sync

```yaml
version: '3.8'
services:
  tpdb-poster-sync:
    build: .
    command: python main.py --once
    volumes:
      - /home/sean/posters:/app/posters:ro
      - ./config.yaml:/app/config.yaml:ro
    network_mode: host
    restart: "no"
```

## Networking

### Host Network (Recommended)

Uses `network_mode: host` for direct access to SMB shares:

```yaml
network_mode: host
```

### Bridge Network (Alternative)

Create custom network if you prefer isolation:

```yaml
networks:
  poster-sync:
    driver: bridge

services:
  tpdb-poster-sync:
    networks:
      - poster-sync
    ports:
      - "445:445"  # If needed for SMB
```

## Security Considerations

### Credentials

- Use `.env` file for sensitive data
- Never commit passwords to version control
- Consider using Docker secrets for production

### File Permissions

- Container runs as non-root user (posteruser)
- Mount poster directories as read-only
- Ensure proper file ownership

### Network Access

- Container needs access to your SMB server
- Use host networking or proper port mapping
- Consider firewall rules

## Troubleshooting

### Common Issues

1. **SMB Connection Failed**
   ```bash
   # Check network connectivity from container
   docker-compose exec tpdb-poster-sync ping 192.168.1.100
   ```

2. **Permission Denied**
   ```bash
   # Check file permissions
   docker-compose exec tpdb-poster-sync ls -la /app/posters
   ```

3. **Config Not Found**
   ```bash
   # Verify mount
   docker-compose exec tpdb-poster-sync cat /app/config.yaml
   ```

### Debug Mode

```bash
# Run with debug logging
docker-compose run --rm tpdb-poster-sync python main.py --verbose

# Interactive shell
docker-compose run --rm tpdb-poster-sync bash
```

## Monitoring

### Health Checks

Docker Compose includes health checks:

```bash
# Check service health
docker-compose ps
```

### Logs

```bash
# View logs
docker-compose logs -f

# Specific timeframe
docker-compose logs --since="1h" tpdb-poster-sync
```

### Resource Usage

```bash
# Monitor resource usage
docker stats tpdb-poster-sync
```
