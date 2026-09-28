"""
Fetches live GitHub contribution data via the GraphQL API and saves it as JSON.

Usage: GITHUB_TOKEN=... python fetch_contributions.py <github_username> <output_json>

The GraphQL API requires a token. In GitHub Actions, pass one through the
GITHUB_TOKEN environment variable (see .github/workflows/update-profile-art.yml).
"""
import json
import os
import sys
import urllib.error
import urllib.request

QUERY = """
query($userName: String!) {
  user(login: $userName) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            weekday
            contributionCount
            contributionLevel
          }
        }
      }
    }
  }
}
"""

LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def fetch_calendar(username, token):
    payload = json.dumps({"query": QUERY, "variables": {"userName": username}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "profile-heatmap",
            "Authorization": f"Bearer {token}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} {e.reason}: {e.read().decode(errors='replace')}")
    if body.get("errors"):
        sys.exit(f"GraphQL error: {body['errors']}")
    user = (body.get("data") or {}).get("user")
    if not user:
        sys.exit(f"User '{username}' not found")
    return user["contributionsCollection"]["contributionCalendar"]


def main():
    if len(sys.argv) != 3:
        sys.exit("Usage: python fetch_contributions.py <github_username> <output_json>")
    username, output_path = sys.argv[1], sys.argv[2]

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN is not set; the GitHub GraphQL API requires a token.")

    cal = fetch_calendar(username, token)
    data = {
        "username": username,
        "total": cal["totalContributions"],
        "weeks": [
            [
                {
                    "date": d["date"],
                    "weekday": d["weekday"],
                    "count": d["contributionCount"],
                    "level": LEVELS.get(d["contributionLevel"], 0),
                }
                for d in w["contributionDays"]
            ]
            for w in cal["weeks"]
        ],
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=1)
    days = sum(len(w) for w in data["weeks"])
    print(f"Wrote {output_path} ({data['total']} contributions, {len(data['weeks'])} weeks, {days} days)")


if __name__ == "__main__":
    main()
