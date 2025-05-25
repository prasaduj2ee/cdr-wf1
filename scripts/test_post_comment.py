import os
import requests

# Load environment variables
repo = os.environ["REPO"]  # e.g. 'username/repo'
sha = os.environ["COMMIT_SHA"]
token = os.environ["GITHUB_TOKEN"]

# GitHub API URL for commit comments
url = f"https://api.github.com/repos/{repo}/commits/{sha}/comments"

# Prepare headers and comment body
headers = {
    "Authorization": f"Bearer {token}",
    "Accept": "application/vnd.github.v3+json"
}

payload = {
    "body": "✅ Test comment posted by GitHub Actions!"
}

# Make the POST request
response = requests.post(url, headers=headers, json=payload)

# Output result
print(f"Status: {response.status_code}")
print(f"Response: {response.text}")
