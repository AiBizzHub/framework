# Copyright (c) 2015, AiBizzHub, LLC and Contributors
# License: MIT. See LICENSE

import json
import os
import subprocess  # nosec
from contextlib import suppress

from semantic_version import SimpleSpec, Version

import frappe
from frappe import _, safe_decode
from frappe.utils import cstr
from frappe.utils.caching import redis_cache
from frappe.utils.frappecloud import on_frappecloud

def get_change_log(user=None):
    if not user:
        user = frappe.session.user

    last_known_versions = frappe._dict(
        json.loads(frappe.db.get_value("User", user, "last_known_versions") or "{}")
    )
    current_versions = get_versions()

    if not last_known_versions:
        update_last_known_versions()
        return []

    change_log = []

    def set_in_change_log(app, opts, change_log):
        from_version = last_known_versions.get(app, {}).get("version") or "0.0.1"
        to_version = opts["version"]

        if from_version != to_version:
            app_change_log = get_change_log_for_app(app, from_version=from_version, to_version=to_version)

            if app_change_log:
                change_log.append(
                    {
                        "title": opts["title"],
                        "description": opts["description"],
                        "version": to_version,
                        "change_log": app_change_log,
                    }
                )

    for app, opts in current_versions.items():
        if app != "frappe":
            set_in_change_log(app, opts, change_log)

    if "frappe" in current_versions:
        set_in_change_log("frappe", current_versions["frappe"], change_log)

    return change_log

def get_change_log_for_app(app, from_version, to_version):
    change_log_folder = os.path.join(frappe.get_app_path(app), "change_log")
    if not os.path.exists(change_log_folder):
        return

    from_version = Version(from_version)
    to_version = Version(to_version)
    # remove pre-release part
    to_version.prerelease = None

    major_version_folders = [f"v{i}" for i in range(from_version.major, to_version.major + 1)]
    app_change_log = []

    for folder in os.listdir(change_log_folder):
        if folder in major_version_folders:
            for file in os.listdir(os.path.join(change_log_folder, folder)):
                version = Version(os.path.splitext(file)[0][1:].replace("_", "."))

                if from_version < version <= to_version:
                    file_path = os.path.join(change_log_folder, folder, file)
                    content = frappe.read_file(file_path)
                    app_change_log.append([version, content])

    app_change_log = sorted(app_change_log, key=lambda d: d[0], reverse=True)

    # convert version to string and send
    return [[cstr(d[0]), d[1]] for d in app_change_log]

@frappe.whitelist()
def update_last_known_versions():
    frappe.db.set_value(
        "User",
        frappe.session.user,
        "last_known_versions",
        json.dumps(get_versions()),
        update_modified=False,
    )

@frappe.whitelist()
def get_versions():
    """Get versions of all installed apps.

    Example:

            {
                    "frappe": {
                            "title": "AiBizzApp Framework",
                            "version": "5.0.0"
                    }
            }"""
    versions = {}
    for app in frappe.get_installed_apps(_ensure_on_bench=True):
        app_hooks = frappe.get_hooks(app_name=app)
        versions[app] = {
            "title": app_hooks.get("app_title")[0],
            "description": app_hooks.get("app_description")[0],
            "branch": get_app_branch(app),
        }

        if versions[app]["branch"] != "master":
            branch_version = app_hooks.get("{}_version".format(versions[app]["branch"]))
            if branch_version:
                versions[app]["branch_version"] = branch_version[0] + f" ({get_app_last_commit_ref(app)})"

        try:
            versions[app]["version"] = frappe.get_attr(app + ".__version__")
        except AttributeError:
            versions[app]["version"] = "0.0.1"

    return versions

def get_app_branch(app):
    """Return branch of an app."""
    try:
        with open(os.devnull, "wb") as null_stream:
            result = subprocess.check_output(
                f"cd ../apps/{app} && git rev-parse --abbrev-ref HEAD",
                shell=True,
                stdin=null_stream,
                stderr=null_stream,
            )
        result = safe_decode(result)
        result = result.strip()
        return result
    except Exception:
        return ""

