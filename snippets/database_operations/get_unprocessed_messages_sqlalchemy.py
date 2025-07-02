import logging
from typing import List, Dict, Any, Optional
from datetime import datetime # For MessageModel definition

# SQLAlchemy imports - for type hinting and example model definition
try:
    from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean # Removed desc as default is asc
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.ext.declarative import declarative_base
    SQLALCHEMY_AVAILABLE = True
    Base = declarative_base()

    # Define a Message model similar to the one in the original project for context.
    class MessageModel(Base): # type: ignore
        __tablename__ = "messages_example_get_unprocessed" # Example table name
        id = Column(Integer, primary_key=True)
        line_message_id = Column(String(255), unique=True, index=True)
        user_id = Column(String(255), index=True)
        message_type = Column(String(50))
        content = Column(Text)
        summary = Column(Text)
        file_path = Column(String(1024))
        processed = Column(Boolean, default=False, nullable=False, index=True) # Ensure indexed for filter
        created_at = Column(DateTime, default=datetime.utcnow, index=True) # Ensure indexed for order_by
        # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        def to_dict(self): # Helper to convert model to dict
            return {c.name: getattr(self, c.name) for c in self.__table__.columns}

except ImportError:
    SQLALCHEMY_AVAILABLE = False
    class Base: pass # type: ignore
    class Column: pass # type: ignore
    class Integer: pass # type: ignore
    class String: pass # type: ignore
    class DateTime: pass # type: ignore
    class Text: pass # type: ignore
    class Boolean: pass # type: ignore
    class Session: pass # type: ignore
    class MessageModel(Base): # type: ignore
        processed = False
        created_at = datetime.now()
        def to_dict(self): return {}
    def sessionmaker(bind): return None
    def create_engine(constr): return None

logger = logging.getLogger(__name__)

