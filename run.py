"""Development entrypoint.

Use this for local work only. For anything user-facing, serve `wsgi:app` with
gunicorn (Linux) or waitress (Windows) — see the README.
"""

import argparse

from app import create_app


def main():
    parser = argparse.ArgumentParser(description="Run the Paw-Patrol dev server")
    parser.add_argument("--host", default="127.0.0.1", help="bind address")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    parser.add_argument("--env", default=None, help="development | production | testing")
    args = parser.parse_args()

    app = create_app(args.env)
    app.run(host=args.host, port=args.port, debug=app.config["DEBUG"], threaded=True)


if __name__ == "__main__":
    main()
