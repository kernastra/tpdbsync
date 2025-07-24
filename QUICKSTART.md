# TPDB Poster Sync - Quick Start Guide

## What This Does

TPDB Poster Sync automatically syncs movie, TV show, and collection poster images from your laptop to a remote server share. It monitors your local poster folders and uploads new or changed posters to the corresponding locations on your server.

## Quick Setup

### 1. Install and Setup
```bash
# Run the automated setup
./install.sh

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure
Edit `config.yaml` with your settings:

```yaml
# Local poster directories
local:
  base_path: "/home/sean/posters"
  folders:
    movies: "media"        # Movies and TV in same folder
    tv: "media"            # Movies and TV in same folder
    collections: "collections"  # Separate collections folder

# Remote server (your Jellyfin server)
remote:
  server: "192.168.1.100"        # Your server IP
  share: "media"                 # SMB share name
  username: "your_username"      # SMB username
  password: "your_password"      # SMB password
  paths:
    movies: "jellyfin/metadata/library/movies"
    tv: "jellyfin/metadata/library/tv"
    collections: "jellyfin/metadata/library/collections"
```

### 3. Test
```bash
# Validate configuration
python manage.py validate-config

# Test connection to server
python manage.py test-connection

# See what would be synced
python main.py --dry-run
```

### 4. Run
```bash
# Start continuous monitoring
python main.py

# Or run once and exit
python main.py --once
```

## Folder Structure

Organize your posters like this:
```
/home/sean/posters/
├── media/                    # Movies and TV shows together
│   ├── The Matrix (1999)/
│   │   └── poster.jpg
│   ├── Inception (2010)/
│   │   └── poster.png
│   ├── Breaking Bad/
│   │   └── poster.jpg
│   └── Game of Thrones/
│       └── poster.png
└── collections/              # Collections separate
    ├── Marvel Cinematic Universe/
    │   └── poster.jpg
    └── Star Wars/
        └── poster.png
```

## Key Features

- **Real-time monitoring**: Automatically detects when you add/change posters
- **Smart file detection**: Looks for poster.jpg, folder.png, cover.jpg, etc.
- **Safe uploads**: Won't overwrite existing files by default
- **Size validation**: Skips files that are too large or too small
- **Dry run mode**: Test what would happen without making changes
- **Comprehensive logging**: Track all sync operations

## Command Line Options

```bash
# Basic usage
python main.py                    # Start monitoring
python main.py --once            # Sync once and exit
python main.py --dry-run         # Preview changes only
python main.py --verbose         # Enable debug logging

# Management utilities
python manage.py validate-config  # Check configuration
python manage.py test-connection  # Test server connection
python manage.py scan-local      # Show local posters
python manage.py dry-run         # Safe test run
```

## Running as a Service

To run automatically in the background:

```bash
# Copy service file
sudo cp tpdb-poster-sync.service /etc/systemd/system/

# Enable and start
sudo systemctl enable tpdb-poster-sync
sudo systemctl start tpdb-poster-sync

# Check status
sudo systemctl status tpdb-poster-sync
```

## Troubleshooting

- **Connection issues**: Check network, credentials, firewall
- **No posters found**: Verify folder structure and file names
- **Permission denied**: Check SMB user permissions
- **See TROUBLESHOOTING.md for detailed help**

## Need Help?

1. Run `python manage.py validate-config` to check setup
2. Check the log file: `tail -f poster_sync.log`
3. Use `--dry-run` to test safely
4. Review TROUBLESHOOTING.md for common issues
