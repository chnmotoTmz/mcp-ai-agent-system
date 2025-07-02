import logging
from typing import List, Dict, Any, Optional
from datetime import datetime # For MessageModel definition

# SQLAlchemy imports - for type hinting and example model definition
try:
    from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, desc
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.ext.declarative import declarative_base
    SQLALCHEMY_AVAILABLE = True
    Base = declarative_base()

    # Define a Message model similar to the one in the original project for context.
    # User of this snippet would have their own SQLAlchemy model.
    class MessageModel(Base): # type: ignore
        __tablename__ = "messages_example_get_user" # Example table name
        id = Column(Integer, primary_key=True)
        line_message_id = Column(String(255), unique=True, index=True) # Not used in this query but part of model
        user_id = Column(String(255), nullable=False, index=True)
        message_type = Column(String(50))
        content = Column(Text)
        summary = Column(Text)
        file_path = Column(String(1024))
        processed = Column(Boolean, default=False)
        created_at = Column(DateTime, default=datetime.utcnow)
        # updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow) # Not used in this query

        def to_dict(self): # Helper to convert model to dict
            return {c.name: getattr(self, c.name) for c in self.__table__.columns}

except ImportError:
    SQLALCHEMY_AVAILABLE = False
    # Mock base and other SQLAlchemy components if not available
    class Base: pass # type: ignore
    class Column: pass # type: ignore
    class Integer: pass # type: ignore
    class String: pass # type: ignore
    class DateTime: pass # type: ignore
    class Text: pass # type: ignore
    class Boolean: pass # type: ignore
    class Session: pass # type: ignore
    class MessageModel(Base): # type: ignore
        user_id = ""
        created_at = datetime.now()
        def to_dict(self): return {}
    def sessionmaker(bind): return None
    def create_engine(constr): return None
    def desc(column): return column # Mock desc for sorting


logger = logging.getLogger(__name__)

def get_user_messages_sqlalchemy(
    db_session: Any, # Should be a SQLAlchemy Session object
    message_model_cls: Any, # The SQLAlchemy model class (e.g., MessageModel)
    user_id: str,
    limit: int = 10,
    order_by_creation: str = "desc" # "asc" or "desc"
) -> List[Dict[str, Any]]:
    """
    Retrieves the latest messages for a specific user from the database using SQLAlchemy.

    Args:
        db_session: The active SQLAlchemy session.
        message_model_cls: The SQLAlchemy model class for messages.
                           It must have 'user_id' and 'created_at' attributes/columns.
        user_id (str): The ID of the user whose messages are to be retrieved.
        limit (int, optional): The maximum number of messages to retrieve. Defaults to 10.
        order_by_creation (str, optional): Order of messages by creation time.
                                           "desc" for latest first, "asc" for oldest first.
                                           Defaults to "desc".

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents
                              a message object. Returns an empty list on error or if no
                              messages are found.
    """
    if not SQLALCHEMY_AVAILABLE:
        logger.error("SQLAlchemy library is not available. Cannot get user messages.")
        return []
    if not isinstance(db_session, Session):
        logger.error("db_session is not a valid SQLAlchemy Session.")
        return []
    if not hasattr(message_model_cls, "user_id") or not hasattr(message_model_cls, "created_at"):
        logger.error("message_model_cls must have 'user_id' and 'created_at' attributes.")
        return []

    try:
        query = db_session.query(message_model_cls).filter_by(user_id=user_id)

        if order_by_creation.lower() == "desc":
            query = query.order_by(desc(message_model_cls.created_at))
        elif order_by_creation.lower() == "asc":
            query = query.order_by(message_model_cls.created_at) # Default is ascending for .order_by()
        else:
            logger.warning(f"Invalid order_by_creation value: '{order_by_creation}'. Defaulting to descending.")
            query = query.order_by(desc(message_model_cls.created_at))

        messages = query.limit(limit).all()

        return [msg.to_dict() for msg in messages if hasattr(msg, 'to_dict')] # Ensure to_dict exists

    except Exception as e:
        logger.error(f"Error retrieving messages for user_id '{user_id}': {e}", exc_info=True)
        return []

