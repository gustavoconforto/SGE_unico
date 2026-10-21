import shutil
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "db.sqlite3"


def run_managepy(*args: str) -> None:
    """Run a Django manage.py command."""
    command = [sys.executable, "manage.py", *args]

    print(f"\n→ {' '.join(command)}")

    subprocess.run(
        command,
        cwd=BASE_DIR,
        check=True,
    )


def delete_database() -> None:
    if DB_FILE.exists():
        print(f"Deleting database: {DB_FILE}")
        DB_FILE.unlink()
    else:
        print("Database does not exist. Skipping.")


def delete_migrations() -> None:
    print("\nDeleting migration files...")

    for migrations_dir in BASE_DIR.rglob("migrations"):
        # Ignore virtual environments and other unwanted directories
        if any(
            part
            in {
                ".venv",
                "venv",
                "site-packages",
                "node_modules",
            }
            for part in migrations_dir.parts
        ):
            continue

        for file in migrations_dir.iterdir():
            if file.name == "__init__.py":
                continue

            if file.is_file() and file.suffix == ".py":
                print(f"Deleting: {file}")
                file.unlink()

            elif file.is_file() and file.suffix == ".pyc":
                file.unlink()

        # Delete __pycache__ if present
        pycache = migrations_dir / "__pycache__"

        if pycache.exists():
            shutil.rmtree(pycache)


def create_migrations() -> None:
    run_managepy("makemigrations")


def migrate() -> None:
    run_managepy("migrate")


SEED_COMMANDS = {"1": "clean", "2": "seed", "3": "full_seed"}


def load_initial_data(option: str) -> None:
    run_managepy(SEED_COMMANDS[option])


def main() -> None:
    print(
        "Choose 1 for clean DB, 2 to clean and populate DB or 3 for clean and full populate DB"
    )
    option = input("-> ").strip()
    if option not in SEED_COMMANDS:
        sys.exit(f"Invalid option: {option!r}. Nothing was deleted.")
    print("=" * 60)
    print("RESETTING DEVELOPMENT DATABASE")
    print("=" * 60)

    delete_database()
    delete_migrations()

    create_migrations()
    migrate()

    load_initial_data(option)

    print("\n" + "=" * 60)
    print("Development database successfully recreated.")
    print("=" * 60)


if __name__ == "__main__":
    main()
