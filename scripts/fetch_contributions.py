"""
Fetches live GitHub contribution data via GraphQL API and saves it as JSON.

Usage: python fetch_contributions.py <github_username> <output_json>
"""
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta


def fetch_contributions_graphql(username, token=None):
    """Fetch contribution data using GitHub GraphQL API"""
    url = "https://api.github.com/graphql"
    
    # Query to get contribution collection
    query = """
    query($userName:String!) {
      user(login: $userName) {
        name
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                weekday
              }
            }
          }
        }
      }
    }
    """
    
    payload = {
        "query": query,
        "variables": {"userName": username}
    }
    
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }
    
    # Add token if available (increases rate limit)
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        
        with urllib.request.urlopen(req, timeout=10) as resp:
            response_data = json.loads(resp.read().decode('utf-8'))
            
            # Check for errors in GraphQL response
            if 'errors' in response_data:
                print(f"GraphQL Error: {response_data['errors']}")
                sys.exit(1)
            
            return response_data['data']['user']['contributionsCollection']['contributionCalendar']
    
    except urllib.error.HTTPError as e:
        print(f"Error: Failed to fetch data for user '{username}'")
        print(f"HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Network error - {e.reason}")
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching contributions: {e}")
        sys.exit(1)


def convert_to_grid_format(calendar_data):
    """Convert GraphQL response to grid format compatible with renderer"""
    cells = []
    row = 0
    
    for week in calendar_data['weeks']:
        col = 0
        for day in week['contributionDays']:
            cells.append({
                "date": day['date'],
                "level": min(4, day['contributionCount'] // 10) if day['contributionCount'] > 0 else 0,
                "row": row,
                "col": col
            })
            col += 1
        row += 1
    
    # Extract months from dates
    months_dict = {}
    for cell in cells:
        month_date = cell['date'][:7]  # YYYY-MM
        if month_date not in months_dict:
            months_dict[month_date] = month_date
    
    months = [{"span": 4, "name": month.split('-')[1]} for month in sorted(months_dict.keys())]
    
    return {
        "total": str(calendar_data['totalContributions']),
        "months": months,
        "cells": cells
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: python fetch_contributions.py <github_username> <output_json>")
        sys.exit(1)

    username, output_path = sys.argv[1], sys.argv[2]
    
    # Try to get GitHub token from environment (optional)
    token = None
    try:
        # Attempt to read from environment variable
        import os
        token = os.environ.get('GITHUB_TOKEN')
    except:
        pass
    
    # Fetch contribution data via GraphQL
    calendar_data = fetch_contributions_graphql(username, token)
    
    # Convert to expected format
    data = {
        "username": username,
        **convert_to_grid_format(calendar_data)
    }

    # Write to file
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Wrote {output_path} ({data['total']} contributions, {len(data['cells'])} cells)")


if __name__ == "__main__":
    main()
