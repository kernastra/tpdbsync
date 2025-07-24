# Example folder structure for local posters

This document shows the expected folder structure for your local poster directories.

## Recommended Structure

```
/home/sean/posters/
├── media/                    # Combined movies and TV shows
│   ├── The Matrix (1999)/
│   │   ├── poster.jpg
│   │   └── fanart.jpg
│   ├── Inception (2010)/
│   │   ├── poster.png
│   │   └── backdrop.jpg
│   ├── Breaking Bad/
│   │   ├── poster.jpg
│   │   └── season01-poster.jpg
│   ├── Game of Thrones/
│   │   ├── poster.png
│   │   └── banner.jpg
│   └── The Office/
│       └── cover.jpg
└── collections/              # Separate collections folder
    ├── Marvel Cinematic Universe/
    │   └── poster.jpg
    ├── Star Wars/
    │   └── poster.png
    └── Lord of the Rings/
        └── folder.jpg
```

## Key Points

1. **Media Folder**: Movies and TV shows are stored together in a single `media` folder
2. **Collections Folder**: Collections have their own separate `collections` folder
3. **Media Item Folders**: Each movie, TV show, or collection gets its own subfolder
4. **Poster Files**: The app looks for files named:
   - `poster.jpg` or `poster.png` (preferred)
   - `folder.jpg` or `folder.png`
   - `cover.jpg` or `cover.png`
5. **File Priority**: If multiple poster files exist, the app will prefer them in this order:
   - poster.* files
   - folder.* files  
   - cover.* files
   - .jpg files over .png files
6. **Mixed Media**: Since movies and TV shows are in the same folder, the sync process will handle both types when syncing to their respective remote locations

## Remote Structure

The app will create a similar structure on your remote server:

```
/jellyfin/metadata/library/
├── movies/
│   ├── The Matrix (1999)/
│   │   └── poster.jpg
│   ├── Inception (2010)/
│   │   └── poster.png
│   └── Avatar (2009)/
│       └── poster.jpg
├── tv/
│   ├── Breaking Bad/
│   │   └── poster.jpg
│   ├── Game of Thrones/
│   │   └── poster.png
│   └── The Office/
│       └── poster.jpg
└── collections/
    ├── Marvel Cinematic Universe/
    │   └── poster.jpg
    ├── Star Wars/
    │   └── poster.png
    └── Lord of the Rings/
        └── poster.jpg
```

## Tips

- Keep folder names consistent with your media server's naming convention
- Use clear, descriptive folder names
- The app will automatically handle file extension conversion
- Large files (>10MB) will be skipped by default
- Very small files (<1KB) will also be skipped
