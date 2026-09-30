import pytest
from sqlalchemy.orm import Session

from database.session import get_engine


@pytest.fixture
def db() -> Session:
    """A DB session wrapped in a transaction that's always rolled back, so
    integration tests never leave rows behind in the dev database.
    """
    connection = get_engine().connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
