import os
import openai
import requests
import json

openai.api_key = os.getenv("OPENAI_API_KEY")
github_token = os.getenv("GITHUB_TOKEN")
repo = os.getenv("GITHUB_REPOSITORY")
ref = os.getenv("GITHUB_REF")
pr_number = ref.split("/")[-1] if ref and "pull" in ref else None

def get_diff():
    if not pr_number:
        print("Not a pull request context.")
        return ""

    headers = {"Authorization": f"token {github_token}"}
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch PR files: {response.status_code}")
        return ""

    files = response.json()
    diff_texts = []
    for f in files:
        if f.get("patch"):
            diff_texts.append(f"File: {f['filename']}\n{f['patch']}")
    return "\n\n".join(diff_texts)

def review_code(diff):
    prompt = f"""You are a senior software engineer reviewing a pull request.
Review the following Git diff and provide constructive, specific feedback for improvements, potential bugs, best practices, or style violations:

{diff}"""

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful and precise code reviewer."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return response["choices"][0]["message"]["content"]

def comment_on_pr(review):
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {"body": review}
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code != 201:
        print("Failed to post review comment:", response.text)
    else:
        print("AI review comment posted successfully.")

if __name__ == "__main__":
    diff = get_diff()
    if diff:
        review = review_code(diff)
        comment_on_pr(review)
    else:
        print("No diff found or not a PR context.")
