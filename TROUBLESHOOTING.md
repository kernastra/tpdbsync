# TPDB Poster Sync - Troubleshooting Guide

## Common Issues and Solutions

### 1. Connection Issues

#### "Connection failed" or "SMB connection error"
- **Check network connectivity**: Ensure your laptop can reach the server
  ```bash
  ping <server-ip>
  ```
- **Verify SMB share is accessible**: Test with another SMB client
  ```bash
  smbclient -L //<server-ip> -U <username>
  ```
- **Check credentials**: Ensure username/password are correct in config.yaml
- **Firewall**: Ensure port 445 (SMB) is open on the server

#### "smbprotocol not available"
- Install the SMB library:
  ```bash
  pip install smbprotocol
  ```

### 2. Permission Issues

#### "Access denied" on remote share
- Check that the SMB user has write permissions to the target directories
- Ensure the share allows the user to create directories
- Test manual file copy to verify permissions

### 3. File Issues

#### "File too large" or "File too small" warnings
- Adjust size limits in config.yaml:
  ```yaml
  sync:
    min_file_size: 1024      # 1KB minimum
    max_file_size: 10485760  # 10MB maximum
  ```

#### "No posters found"
- Check folder structure matches expected format
- Verify file extensions are supported (.jpg, .jpeg, .png)
- Ensure poster files are named correctly (poster.jpg, folder.png, etc.)

### 4. Configuration Issues

#### "Missing required configuration keys"
- Ensure all required fields are filled in config.yaml:
  - `local.base_path`
  - `remote.server`
  - `remote.share`
  - `remote.username`
  - `remote.password`

#### "Directory does not exist"
- Create the local poster directories
- Check paths in config.yaml are correct and absolute

### 5. Performance Issues

#### Slow sync or timeouts
- Reduce file size limits
- Increase sync interval
- Check network speed between laptop and server

### 6. Monitoring Issues

#### File changes not detected
- Ensure watchdog is installed: `pip install watchdog`
- Check that local directories exist and are readable
- Try running without monitoring (--once flag)

## Debugging Steps

### 1. Test Configuration
```bash
python manage.py validate-config
```

### 2. Test Connection
```bash
python manage.py test-connection
```

### 3. Scan Local Folders
```bash
python manage.py scan-local
```

### 4. Dry Run
```bash
python main.py --dry-run
```

### 5. Verbose Logging
```bash
python main.py --verbose
```

## Log Files

Check the log file (default: `poster_sync.log`) for detailed error messages:
```bash
tail -f poster_sync.log
```

## Getting Help

1. Check this troubleshooting guide
2. Review the log files for specific error messages
3. Test individual components using the manage.py utility
4. Ensure all dependencies are installed correctly

## Manual Testing

### Test SMB Connection Manually
```bash
# Install smbclient (if not available)
sudo apt-get install smbclient

# List shares
smbclient -L //<server-ip> -U <username>

# Connect to share
smbclient //<server-ip>/<share> -U <username>
```

### Test File Operations
```bash
# Check local folders exist
ls -la /path/to/your/posters

# Check poster files
find /path/to/your/posters -name "*.jpg" -o -name "*.png"
```