# Example Usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if not SQLALCHEMY_AVAILABLE:
        print("SQLAlchemy not available. Skipping get_user_messages tests.")
    else:
        # --- Setup In-Memory SQLite Database for Testing ---
        engine_get = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine_get) # Create tables
        SessionLocalGet = sessionmaker(autocommit=False, autoflush=False, bind=engine_get)
        db_get = SessionLocalGet()

        # --- Populate with some test data ---
        user1_id = "user123_get"
        user2_id = "user456_get"

        # Messages for user1
        db_get.add(MessageModel(line_message_id="u1m1", user_id=user1_id, message_type="text", content="Hello", created_at=datetime(2023, 1, 1, 10, 0, 0)))
        db_get.add(MessageModel(line_message_id="u1m2", user_id=user1_id, message_type="image", file_path="/img/1.jpg", created_at=datetime(2023, 1, 1, 10, 5, 0)))
        db_get.add(MessageModel(line_message_id="u1m3", user_id=user1_id, message_type="text", content="How are you?", created_at=datetime(2023, 1, 1, 10, 10, 0)))

        # Messages for user2
        db_get.add(MessageModel(line_message_id="u2m1", user_id=user2_id, message_type="text", content="Test message for user2", created_at=datetime(2023, 1, 2, 11, 0, 0)))
        db_get.commit()

        print(f"\n--- Test Case 1: Get latest 2 messages for user '{user1_id}' (desc) ---")
        user1_msgs_desc = get_user_messages_sqlalchemy(db_get, MessageModel, user1_id, limit=2, order_by_creation="desc")
        print(f"Found {len(user1_msgs_desc)} messages for {user1_id} (desc):")
        for msg_dict in user1_msgs_desc:
            print(f"  ID: {msg_dict.get('line_message_id')}, Content: {msg_dict.get('content', msg_dict.get('file_path'))}, Created: {msg_dict.get('created_at')}")
        assert len(user1_msgs_desc) == 2
        if len(user1_msgs_desc) == 2:
            assert user1_msgs_desc[0]["line_message_id"] == "u1m3" # Latest
            assert user1_msgs_desc[1]["line_message_id"] == "u1m2"

        print(f"\n--- Test Case 2: Get oldest 2 messages for user '{user1_id}' (asc) ---")
        user1_msgs_asc = get_user_messages_sqlalchemy(db_get, MessageModel, user1_id, limit=2, order_by_creation="asc")
        print(f"Found {len(user1_msgs_asc)} messages for {user1_id} (asc):")
        for msg_dict in user1_msgs_asc:
            print(f"  ID: {msg_dict.get('line_message_id')}, Content: {msg_dict.get('content', msg_dict.get('file_path'))}, Created: {msg_dict.get('created_at')}")
        assert len(user1_msgs_asc) == 2
        if len(user1_msgs_asc) == 2:
            assert user1_msgs_asc[0]["line_message_id"] == "u1m1" # Oldest
            assert user1_msgs_asc[1]["line_message_id"] == "u1m2"

        print(f"\n--- Test Case 3: Get messages for user '{user2_id}' (default limit 10) ---")
        user2_msgs = get_user_messages_sqlalchemy(db_get, MessageModel, user2_id)
        print(f"Found {len(user2_msgs)} messages for {user2_id}:")
        assert len(user2_msgs) == 1
        if user2_msgs: print(f"  Content: {user2_msgs[0].get('content')}")

        print(f"\n--- Test Case 4: Get messages for a user with no messages ---")
        no_user_msgs = get_user_messages_sqlalchemy(db_get, MessageModel, "non_existent_user")
        print(f"Found {len(no_user_msgs)} messages for non_existent_user.")
        assert len(no_user_msgs) == 0

        db_get.close()
        print("\nIn-memory database tests for get_user_messages complete.")

    print("\nNote: This snippet requires a SQLAlchemy Session and a mapped Message model class with 'user_id' and 'created_at' fields.")
