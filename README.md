# TPDB Poster Sync

A comprehensive Python application that automatically syncs movie, TV show, and collection posters from local directories to remote Jellyfin metadata storage on TrueNAS or other SMB/CIFS shares.

## 🔄 Purpose & Integration

This program serves as a **middleman solution** that bridges the gap between poster management tools and Jellyfin's metadata storage. It relies on having the following programs installed and running:

- **[JellyfinUpdatePoster](https://github.com/Iceshadow1404/JellyfinUpdatePoster)** - For downloading and managing poster files
- **[Jellyfin.Plugin.LocalPosters](https://github.com/NooNameR/Jellyfin.Plugin.LocalPosters/)** - For enabling Jellyfin to use local poster files

TPDB Poster Sync acts as the connector that automatically transfers poster files from your local management system to your Jellyfin server's metadata storage, ensuring seamless poster integration.

## 🎯 Features

- **Automatic Poster Sync**: Syncs `.jpg`, `.jpeg`, and `.png` poster files
- **Multiple Libraries**: Supports movies, TV shows, and collections
- **Real-time Monitoring**: Watches for file changes and syncs automatically
- **Mount-based SMB**: Uses system CIFS mounts for reliable file transfers
- **Dry Run Mode**: Preview changes without making modifications
- **Docker Support**: Ready-to-use Docker containers and compose files
- **Comprehensive Logging**: Detailed logs with configurable levels
- **Error Handling**: Robust error handling and recovery

## 📋 Requirements

- Python 3.9+
- Linux system with CIFS utilities
- Access to TrueNAS or SMB/CIFS share
- Sudo access for mounting SMB shares

## 🚀 Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd tpdbsync
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Install System Dependencies

```bash
sudo apt update
sudo apt install cifs-utils smbclient
```

### 3. Configure

```bash
cp config.yaml.example config.yaml
# Edit config.yaml with your settings
```

### 4. Test Connection

```bash
python manage.py test-connection
```

### 5. Run Sync

```bash
# Dry run first
python main.py --once --dry-run

# Actual sync
python main.py --once

# Continuous monitoring
python main.py
```

## ⚙️ Configuration

### Main Configuration (`config.yaml`)

```yaml
# Local poster directories
local:
  base_path: "/path/to/your/posters"
  poster_folder: "Poster"
  collections_folder: "Collections"

# Remote server settings
remote:
  server: "192.168.1.187"
  share: "apollo"
  username: "your_username"
  password: "your_password"
  domain: "WORKGROUP"
  
  # Remote paths (within the share)
  paths:
    movies: "media/jellyfin/metadata/library/movies"
    tv: "media/jellyfin/metadata/library/tv"
    collections: "media/jellyfin/metadata/library/collections"

# Sync settings
sync:
  poster_extensions: [".jpg", ".jpeg", ".png"]
  poster_names: ["poster", "folder", "cover"]
  overwrite_existing: false
  watch_folders: true
  sync_interval: 300

# Logging
logging:
  level: "INFO"
  file: "poster_sync.log"
  max_size: 10485760
  backup_count: 5
```

### Environment Variables (`.env`)

```bash
# Copy from .env.example and modify
cp .env.example .env
```

## 📁 Directory Structure

### Local Directory Structure
```
/path/to/posters/
├── Poster/
│   ├── Movie Name (Year)/
│   │   └── poster.jpg
│   └── TV Show Name (Year)/
│       └── poster.jpg
└── Collections/
    └── Collection Name/
        └── poster.jpg
```

### Remote Directory Structure (Created Automatically)
```
/share/media/jellyfin/metadata/library/
├── movies/
│   └── Movie Name (Year)/
│       └── poster.jpg
├── tv/
│   └── TV Show Name (Year)/
│       └── poster.jpg
└── collections/
    └── Collection Name/
        └── poster.jpg
```

## 🐳 Docker Usage

### Using Docker Compose

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your settings

# Run with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

### Manual Docker Build

```bash
# Build image
docker build -t tpdbsync .

# Run container
docker run -d \
  --name tpdbsync \
  --cap-add SYS_ADMIN \
  --device /dev/fuse \
  --security-opt apparmor:unconfined \
  -v /path/to/local/posters:/app/posters \
  -e REMOTE_SERVER=192.168.1.187 \
  -e REMOTE_SHARE=apollo \
  -e REMOTE_USERNAME=your_username \
  -e REMOTE_PASSWORD=your_password \
  tpdbsync
```

## 🛠️ Management Commands

The `manage.py` script provides several utility functions:

```bash
# Test remote connection
python manage.py test-connection

# Scan and show local posters
python manage.py scan-local

# List remote files
python manage.py list-remote

# Check sync status
python manage.py status
```

## 📊 Command Line Options

### Main Application (`main.py`)

```bash
python main.py [OPTIONS]

Options:
  --config PATH     Path to configuration file (default: config.yaml)
  --dry-run         Show what would be synced without making changes
  --once            Run sync once and exit (don't monitor for changes)
  --verbose, -v     Enable verbose logging
  --help            Show help message
```

### Examples

```bash
# One-time sync with dry run
python main.py --once --dry-run

# Continuous monitoring with verbose logging
python main.py --verbose

# Use custom config file
python main.py --config /path/to/custom/config.yaml
```

## 🔍 Monitoring and Logs

### Log Files

- **poster_sync.log**: Main application log
- **Location**: Configurable in `config.yaml`
- **Rotation**: Automatic log rotation with configurable size and backup count

### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General information about sync operations
- **WARNING**: Warning messages for non-critical issues
- **ERROR**: Error messages for failed operations

### Real-time Monitoring

```bash
# Watch logs in real-time
tail -f poster_sync.log

# Monitor specific log levels
tail -f poster_sync.log | grep ERROR
```

## 🐛 Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   ```bash
   # Check SMB share permissions
   smbclient -L //server-ip -U username
   
   # Test manual mount
   sudo mount -t cifs //server/share /tmp/test -o username=user,password=pass
   ```

2. **Mount Failures**
   ```bash
   # Install required packages
   sudo apt install cifs-utils
   
   # Check SMB connectivity
   ping server-ip
   telnet server-ip 445
   ```

3. **Authentication Issues**
   ```bash
   # Verify credentials
   smbclient //server/share -U username
   
   # Check domain/workgroup settings
   # Try with and without domain prefix
   ```

### Debug Mode

```bash
# Run with maximum verbosity
python main.py --verbose --dry-run

# Check configuration
python -c "from src.config import Config; c=Config('config.yaml'); print(c.config)"
```

## 🔐 Security Considerations

- **Passwords**: Store passwords securely using environment variables
- **File Permissions**: Ensure proper file permissions for config files
- **Network Security**: Use secure networks for SMB connections
- **Docker Security**: Review container capabilities and security options

## 📈 Project Status

**Status**: ✅ **Production Ready**

- ✅ Successfully tested with 75+ poster files
- ✅ Mount-based SMB connectivity working
- ✅ Error handling and recovery implemented
- ✅ Docker containers ready
- ✅ Comprehensive logging and monitoring

## 🚀 Recent Success Story

This application has been successfully tested and deployed with:

- **75 poster files** uploaded successfully (36 movies + 36 TV shows + 3 collections)
- **100% success rate** with zero errors
- **TrueNAS integration** working perfectly
- **Automatic directory creation** for organized metadata structure
- **Real-time monitoring** and logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

### Core Dependencies
This program functions as a middleman between excellent existing tools and relies on their functionality:

**Special Thanks To:**
- **[Iceshadow1404](https://github.com/Iceshadow1404)** for [JellyfinUpdatePoster](https://github.com/Iceshadow1404/JellyfinUpdatePoster) - An amazing tool for downloading and managing poster files from various sources
- **[NooNameR](https://github.com/NooNameR)** for [Jellyfin.Plugin.LocalPosters](https://github.com/NooNameR/Jellyfin.Plugin.LocalPosters/) - The essential Jellyfin plugin that enables local poster file support

### Technical Credits
- Built for Jellyfin media server integration
- Uses smbprotocol for SMB/CIFS connectivity
- Supports TrueNAS and other NAS solutions
- Mount-based approach for reliable file transfers

**Note**: This application requires both of the above tools to be properly installed and configured to function as intended. TPDB Poster Sync serves as the automated bridge that connects your poster management workflow to your Jellyfin server.

---

*For support, please open an issue on GitHub or check the troubleshooting section above.*