def get_app_last_commit_ref(app):
    try:
        with open(os.devnull, "wb") as null_stream:
            result = subprocess.check_output(
                f"cd ../apps/{app} && git rev-parse HEAD --short 7",
                shell=True,
                stdin=null_stream,
                stderr=null_stream,
            )
        result = safe_decode(result)
        result = result.strip()
        return result
    except Exception:
        return ""

def check_for_update():
    # This function is now a no-op
    pass

def has_app_update_notifications() -> bool:
    return False

def parse_latest_non_beta_release(response: list, current_version: Version) -> list | None:
    """Parse the response JSON for all the releases and return the latest non prerelease.

    Args:

    response (list): response object returned by github

    Return a json object pertaining to the latest non-beta release
    """
    version_list = [
        release.get("tag_name").strip("v") for release in response if not release.get("prerelease")
    ]

    def prioritize_minor_update(v: str) -> Version:
        target = Version(v)
        return (current_version.major == target.major, target)

    if version_list:
        return sorted(version_list, key=prioritize_minor_update, reverse=True)[0]

    return None

def check_release_on_github(
    owner: str, repo: str, current_version: Version
) -> tuple[Version, str] | tuple[None, None]:
    """Check the latest release for a repo URL on GitHub."""
    import requests

    if not owner:
        raise ValueError("Owner cannot be empty")

    if not repo:
        raise ValueError("Repo cannot be empty")

    # Get latest version from GitHub
    releases = _get_latest_releases(owner, repo)
    latest_non_beta_release = parse_latest_non_beta_release(releases, current_version)
    if latest_non_beta_release:
        return Version(latest_non_beta_release), owner

    return None, None

def security_issues_count(owner: str, repo: str, current_version: Version, target_version: Version) -> int:
    advisories = _get_security_issues(owner, repo)

    def applicable(advisory) -> bool:
        # Current version is in vulnerable range
        # Target version is not in vulnerabe range
        for vuln in advisory["vulnerabilities"]:
            with suppress(Exception):
                vulnerable_range = SimpleSpec(vuln["vulnerable_version_range"].replace(" ", ""))
                patch_version = Version(vuln["patched_versions"].replace(" ", ""))
                if (
                    current_version in vulnerable_range
                    and target_version not in vulnerable_range
                    # XXX: this is not 100% correct, but works for frappe
                    and current_version.major == patch_version.major
                ):
                    return True

    return len([sa for sa in advisories if applicable(sa)])

@redis_cache(ttl=6 * 24 * 60 * 60, shared=True)
def _get_latest_releases(owner, repo):
    import requests

    r = requests.get(f"https://api.github.com/repos/{owner}/{repo}/releases")
    if not r.ok:
        return []

    return r.json()

@redis_cache(ttl=6 * 24 * 60 * 60, shared=True)
def _get_security_issues(owner, repo):
    import requests

    r = requests.get(f"https://api.github.com/repos/{owner}/{repo}/security-advisories")
    if not r.ok:
        return []

    return r.json()

def parse_github_url(remote_url: str) -> tuple[str, str] | tuple[None, None]:
    """Parse the remote URL to get the owner and repo name."""
    import re

    if not remote_url:
        raise ValueError("Remote URL cannot be empty")

    pattern = r"github\.com[:/](.+)\/([^\.]+)"
    match = re.search(pattern, remote_url)

    return (match[1], match[2]) if match else (None, None)

def get_source_url(app: str) -> str | None:
    """Get the remote URL of the app."""
    pyproject = get_pyproject(app)
    if not pyproject:
        return
    if remote_url := pyproject.get("project", {}).get("urls", {}).get("Repository"):
        return remote_url.rstrip("/")

def add_message_to_redis(update_json):
    # This function is now a no-op
    pass

@frappe.whitelist()
def show_update_popup():
    # This function is now a no-op
    pass

def get_pyproject(app: str) -> dict | None:
    from tomli import load

    pyproject_path = frappe.get_app_path(app, "..", "pyproject.toml")

    if not os.path.exists(pyproject_path):
        return None

    with open(pyproject_path, "rb") as f:
        return load(f)
