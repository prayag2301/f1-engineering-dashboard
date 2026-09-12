"""Create local credentials; retain the original Compose database credential on upgrades."""

from pathlib import Path
import secrets
import subprocess

root = Path(__file__).resolve().parents[1]
path = root / ".env"
existing = path.read_text() if path.exists() else ""
keys = {
    line.split("=", 1)[0]
    for line in existing.splitlines()
    if "=" in line and line.split("=", 1)[1].strip()
}
missing = {
    key: secrets.token_urlsafe(32)
    for key in ("ADMIN_TOKEN", "SESSION_SECRET", "POSTGRES_PASSWORD")
    if key not in keys
}
if "POSTGRES_PASSWORD" in missing:
    try:
        legacy = (
            subprocess.run(
                ["docker", "volume", "inspect", "f1-engineering-dashboard_pgdata"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            ).returncode
            == 0
        )
    except (OSError, subprocess.TimeoutExpired):
        legacy = False
    if legacy:
        # This was the hardcoded credential in the previous repository's Compose file.
        # Never alter the database password or overwrite an existing .env setting.
        missing["POSTGRES_PASSWORD"] = "f1pass"
        print(
            "Existing legacy volume found. Retaining its original Compose credential."
        )
if missing:
    with path.open("a") as out:
        out.write(
            "\n" + "\n".join(f"{key}={value}" for key, value in missing.items()) + "\n"
        )
path.chmod(0o600)
print("Local credentials are ready in .env. Use ADMIN_TOKEN to sign in at /review.")
