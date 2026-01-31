#!/usr/bin/env python3
"""
Update API key in the database from .env file
This script updates the provider's API key without losing other data
"""

import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get the new API key from .env
new_api_key = os.getenv('API_KEY')
provider_name = os.getenv('PROVIDER_NAME', 'OpenAI')
database_path = os.getenv('DATABASE_PATH', 'Xion.db')

if not new_api_key:
    print("❌ ERROR: API_KEY not found in .env file")
    exit(1)

print(f"🔄 Updating API key for provider '{provider_name}' in database...")
print(f"   Database: {database_path}")
print(f"   New API Key: {new_api_key[:10]}...{new_api_key[-4:]}")

try:
    # Connect to database
    conn = sqlite3.connect(database_path)
    cursor = conn.cursor()
    
    # Update the API key for the provider
    cursor.execute(
        "UPDATE providers SET api_key = ? WHERE name = ?",
        (new_api_key, provider_name)
    )
    
    rows_updated = cursor.rowcount
    conn.commit()
    
    if rows_updated > 0:
        print(f"✅ Successfully updated {rows_updated} provider(s)")
        
        # Verify the update
        cursor.execute("SELECT id, name, api_key FROM providers WHERE name = ?", (provider_name,))
        result = cursor.fetchone()
        if result:
            print(f"   Provider ID: {result[0]}")
            print(f"   Provider Name: {result[1]}")
            print(f"   API Key: {result[2][:10]}...{result[2][-4:]}")
    else:
        print(f"⚠️  No provider found with name '{provider_name}'")
        print("   The app will create a new provider on next startup")
    
    conn.close()
    
    print("\n✅ Done! Please restart the app for changes to take effect.")
    
except sqlite3.Error as e:
    print(f"❌ Database error: {e}")
    exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