def get_unprocessed_messages_sqlalchemy(
    db_session: Any, # Should be a SQLAlchemy Session object
    message_model_cls: Any, # The SQLAlchemy model class (e.g., MessageModel)
    limit: Optional[int] = None, # Optional limit on the number of messages to fetch
    order_by_creation: str = "asc" # "asc" for oldest first (typical for processing queues)
) -> List[Dict[str, Any]]:
    """
    Retrieves messages marked as 'unprocessed' from the database using SQLAlchemy,
    typically ordered by creation time to process oldest first.

    Args:
        db_session: The active SQLAlchemy session.
        message_model_cls: The SQLAlchemy model class for messages.
                           It must have 'processed' (boolean) and 'created_at' attributes/columns.
        limit (Optional[int], optional): The maximum number of unprocessed messages
                                         to retrieve. If None, retrieves all. Defaults to None.
        order_by_creation (str, optional): Order of messages by creation time.
                                           "asc" for oldest first, "desc" for newest first.
                                           Defaults to "asc".

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents
                              an unprocessed message object. Returns an empty list on error
                              or if no unprocessed messages are found.
    """
    if not SQLALCHEMY_AVAILABLE:
        logger.error("SQLAlchemy library is not available. Cannot get unprocessed messages.")
        return []
    if not isinstance(db_session, Session):
        logger.error("db_session is not a valid SQLAlchemy Session.")
        return []
    if not hasattr(message_model_cls, "processed") or not hasattr(message_model_cls, "created_at"):
        logger.error("message_model_cls must have 'processed' and 'created_at' attributes.")
        return []

    try:
        query = db_session.query(message_model_cls).filter_by(processed=False)

        if order_by_creation.lower() == "asc":
            query = query.order_by(message_model_cls.created_at) # Default .asc() if not specified after order_by
        elif order_by_creation.lower() == "desc":
            # Need to import `desc` from sqlalchemy for this if not already globally available
            from sqlalchemy import desc as sql_desc
            query = query.order_by(sql_desc(message_model_cls.created_at))
        else:
            logger.warning(f"Invalid order_by_creation value: '{order_by_creation}'. Defaulting to ascending.")
            query = query.order_by(message_model_cls.created_at)

        if limit is not None and isinstance(limit, int) and limit > 0:
            query = query.limit(limit)

        unprocessed_messages = query.all()

        return [msg.to_dict() for msg in unprocessed_messages if hasattr(msg, 'to_dict')]

    except Exception as e:
        logger.error(f"Error retrieving unprocessed messages: {e}", exc_info=True)
        return []

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if not SQLALCHEMY_AVAILABLE:
        print("SQLAlchemy not available. Skipping get_unprocessed_messages tests.")
    else:
        # --- Setup In-Memory SQLite Database for Testing ---
        engine_unprocessed = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine_unprocessed) # Create tables
        SessionLocalUnprocessed = sessionmaker(autocommit=False, autoflush=False, bind=engine_unprocessed)
        db_unprocessed = SessionLocalUnprocessed()

        # --- Populate with test data ---
        db_unprocessed.add(MessageModel(line_message_id="unproc_m1", user_id="userA", message_type="text", content="Unprocessed 1", processed=False, created_at=datetime(2023, 2, 1, 9, 0, 0)))
        db_unprocessed.add(MessageModel(line_message_id="proc_m1", user_id="userA", message_type="text", content="Processed 1", processed=True, created_at=datetime(2023, 2, 1, 9, 5, 0)))
        db_unprocessed.add(MessageModel(line_message_id="unproc_m2", user_id="userB", message_type="image", file_path="/img/u2.jpg", processed=False, created_at=datetime(2023, 2, 1, 8, 0, 0))) # Older
        db_unprocessed.add(MessageModel(line_message_id="unproc_m3", user_id="userA", message_type="text", content="Unprocessed 2", processed=False, created_at=datetime(2023, 2, 1, 9, 10, 0))) # Newer
        db_unprocessed.commit()

        print(f"\n--- Test Case 1: Get all unprocessed messages (ordered by oldest first by default) ---")
        all_unprocessed = get_unprocessed_messages_sqlalchemy(db_unprocessed, MessageModel)
        print(f"Found {len(all_unprocessed)} unprocessed messages:")
        for msg_dict in all_unprocessed:
            print(f"  ID: {msg_dict.get('line_message_id')}, Processed: {msg_dict.get('processed')}, Created: {msg_dict.get('created_at')}")
        assert len(all_unprocessed) == 3
        if len(all_unprocessed) == 3:
            assert all_unprocessed[0]["line_message_id"] == "unproc_m2" # Oldest
            assert all_unprocessed[1]["line_message_id"] == "unproc_m1"
            assert all_unprocessed[2]["line_message_id"] == "unproc_m3" # Newest among unprocessed

        print(f"\n--- Test Case 2: Get 1 unprocessed message (oldest first) ---")
        limited_unprocessed = get_unprocessed_messages_sqlalchemy(db_unprocessed, MessageModel, limit=1)
        print(f"Found {len(limited_unprocessed)} unprocessed messages with limit 1:")
        assert len(limited_unprocessed) == 1
        if limited_unprocessed:
            print(f"  ID: {limited_unprocessed[0].get('line_message_id')}")
            assert limited_unprocessed[0]["line_message_id"] == "unproc_m2"

        print(f"\n--- Test Case 3: Get unprocessed messages ordered by newest first ---")
        newest_unprocessed = get_unprocessed_messages_sqlalchemy(db_unprocessed, MessageModel, order_by_creation="desc")
        print(f"Found {len(newest_unprocessed)} unprocessed messages (newest first):")
        for msg_dict in newest_unprocessed:
            print(f"  ID: {msg_dict.get('line_message_id')}, Created: {msg_dict.get('created_at')}")
        assert len(newest_unprocessed) == 3
        if len(newest_unprocessed) == 3:
            assert newest_unprocessed[0]["line_message_id"] == "unproc_m3" # Newest
            assert newest_unprocessed[1]["line_message_id"] == "unproc_m1"
            assert newest_unprocessed[2]["line_message_id"] == "unproc_m2" # Oldest

        # Mark one as processed and re-fetch
        msg_to_process = db_unprocessed.query(MessageModel).filter_by(line_message_id="unproc_m2").first()
        if msg_to_process:
            msg_to_process.processed = True
            db_unprocessed.commit()
            print(f"\n--- Test Case 4: Get unprocessed after marking one as processed ---")
            remaining_unprocessed = get_unprocessed_messages_sqlalchemy(db_unprocessed, MessageModel)
            print(f"Found {len(remaining_unprocessed)} unprocessed messages after update:")
            assert len(remaining_unprocessed) == 2
            for msg_dict in remaining_unprocessed:
                assert msg_dict.get("processed") is False
                print(f"  ID: {msg_dict.get('line_message_id')}")


        db_unprocessed.close()
        print("\nIn-memory database tests for get_unprocessed_messages complete.")

    print("\nNote: This snippet requires a SQLAlchemy Session and a mapped Message model class with 'processed' (boolean) and 'created_at' fields.")
