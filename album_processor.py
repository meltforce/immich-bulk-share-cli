import requests
import json
import csv
import re
from typing import List, Dict, Optional, Set
import argparse
from pathlib import Path
import sys
from datetime import datetime

class AlbumAPIProcessor:
    """Process albums through API with capabilities to list, add, update, and remove users."""
    
    COL_ALBUM_NAME = 'AlbumName'
    COL_ALBUM_ID = 'AlbumId'
    COL_ROLE = 'Role'

    def __init__(self, base_url: str, api_key: str):
        """Initialize the API processor with base URL and authentication."""
        self.base_url = self._validate_and_adjust_url(base_url)
        self.api_key = api_key
        self.headers = {
            'Accept': 'application/json',
            'x-api-key': self.api_key
        }
        self.user_email_to_id = {}  # Cache for email to ID mapping

    def _validate_and_adjust_url(self, url: str) -> str:
        """Validate URL and switch to HTTPS if HTTP is used."""
        if not re.match(r'^https?://', url):
            raise ValueError("Invalid URL provided. Ensure it starts with http:// or https://.")
        
        parsed_url = requests.utils.urlparse(url)
        if parsed_url.scheme == 'http':
            print("Warning: Switching to HTTPS for security.")
            url = parsed_url._replace(scheme='https').geturl()
        
        # Check server reachability
        try:
            response = requests.get(url, timeout=5)
            if response.status_code != 200:
                print(f"Warning: The server responded with status code {response.status_code}.")
        except requests.ConnectionError:
            sys.exit("Error: Cannot reach the server. Check your network connection and URL.")
        except requests.Timeout:
            sys.exit("Error: The server took too long to respond.")
        
        return url.rstrip('/')

    def get_albums(self) -> List[Dict]:
        """Fetch all albums from the API."""
        url = f"{self.base_url}/api/albums"
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching albums: {e}")
            sys.exit(1)

    def get_album_details(self, album_id: str) -> Optional[Dict]:
        """Fetch detailed information about a specific album."""
        url = f"{self.base_url}/api/albums/{album_id}?withoutAssets=true"
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching album details for {album_id}: {e}")
            return None

    def get_users(self) -> Dict[str, str]:
        """Fetch all users and create email to ID mapping."""
        url = f"{self.base_url}/api/users"
        try:
            response = requests.get(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            users = response.json()
            
            # Create email to ID mapping
            email_to_id = {}
            for user in users:
                email = user.get('email')
                user_id = user.get('id')
                if email and user_id:
                    email_to_id[email.lower()] = user_id  # Store emails in lowercase
            
            print(f"Loaded {len(email_to_id)} user email-ID mappings")
            return email_to_id
        except requests.exceptions.RequestException as e:
            print(f"Error fetching users: {e}")
            sys.exit(1)

    def share_album_with_user(self, album_id: str, user_id: str, role: str) -> bool:
        """Share an album with a user or update their role."""
        url = f"{self.base_url}/api/albums/{album_id}/users"
        
        headers = {**self.headers, 'Content-Type': 'application/json'}
        payload = {
            "albumUsers": [
                {
                    "role": role,
                    "userId": user_id
                }
            ]
        }
        
        try:
            response = requests.put(url, headers=headers, data=json.dumps(payload), timeout=5)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error sharing album {album_id} with user {user_id}: {e}")
            return False

    def remove_user_from_album(self, album_id: str, user_id: str) -> bool:
        """Remove a user from an album."""
        url = f"{self.base_url}/api/albums/{album_id}/user/{user_id}"
        try:
            response = requests.delete(url, headers=self.headers, timeout=5)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error removing user {user_id} from album {album_id}: {e}")
            return False

    def get_current_album_users(self, album_id: str) -> Dict[str, str]:
        """Get current users and their roles for an album."""
        album_details = self.get_album_details(album_id)
        if not album_details:
            return {}
        
        current_users = {}
        for user_info in album_details.get('albumUsers', []):
            email = user_info.get('user', {}).get('email', '').lower()
            role = user_info.get('role', '')
            if email and role:
                current_users[email] = role
        return current_users

    def process_albums_to_csv(self, output_file: str = None):
        """Process all albums and create a CSV export."""
        print("Fetching albums...")
        albums = self.get_albums()
        
        if not albums:
            print("No albums found.")
            return

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"albums_{timestamp}.csv"

        processed_albums = []
        total_albums = len(albums)
        
        print(f"Processing {total_albums} albums...")
        for index, album in enumerate(albums, 1):
            if index % 10 == 0:  # Progress indicator every 10 albums
                print(f"Processing album {index}/{total_albums}")
                
            album_name = album.get('albumName', '')
            album_id = album.get('id', '')
            album_users = album.get('albumUsers', [])
            
            if not album_users:
                processed_albums.append({
                    'name': album_name,
                    'id': album_id,
                    'role': '',
                    'users': []
                })
            else:
                role_users = {}
                for user_info in album_users:
                    role = user_info.get('role', 'unknown')
                    user_email = user_info.get('user', {}).get('email', '')
                    
                    if role not in role_users:
                        role_users[role] = []
                    if user_email:
                        role_users[role].append(user_email)
                
                for role, users in role_users.items():
                    processed_albums.append({
                        'name': album_name,
                        'id': album_id,
                        'role': role,
                        'users': users
                    })

        max_users = max(len(album['users']) for album in processed_albums) if processed_albums else 0

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            headers = [self.COL_ALBUM_NAME, self.COL_ALBUM_ID, self.COL_ROLE] + \
                     [f'User {i+1}' for i in range(max_users)]
            writer = csv.writer(f, delimiter=';')
            writer.writerow(headers)

            for album in processed_albums:
                row = [
                    album['name'],
                    album['id'],
                    album['role']
                ] + album['users'] + [''] * (max_users - len(album['users']))
                writer.writerow(row)

        print(f"Created CSV file: {output_file}")
        print(f"Processed {len(albums)} albums into {len(processed_albums)} entries.")
        print(f"Maximum number of users in any album: {max_users}")

    def process_share_albums(self, input_file: str):
        """Process CSV file and synchronize album sharing permissions."""
        try:
            print("Fetching user email to ID mapping...")
            self.user_email_to_id = self.get_users()

            with open(input_file, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=';')
                headers = next(reader)
                
                # print("Debug: CSV Headers found:", headers)
                
                try:
                    name_idx = headers.index(self.COL_ALBUM_NAME)
                    id_idx = headers.index(self.COL_ALBUM_ID)
                    role_idx = headers.index(self.COL_ROLE)
                    user_indices = range(3, len(headers))
                except ValueError as e:
                    print(f"Error: Invalid CSV format. Required columns not found.")
                    print(f"Expected columns: {self.COL_ALBUM_NAME}, {self.COL_ALBUM_ID}, {self.COL_ROLE}")
                    print(f"Found columns: {', '.join(headers)}")
                    return

                stats = {
                    'total_albums': 0,
                    'successful_shares': 0,
                    'failed_shares': 0,
                    'users_removed': 0,
                    'removal_failures': 0,
                    'users_not_found': set()
                }

                # Group rows by album ID to process each album once
                album_data = {}
                for row in reader:
                    if not row:
                        continue
                    
                    album_id = row[id_idx].strip()
                    role = row[role_idx].strip().lower()
                    
                    if not album_id or not role:
                        continue

                    if album_id not in album_data:
                        album_data[album_id] = {'users': set(), 'role': role}

                    # Add all users from this row
                    for i in user_indices:
                        if i < len(row):
                            email = row[i].strip().lower()
                            if email:
                                album_data[album_id]['users'].add((email, role))

                # Process each album
                for album_id, data in album_data.items():
                    stats['total_albums'] += 1
                    
                    # Get album details for name
                    album_details = self.get_album_details(album_id)
                    album_name = album_details.get('albumName', 'Unknown Album') if album_details else 'Unknown Album'
                    print(f"\nProcessing album: {album_name} ({album_id})")
                    
                    # Get current users
                    current_users = self.get_current_album_users(album_id)
                    print(f"Current users in album: {len(current_users)}")

                    # Determine users to remove
                    desired_users = {email for email, _ in data['users']}
                    users_to_remove = set(current_users.keys()) - desired_users

                    # Remove unauthorized users
                    for email in users_to_remove:
                        user_id = self.user_email_to_id.get(email)
                        if user_id:
                            print(f"Removing user {email} from album {album_id}")
                            if self.remove_user_from_album(album_id, user_id):
                                stats['users_removed'] += 1
                                print(f"Successfully removed {email}")
                            else:
                                stats['removal_failures'] += 1
                                print(f"Failed to remove {email}")

                    # Add or update authorized users
                    for email, role in data['users']:
                        user_id = self.user_email_to_id.get(email)
                        if user_id:
                            current_role = current_users.get(email)
                            if current_role != role:
                                print(f"Updating/Adding user {email} with role {role}")
                                if self.share_album_with_user(album_id, user_id, role):
                                    stats['successful_shares'] += 1
                                else:
                                    stats['failed_shares'] += 1
                        else:
                            stats['users_not_found'].add(email)
                            stats['failed_shares'] += 1

                # Print final statistics
                print("\nOperation completed:")
                print(f"Total albums processed: {stats['total_albums']}")
                print(f"Successful shares/updates: {stats['successful_shares']}")
                print(f"Failed shares/updates: {stats['failed_shares']}")
                print(f"Users removed: {stats['users_removed']}")
                print(f"Failed removals: {stats['removal_failures']}")
                if stats['users_not_found']:
                    print("\nUsers not found:")
                    for email in sorted(stats['users_not_found']):
                        print(f"- {email}")

        except FileNotFoundError:
            print(f"Error: Input file '{input_file}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error processing file: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Process and share albums via API.')

    parser.add_argument('command', choices=['list-all', 'share-albums'], 
                      nargs='?', help='Command to execute (list-all or share-albums)')
    parser.add_argument('--url', help='Base URL for the API')
    parser.add_argument('--api-key', help='API key for authentication')
    parser.add_argument('--output', help='Output CSV file name (for list-all)')
    parser.add_argument('--input', help='Input CSV file name (for share-albums)')
    
    args = parser.parse_args()

    if not args.command or not args.url or not args.api_key:
        parser.print_help()
        sys.exit(1)

    processor = AlbumAPIProcessor(args.url, args.api_key)

    if args.command == 'list-all':
        processor.process_albums_to_csv(args.output)
    elif args.command == 'share-albums':
        if not args.input:
            print("Error: --input file is required for share-albums command")
            sys.exit(1)
        processor.process_share_albums(args.input)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
