"""Generate a TOTP secret for the admin UI."""
from __future__ import annotations

import argparse

import pyotp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Generate a new secret")
    args = parser.parse_args()

    secret = pyotp.random_base32()
    if args.reset:
        print("Resetting TOTP secret...")
    print(f"TOTP_SECRET=\"{secret}\"")
    print("Use this secret in your .env file.")


if __name__ == "__main__":
    main()
