import os
import xml.etree.ElementTree as ET
import requests
import json

# ENV variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
COMMIT_SHA = os.getenv("COMMIT_SHA")
REPO = os.getenv("REPO")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

BASE_API = f"https://api.github.com/repos/{REPO}/commits/{COMMIT_SHA}/comments"

# --- Fetch diff info to determine which lines changed ---
def get_commit_diff_lines():
    """Fetch diff and return a dict of {file_path: set of changed lines}"""
    diff_url = f"https://api.github.com/repos/{REPO}/commits/{COMMIT_SHA}"
    response = requests.get(diff_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Failed to fetch commit diff: {response.status_code}")
        return {}

    files_changed = response.json().get("files", [])
    diff_map = {}

    for f in files_changed:
        path = f["filename"]
        patch = f.get("patch", "")
        changed_lines = set()
        old_line = None
        new_line = None
        for line in patch.splitlines():
            if line.startswith("@@"):
                # Parse diff hunk: @@ -old_start,old_count +new_start,new_count @@
                try:
                    new_info = line.split("@@")[1].split("+")[1].split(" ")[0]
                    new_start = int(new_info.split(",")[0])
                    new_line = new_start - 1
                except:
                    continue
            elif line.startswith("+") and not line.startswith("+++"):
                new_line += 1
                changed_lines.add(new_line)
            elif not line.startswith("-"):
                new_line += 1
        diff_map[path] = changed_lines
    return diff_map

DIFF_LINES = get_commit_diff_lines()

# --- Post comment depending on line change status ---
def post_comment(file_path, line, message):
    file_path = file_path.strip()
    line_num = int(line) if line else None
    path_in_diff = DIFF_LINES.get(file_path, set())

    if line_num and line_num in path_in_diff:
        # Inline comment on a changed line
        payload = {
            "body": message,
            "path": file_path,
            "line": line_num,
            "position": 1  # required even though it's ignored for direct commits
        }
    else:
        # Fallback: general commit comment
        payload = {
            "body": f"{message}\n(file: `{file_path}`, line: {line})"
        }

    print("Posting comment:\n" + json.dumps(payload, indent=2))
    response = requests.post(BASE_API, headers=HEADERS, json=payload)
    print(f"Response {response.status_code}")
    if response.status_code != 201:
        print(response.text)

# --- Parse Checkstyle XML ---
def parse_checkstyle(xml_path):
    if not os.path.exists(xml_path):
        print(f"Checkstyle file not found: {xml_path}")
        return
    tree = ET.parse(xml_path)
    root = tree.getroot()
    for file_elem in root.findall("file"):
        file_path = file_elem.get("name")
        file_path = file_path[file_path.find("src/"):] if "src/" in file_path else file_path
        for error in file_elem.findall("error"):
            line = error.get("line")
            message = f"[Checkstyle] {error.get('message')}"
            post_comment(file_path, line, message)

# --- Parse PMD XML ---
def parse_pmd(xml_path):
    if not os.path.exists(xml_path):
        print(f"PMD file not found: {xml_path}")
        return
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Handle XML namespaces
    namespace = ''
    if root.tag.startswith('{'):
        namespace = root.tag.split('}')[0].strip('{')
        ns = {'ns': namespace}
    else:
        ns = {}

    file_elements = root.findall("ns:file", ns) if ns else root.findall("file")
    for file_elem in file_elements:
        file_path = file_elem.get("name")
        file_path = file_path[file_path.find("src/"):] if "src/" in file_path else file_path

        violations = file_elem.findall("ns:violation", ns) if ns else file_elem.findall("violation")
        for violation in violations:
            line = violation.get("beginline")
            message = f"[PMD] {violation.text.strip()}"
            post_comment(file_path, line, message)

# --- Run both parsers ---
parse_checkstyle("build/reports/checkstyle/main.xml")
parse_pmd("build/reports/pmd/main.xml")
