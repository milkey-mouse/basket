"""uWSGI starts the app through this entry point."""
from . import create_app

app = create_app()
if __name__ == "__main__":
    app.run()
