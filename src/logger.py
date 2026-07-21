import logging
from pathlib import Path

_logging_configured = False


def setup_logging(log_file: str = None, level=logging.INFO):
    global _logging_configured

    if _logging_configured:
        return

    if log_file is None:
        project_root = Path(__file__).parent.parent
        log_file = project_root / "logs" / "log.txt"
    else:
        log_file = Path(log_file)

    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(),
        ],
    )

    # Bibliothèques réseau et HTTP
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # Bibliothèques async
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)

    # Bases de données
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("psycopg").setLevel(logging.WARNING)

    # Web frameworks
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("django").setLevel(logging.WARNING)

    # Data & ML
    logging.getLogger("tensorflow").setLevel(logging.WARNING)
    logging.getLogger("torch").setLevel(logging.WARNING)
    logging.getLogger("transformers").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    # Autres outils courants
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    logging.getLogger("celery").setLevel(logging.WARNING)
    logging.getLogger("kombu").setLevel(logging.WARNING)

    _logging_configured = True


setup_logging()
