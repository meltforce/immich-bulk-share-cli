# immich-bulk-share-cli
Python script for managing album sharing permissions via Immich API. Supports listing current album permissions and bulk updates through CSV files.
## Requirements

- Python 3.6+
- `requests` library

## Installation

```bash
pip install requests
```

## Usage

The script has two main commands:

### List Albums and Permissions

Exports all albums and their sharing permissions to CSV:

```bash
python album_processor.py list-all --url https://api.example.com --api-key YOUR_API_KEY [--output albums.csv]
```

If no output file is specified, creates `albums_YYYYMMDD_HHMMSS.csv`

### Update Sharing Permissions

Updates album sharing permissions from CSV:

```bash
python album_processor.py share-albums --url https://api.example.com --api-key YOUR_API_KEY --input albums.csv
```

## CSV Format

### Structure
Required columns:
- AlbumName
- AlbumId
- Role
- User columns (User 1, User 2, etc.)

Example:
```csv
AlbumName;AlbumId;Role;User 1;User 2
Vacation 2023;abc123;viewer;user1@example.com;user2@example.com
Holiday Photos;def456;editor;user3@example.com;
```

### Processing Rules
- Users will be added to albums with specified roles
- Existing users' roles will be updated if different
- Users not in CSV will be removed from album
- Empty cells are ignored

## Error Handling

The script handles:
- Network connectivity issues
- Server timeouts
- Invalid CSV formats
- Missing users
- Invalid URLs (auto-upgrades to HTTPS)

Operation results include:
- Number of processed albums
- Successful/failed updates
- Removed users
- List of users not found

## Exit Codes
- 0: Success
- 1: Error (file not found, network error, etc.)

