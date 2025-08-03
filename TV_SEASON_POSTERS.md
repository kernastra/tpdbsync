# TV Season Poster Support - New Feature Guide

## Overview

TPDB Poster Sync now supports automatic synchronization of both TV series posters and individual season posters. This enhancement allows you to organize and sync posters for each season of your TV shows separately.

## How It Works

### Series vs Season Posters

**Series Posters** (Main show poster):
- Represents the entire TV series
- Uses standard naming: `poster.jpg`, `folder.png`, `cover.jpg`
- Synced to: `remote/tv/Show Name/poster.jpg`

**Season Posters** (Individual season posters):
- Represents specific seasons of a TV show
- Uses season-specific naming patterns
- Synced to: `remote/tv/Show Name/Season XX/poster.jpg`

### Supported Season Naming Patterns

The application recognizes these season poster filename patterns:

- `season01-poster.jpg` (Season 1)
- `season02-poster.png` (Season 2)  
- `s01-poster.jpg` (Season 1, short format)
- `s12-poster.png` (Season 12, short format)
- `season01-folder.jpg` (Alternative naming)
- `s01-folder.png` (Alternative naming)
- `season01-cover.jpg` (Cover style naming)
- `s01-cover.png` (Cover style naming)

### Season Number Detection

The application automatically extracts season numbers from filenames:
- `season01-poster.jpg` → Season 01
- `s3-poster.png` → Season 03 (zero-padded)
- `season12-folder.jpg` → Season 12

## Directory Structure Examples

### Local Directory Structure
```
/home/sean/posters/media/
├── Breaking Bad/
│   ├── poster.jpg              # Series poster
│   ├── season01-poster.jpg     # Season 1 poster
│   ├── season02-poster.jpg     # Season 2 poster
│   ├── season03-poster.jpg     # Season 3 poster
│   ├── season04-poster.jpg     # Season 4 poster
│   └── season05-poster.jpg     # Season 5 poster
├── Game of Thrones/
│   ├── poster.png              # Series poster
│   ├── s01-poster.jpg          # Season 1 (alternative naming)
│   ├── s02-poster.jpg          # Season 2
│   ├── s03-poster.jpg          # Season 3
│   └── s08-poster.jpg          # Season 8
└── The Office/
    ├── folder.jpg              # Series poster (alternative naming)
    ├── season01-folder.png     # Season 1 (folder naming style)
    └── season02-cover.jpg      # Season 2 (cover naming style)
```

### Remote Directory Structure (Auto-created)
```
/share/media/jellyfin/metadata/library/tv/
├── Breaking Bad/
│   ├── poster.jpg              # Series poster
│   ├── Season 01/
│   │   └── poster.jpg          # Season 1 poster
│   ├── Season 02/
│   │   └── poster.jpg          # Season 2 poster
│   ├── Season 03/
│   │   └── poster.jpg          # Season 3 poster
│   ├── Season 04/
│   │   └── poster.jpg          # Season 4 poster
│   └── Season 05/
│       └── poster.jpg          # Season 5 poster
├── Game of Thrones/
│   ├── poster.png              # Series poster
│   ├── Season 01/
│   │   └── poster.jpg          # Season 1 poster
│   ├── Season 02/
│   │   └── poster.jpg          # Season 2 poster
│   ├── Season 03/
│   │   └── poster.jpg          # Season 3 poster
│   └── Season 08/
│       └── poster.jpg          # Season 8 poster
└── The Office/
    ├── poster.jpg              # Series poster (renamed from folder.jpg)
    ├── Season 01/
    │   └── poster.png          # Season 1 poster
    └── Season 02/
        └── poster.jpg          # Season 2 poster
```

## Configuration

### Enable/Disable Season Poster Sync

In your `config.yaml`:

```yaml
sync:
  # Enable TV season poster syncing (default: true)
  tv_season_posters: true
  
  # Customize season poster filename patterns (optional)
  season_poster_patterns:
    - "season\\d{2}-?poster"      # season01-poster, season01poster
    - "s\\d{2}-?poster"           # s01-poster, s01poster  
    - "season\\d{1,2}-?poster"    # season1-poster, season12-poster
    - "s\\d{1,2}-?poster"         # s1-poster, s12-poster
    - "season\\d{2}-?folder"      # season01-folder
    - "s\\d{2}-?folder"           # s01-folder
    - "season\\d{2}-?cover"       # season01-cover
    - "s\\d{2}-?cover"            # s01-cover
```

### Disable Season Syncing

To sync only series posters (not individual seasons):

```yaml
sync:
  tv_season_posters: false
```

## Testing the Feature

### Dry Run Test

Test the new functionality without making changes:

```bash
python main.py --once --dry-run --verbose
```

Look for log entries like:
```
INFO: Found series poster: Breaking Bad/poster.jpg
INFO: Found season poster: Breaking Bad/season01-poster.jpg → Season 01
INFO: Found season poster: Breaking Bad/season02-poster.jpg → Season 02
DRY RUN: Would upload Breaking Bad poster: poster.jpg
DRY RUN: Would upload Breaking Bad (Season 01) poster: season01-poster.jpg
DRY RUN: Would upload Breaking Bad (Season 02) poster: season02-poster.jpg
```

### Scan Local Posters

See what the scanner detects:

```bash
python manage.py scan-local
```

Expected output:
```
📁 TV: /home/sean/posters/media
   📄 Breaking Bad: 6 poster(s)
      → poster.jpg (series)
      → season01-poster.jpg (Season 01)
      → season02-poster.jpg (Season 02)
      → season03-poster.jpg (Season 03)
      → season04-poster.jpg (Season 04)
      → season05-poster.jpg (Season 05)
```

## Best Practices

1. **Consistent Naming**: Use consistent season naming patterns within each show
2. **Zero Padding**: Use two-digit season numbers (01, 02, etc.) for better sorting
3. **File Quality**: Season posters should follow the same quality guidelines as series posters
4. **Backup First**: Always test with `--dry-run` before the first real sync

## Troubleshooting

### Season Posters Not Detected

1. Check filename patterns match the supported formats
2. Verify files are in the correct TV show folder
3. Ensure `tv_season_posters: true` in config
4. Run with `--verbose` to see detection details

### Season Folders Not Created

1. Check remote permissions allow folder creation
2. Verify SMB connection has write access
3. Review log files for permission errors

### Wrong Season Numbers

1. Verify filename format matches patterns
2. Check for typos in season numbers
3. Ensure season numbers are numeric

## Example Log Output

```
INFO: Syncing tv posters from /home/sean/posters/media
INFO: Processing Breaking Bad with season poster support
INFO: Found series poster: poster.jpg
INFO: Found season posters: season01-poster.jpg (Season 01), season02-poster.jpg (Season 02)
INFO: Uploaded Breaking Bad poster: poster.jpg
INFO: Uploaded Breaking Bad (Season 01) poster: season01-poster.jpg
INFO: Uploaded Breaking Bad (Season 02) poster: season02-poster.jpg
INFO: Sync completed - Processed: 1, Uploaded: 3, Skipped: 0, Errors: 0
```

## Integration with Jellyfin

Once synced, Jellyfin will automatically detect and use the season posters:

1. Series poster appears on the main TV show page
2. Season posters appear on individual season pages
3. Both work with the Local Posters plugin
4. Automatic fallback to series poster if season poster missing

This enhancement makes your TV show library much more visually appealing with dedicated artwork for each season!
