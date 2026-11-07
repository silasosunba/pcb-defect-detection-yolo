"""Create the first administrator interactively. Never accepts a password on argv."""

import argparse
import getpass
import psycopg
import time
import uuid

from pydantic import EmailStr, TypeAdapter

from backend.config import Settings
from backend.db import close_pool, connect, initialize
from backend.security import audit, passwords


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["create-admin", "migrate", "check-db"])
    parser.add_argument("--email")
    parser.add_argument("--name", default="Administrator")
    args = parser.parse_args()
    settings = Settings()

    try:

        if args.command == "check-db":

            with connect(settings) as db:

                db.execute("SELECT 1 AS connected").fetchone()

            print("PostgreSQL connection verified.")

            return

        if args.command == "create-admin" and not args.email:

            parser.error("--email is required for create-admin")

        initialize(settings)

        if args.command == "migrate":

            print("PostgreSQL migrations applied successfully.")

            return

        email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
        name = args.name.strip()

        if not 2 <= len(name) <= 80:

            raise SystemExit("The administrator name must contain 2–80 characters.")

        password = getpass.getpass("Admin password (12–128 characters): ")

        if not 12 <= len(password) <= 128 or password != getpass.getpass(
            "Confirm password: "
        ):

            raise SystemExit("Passwords must match and contain 12–128 characters.")

        user_id = str(uuid.uuid4())

        with connect(settings) as db:

            db.execute(
                "INSERT INTO users(id,name,email,password_hash,role,created_at) VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    user_id,
                    name,
                    email,
                    passwords.hash(password),
                    "admin",
                    int(time.time()),
                ),
            )
            audit(db, user_id, "admin.created_cli", user_id)

        print(f"Administrator created: {email}")

    except psycopg.errors.UniqueViolation:

        raise SystemExit(
            "An account with that email already exists. Use another email or an existing administrator to change its role."
        )

    finally:

        close_pool(settings)



if __name__ == "__main__":

    main()
