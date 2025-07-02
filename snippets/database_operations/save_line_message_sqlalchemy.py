import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime # For default created_at

# SQLAlchemy imports - these would be part of the user's existing setup
try:
    from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.ext.declarative import declarative_base
    SQLALCHEMY_AVAILABLE = True
    Base = declarative_base()

    # Define a Message model similar to the one in the original project for context.
    # The user of this snippet would have their own SQLAlchemy model defined.
    class MessageModel(Base): # type: ignore
        __tablename__ = "messages_example" # Example table name
        id = Column(Integer, primary_key=True)
        line_message_id = Column(String(255), unique=True, nullable=False, index=True)
        user_id = Column(String(255), nullable=False, index=True)
        message_type = Column(String(50), nullable=False) # 'text', 'image', 'video', etc.
        content = Column(Text, nullable=True) # For text messages
        summary = Column(Text, nullable=True) # Auto-generated summary
        file_path = Column(String(1024), nullable=True) # For image/video/audio files
        processed = Column(Boolean, default=False, nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        def to_dict(self): # Helper to convert model to dict, similar to original
            return {c.name: getattr(self, c.name) for c in self.__table__.columns}

except ImportError:
    SQLALCHEMY_AVAILABLE = False
    # Mock base and other SQLAlchemy components if not available, so file can be parsed
    class Base: pass # type: ignore
    class Column: pass # type: ignore
    class Integer: pass # type: ignore
    class String: pass # type: ignore
    class DateTime: pass # type: ignore
    class Boolean: pass # type: ignore
    class Text: pass # type: ignore
    class Session: pass # type: ignore
    class MessageModel(Base): # type: ignore
        def to_dict(self): return {}
    def sessionmaker(bind): return None
    def create_engine(constr): return None


logger = logging.getLogger(__name__)

def _generate_simple_summary(message_type: str, content: Optional[str], file_path: Optional[str]) -> Optional[str]:
    """
    Generates a very simple summary based on message type and content/filepath.
    (Adapted from original LineService logic)
    """
    if message_type == 'text' and content:
        return f"Text: {content[:50]}{'...' if len(content) > 50 else ''}"
    elif message_type in ['image', 'video', 'audio'] and file_path:
        return f"{message_type.capitalize()} file: {os.path.basename(file_path)}"
    return None

def save_line_message_sqlalchemy(
    db_session: Any, # Should be a SQLAlchemy Session object
    message_model_cls: Any, # The SQLAlchemy model class (e.g., MessageModel)
    line_message_id: str,
    user_id: str,
    message_type: str,
    content: Optional[str] = None,
    file_path: Optional[str] = None,
    generate_summary: bool = True, # Whether to auto-generate a simple summary
    custom_summary: Optional[str] = None # Allow passing a pre-generated summary
) -> Optional[Dict[str, Any]]:
    """
    Saves a LINE message to the database using SQLAlchemy.
    Checks if a message with the same line_message_id already exists.
    Optionally generates a simple summary.

    Args:
        db_session: The active SQLAlchemy session.
        message_model_cls: The SQLAlchemy model class for messages.
        line_message_id (str): The unique message ID from LINE.
        user_id (str): The user ID from LINE.
        message_type (str): Type of the message (e.g., 'text', 'image').
        content (Optional[str]): Text content of the message.
        file_path (Optional[str]): Path to downloaded file for media messages.
        generate_summary (bool): If True, a simple summary will be generated.
        custom_summary (Optional[str]): If provided, this summary is used instead of auto-generation.

    Returns:
        Optional[Dict[str, Any]]: A dictionary representation of the saved or existing
                                  message object if successful, None on error.
    """
    if not SQLALCHEMY_AVAILABLE:
        logger.error("SQLAlchemy library is not available. Cannot save message.")
        return None
    if not isinstance(db_session, Session): # Basic check
        logger.error("db_session is not a valid SQLAlchemy Session.")
        return None

    try:
        # Check if message already exists
        existing_message = db_session.query(message_model_cls).filter_by(line_message_id=line_message_id).first()
        if existing_message:
            logger.info(f"Message with line_message_id '{line_message_id}' already exists. Returning existing.")
            return existing_message.to_dict() # Assuming model has a to_dict() method

        # Create new message instance
        new_message_data = {
            "line_message_id": line_message_id,
            "user_id": user_id,
            "message_type": message_type,
            "content": content,
            "file_path": file_path,
            "processed": False, # Default for new messages
            # created_at and updated_at are often handled by SQLAlchemy's default/onupdate
        }

        if custom_summary is not None:
            new_message_data["summary"] = custom_summary
        elif generate_summary:
            new_message_data["summary"] = _generate_simple_summary(message_type, content, file_path)

        # Ensure all fields expected by the model are present, even if None
        # This depends on the specific model definition.
        # For MessageModel example:
        # if "summary" not in new_message_data: new_message_data["summary"] = None


        message_entry = message_model_cls(**new_message_data)

        db_session.add(message_entry)
        db_session.commit()

        logger.info(f"Message with line_message_id '{line_message_id}' saved successfully.")
        return message_entry.to_dict()

    except Exception as e:
        logger.error(f"Error saving message (ID: {line_message_id}) to database: {e}", exc_info=True)
        if db_session:
            try:
                db_session.rollback()
            except Exception as rb_e:
                logger.error(f"Failed to rollback database session: {rb_e}")
        return None

# Example Usage (requires SQLAlchemy setup and a Message model)
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if not SQLALCHEMY_AVAILABLE:
        print("SQLAlchemy not available. Skipping database operation tests.")
    else:
        # --- Setup In-Memory SQLite Database for Testing ---
        engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine) # Create tables based on Base's metadata (includes MessageModel)

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db = SessionLocal() # This is our db_session for the test

        print("\n--- Test Case 1: Save a new text message ---")
        msg_id_1 = "testmsg001" + datetime.now().strftime("%f")
        saved_msg1 = save_line_message_sqlalchemy(
            db_session=db,
            message_model_cls=MessageModel, # Pass the actual model class
            line_message_id=msg_id_1,
            user_id="user123",
            message_type="text",
            content="Hello, this is a test message for the database snippet!"
        )
        if saved_msg1:
            print("Saved message 1:", saved_msg1)
            assert saved_msg1["line_message_id"] == msg_id_1
            assert "Text: Hello, this is a test message for the database sn..." in saved_msg1.get("summary", "")
        else:
            print("Failed to save message 1.")

        print("\n--- Test Case 2: Try to save the same message again (should return existing) ---")
        saved_msg2 = save_line_message_sqlalchemy(
            db, MessageModel, msg_id_1, "user123", "text", "Hello again!"
        )
        if saved_msg2:
            print("Attempt to save duplicate, result:", saved_msg2)
            assert saved_msg2["line_message_id"] == msg_id_1 # Should be the same ID
            assert saved_msg2["content"] == "Hello, this is a test message for the database snippet!" # Original content
        else:
            print("Failed on duplicate message handling (unexpected).")

        print("\n--- Test Case 3: Save an image message with file_path ---")
        msg_id_3 = "imgmsg001" + datetime.now().strftime("%f")
        saved_msg3 = save_line_message_sqlalchemy(
            db, MessageModel, msg_id_3, "user456", "image",
            file_path="/path/to/images/cool_pic.jpg",
            custom_summary="A beautiful sunset." # Provide a custom summary
        )
        if saved_msg3:
            print("Saved message 3:", saved_msg3)
            assert saved_msg3["message_type"] == "image"
            assert saved_msg3["summary"] == "A beautiful sunset." # Custom summary used
        else:
            print("Failed to save message 3.")

        print("\n--- Test Case 4: Save message without auto-summary ---")
        msg_id_4 = "nosummary001" + datetime.now().strftime("%f")
        saved_msg4 = save_line_message_sqlalchemy(
            db, MessageModel, msg_id_4, "user789", "video",
            file_path="/path/to/videos/funny.mp4",
            generate_summary=False
        )
        if saved_msg4:
            print("Saved message 4 (no auto-summary):", saved_msg4)
            assert saved_msg4.get("summary") is None
        else:
            print("Failed to save message 4.")


        # Clean up session
        db.close()
        print("\nIn-memory database tests complete.")

    print("\nNote: This snippet requires a SQLAlchemy Session and a mapped Message model class.")
    print("The example uses an in-memory SQLite database and a sample MessageModel for demonstration.")
