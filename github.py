#!/usr/bin/env python3
import os
import time
import json
import subprocess
import threading
from pathlib import Path
import getpass

CONFIG_PATH = str(Path.home() / ".github_sync_config.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

def save_config(cfg):
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=4)

def run(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out.decode(), err.decode()

def first_time_setup():
    print("\n--- GitHub Setup ---")

    username = input("GitHub Username: ").strip()
    token = getpass.getpass("GitHub Personal Access Token: ").strip()

    cfg = {
        "username": username,
        "token": token
    }
    save_config(cfg)
    print("Credentials saved.\n")
    return cfg

def detect_project_folder():
    return os.getcwd()

def create_repo_if_needed(cfg, project_path):
    folder_name = os.path.basename(project_path)
    repo_name = folder_name.replace(" ", "-")

    print(f"\nChecking repository: {repo_name}")

    # Check if .git folder exists
    if not os.path.exists(os.path.join(project_path, ".git")):
        print("No git repo found. Initializing…")
        run("git init")
        run("git branch -M main")

    # Check remote
    out, _ = run("git remote -v")
    if "origin" in out:
        print("Remote already configured.")
        return repo_name

    print("Creating repo on GitHub…")

    curl_cmd = (
        f'curl -u "{cfg["username"]}:{cfg["token"]}" '
        f'https://api.github.com/user/repos -d \'{{"name": "{repo_name}"}}\''
    )
    out, err = run(curl_cmd)

    if "created_at" in out:
        print("Repository created successfully.")
    else:
        print("Repo may already exist. Linking to existing repo…")

    remote_url = f"https://{cfg['username']}:{cfg['token']}@github.com/{cfg['username']}/{repo_name}.git"
    run(f"git remote add origin {remote_url}")

    return repo_name

def git_sync_loop(project_path):
    while True:
        run("git add .")
        out, err = run('git commit -m "auto-sync"')
        if "nothing to commit" not in out:
            print("[SYNC] Committed changes.")
            run("git push origin main")
            print("[SYNC] Pushed to GitHub.")

        time.sleep(15)

def menu():
    cfg = load_config()
    if not cfg:
        cfg = first_time_setup()

    while True:
        print("\n========== GitHub Sync Menu ==========")
        print("1. Detect project folder and link")
        print("2. Start background auto-sync")
        print("3. Change Github Credentials")
        print("4. Exit")
        choice = input("Choose: ").strip()

        if choice == "1":
            project = detect_project_folder()
            print(f"Detected Project: {project}")
            create_repo_if_needed(cfg, project)

        elif choice == "2":
            project = detect_project_folder()
            print(f"Syncing Project: {project}")
            create_repo_if_needed(cfg, project)

            print("Auto-sync running in background every 15s…")
            t = threading.Thread(target=git_sync_loop, args=(project,), daemon=True)
            t.start()

            while True:
                time.sleep(1)

        elif choice == "3":
            cfg = first_time_setup()

        elif choice == "4":
            print("Bye.")
            break

        else:
            print("Invalid option.")

if __name__ == "__main__":
    menu()

