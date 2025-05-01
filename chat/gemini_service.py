import os
import google.generativeai as genai
from dotenv import load_dotenv
from django.conf import settings
from .models import Message, Room

# Load environment variables
load_dotenv()

# Use the key from settings
api_key = getattr(settings, 'GOOGLE_API_KEY', os.getenv('GOOGLE_API_KEY'))
genai.configure(api_key=api_key)

# Set up the model
model = genai.GenerativeModel('gemini-1.5-pro')

def get_chat_history(room_name, limit=100):
    """Get chat history for a specific room"""
    try:
        room = Room.objects.get(name=room_name)
        messages = Message.objects.filter(room=room.id).order_by('-date')[:limit]
        
        # Format messages for summary
        formatted_messages = []
        for msg in reversed(messages):
            formatted_messages.append(f"{msg.user}: {msg.value}")
        
        return "\n".join(formatted_messages)
    except Room.DoesNotExist:
        return "Room not found"
    except Exception as e:
        return f"Error retrieving chat history: {str(e)}"

def generate_summary(room_name):
    """Generate a summary of the chat using Gemini API"""
    history = get_chat_history(room_name)
    
    if not history or history == "Room not found":
        return "No chat history available to summarize."
    
    prompt = f"""
    Please provide a concise summary of this chat conversation. 
    Identify the main topics discussed, key points made by participants, and any decisions or action items mentioned.
    
    CHAT HISTORY:
    {history}
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error generating summary: {str(e)}"

def ask_gemini(user_query, room_name=None):
    """Process a user query with context about the chat/app"""
    
    system_context = """
    You are an AI assistant integrated into a Django-based chat application called Django Chat.
    This app allows users to create chat rooms, send messages, share files, and communicate in real-time.
    Users can also edit and delete their messages, forward messages to other rooms, and download chat history.
    """
    
    # If room is specified, add chat history context
    room_context = ""
    if room_name:
        history = get_chat_history(room_name, limit=30)  # Limit to last 30 messages for context
        if history and history != "Room not found":
            room_context = f"\nCURRENT CHAT ROOM: {room_name}\n\nRECENT CHAT HISTORY:\n{history}"
    
    full_prompt = f"{system_context}{room_context}\n\nUSER QUERY: {user_query}"
    
    try:
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Error processing your query: {str(e)}"