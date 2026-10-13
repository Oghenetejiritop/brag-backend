
"""
Create a BRAG API key for an existing development user.

Run locally only. Do not use this script as a public API.
"""

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models.user import User
from app.services.authentication_service import AuthenticationService


def main() -> None:
    """Generate an API key for a selected active user."""

    with SessionLocal() as session:
        users = list(
            session.scalars(
                select(User).order_by(User.id)
            ).all()
        )

        if not users:
            print(
                "No users exist in the database. "
                "Create a development user first."
            )
            return

        print("Existing BRAG users:")

        for user in users:
            print(
                f"User ID: {user.user_id}, "
                f"Active: {user.is_active}"
            )

        selected_id = input(
            "Enter the public user ID to issue a key for: "
        ).strip()

        selected_user = next(
            (
                user for user in users
                if str(user.user_id) == selected_id
            ),
            None,
        )

        if selected_user is None:
            print("User not found. No key created.")
            return

        if not selected_user.is_active:
            print("User is inactive. No key created.")
            return

        authentication_service = AuthenticationService(
            database_session=session
        )

        result = authentication_service.create_api_key(
            user=selected_user
        )

        print("\nAPI key created successfully.")
        print("Copy the key below into Swagger.")
        print("Do not share or commit this credential.")
        print(result.api_key)


if __name__ == "__main__":
    main()
