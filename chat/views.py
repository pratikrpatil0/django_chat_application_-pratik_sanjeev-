from django.shortcuts import render, redirect, get_object_or_404
from chat.models import Room, Message
from django.http import HttpResponse, JsonResponse, Http404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
import os
from django.conf import settings
from django.http import FileResponse
from django.http import HttpResponse
import csv
from io import StringIO
from datetime import datetime
# Add these imports at the top of your views.py
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from .gemini_service import generate_summary, ask_gemini

# Authentication views
def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'login.html', {'error_message': 'Invalid username or password'})
    
    return render(request, 'login.html')

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        if password1 != password2:
            return render(request, 'register.html', {'error_message': 'Passwords do not match'})
        
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error_message': 'Username already exists'})
        
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error_message': 'Email already exists'})
        
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()
        
        login(request, user)
        return redirect('home')
    
    return render(request, 'register.html')

def logout_view(request):
    logout(request)
    return redirect('home')

# Chat views
def home(request):
    # Get all active rooms
    rooms = Room.objects.all().order_by('name')
    return render(request, 'home.html', {'rooms': rooms})

@login_required(login_url='/login/')
def room(request, room):
    try:
        # If room doesn't exist, raise 404
        room_details = get_object_or_404(Room, name=room)
        
        # Always use the logged-in user's username
        username = request.user.username
        
        return render(request, 'room.html', {
            'username': username,
            'room': room,
            'room_details': room_details
        })
    except Http404:
        messages.error(request, f"Room '{room}' does not exist.")
        return redirect('home')

@login_required(login_url='/login/')
def checkview(request):
    room = request.POST['room_name']
    username = request.user.username  # Always use authenticated username

    if Room.objects.filter(name=room).exists():
        return redirect('/'+room+'/')
    else:
        new_room = Room.objects.create(name=room)
        new_room.save()
        return redirect('/'+room+'/')

@login_required(login_url='/login/')
def send(request):
    if request.method == 'POST':
        message = request.POST.get('message', '')
        username = request.user.username
        room_id = request.POST['room_id']
        attachment = request.FILES.get('attachment', None)

        new_message = Message.objects.create(
            value=message,
            user=username,
            room=room_id,
            attachment=attachment
        )
        new_message.save()
        return HttpResponse('Message sent successfully')
    return HttpResponse('Invalid request', status=400)

def getMessages(request, room):
    try:
        room_details = get_object_or_404(Room, name=room)
        messages = Message.objects.filter(room=room_details.id).order_by('date')
        message_list = []
        for msg in messages:
            message_list.append({
                'id': msg.id,
                'value': msg.value,
                'date': msg.date.strftime('%Y-%m-%d %H:%M'),
                'user': msg.user,
                'attachment': msg.attachment.url if msg.attachment else ''
            })
        return JsonResponse({"messages": message_list})
    except Http404:
        return JsonResponse({"error": "Room not found"}, status=404)

@login_required(login_url='/login/')
def get_rooms(request):
    rooms = Room.objects.all()
    room_list = []
    
    for room in rooms:
        room_list.append({
            'id': room.id,
            'name': room.name
        })
    
    # Print debug info to console
    print(f"Returning {len(room_list)} rooms")
    for room in room_list:
        print(f"Room: {room['name']} (ID: {room['id']})")
    
    return JsonResponse({'rooms': room_list})

@login_required(login_url='/login/')
def download_attachment(request, file_path):
    # Security check
    if '..' in file_path:
        raise Http404("File not found")
    
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)
    
    if os.path.exists(full_path):
        file_name = os.path.basename(full_path)
        response = FileResponse(open(full_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
    else:
        raise Http404("File not found")

@login_required(login_url='/login/')
def delete_message(request):
    if request.method == 'POST':
        message_id = request.POST.get('message_id')
        try:
            message = Message.objects.get(id=message_id)
            # Security check - only allow users to delete their own messages
            if message.user == request.user.username:
                message.delete()
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'You can only delete your own messages'}, status=403)
        except Message.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Message not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required(login_url='/login/')
def edit_message(request):
    if request.method == 'POST':
        message_id = request.POST.get('message_id')
        new_text = request.POST.get('new_text')
        
        if not new_text or new_text.strip() == '':
            return JsonResponse({'status': 'error', 'message': 'Message cannot be empty'}, status=400)
            
        try:
            message = Message.objects.get(id=message_id)
            # Security check - only allow users to edit their own messages
            if message.user == request.user.username:
                message.value = new_text
                message.save()
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'You can only edit your own messages'}, status=403)
        except Message.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Message not found'}, status=404)
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required(login_url='/login/')
def forward_message(request):
    if request.method == 'POST':
        message_id = request.POST.get('message_id')
        target_room_id = request.POST.get('target_room')
        
        # Add debug print statements
        print(f"Forwarding message {message_id} to room {target_room_id}")
        
        try:
            # Get the original message
            original_message = Message.objects.get(id=message_id)
            
            # Get the target room object
            target_room = Room.objects.get(id=target_room_id)
            
            # Create the forwarded message - use the room ID as string
            new_message = Message.objects.create(
                value=original_message.value,
                user=request.user.username,
                room=str(target_room.id),  # Convert to string to match your data model
                attachment=original_message.attachment if original_message.attachment else None
            )
            
            print(f"Successfully created forwarded message with ID {new_message.id}")
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Message forwarded successfully',
                'room_name': target_room.name,
                'new_message_id': new_message.id
            })
            
        except Message.DoesNotExist:
            print("Original message not found")
            return JsonResponse({'status': 'error', 'message': 'Original message not found'}, status=404)
        except Room.DoesNotExist:
            print(f"Target room {target_room_id} not found")
            return JsonResponse({'status': 'error', 'message': 'Target room not found'}, status=404)
        except Exception as e:
            print(f"Error forwarding message: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required(login_url='/login/')
def download_chat_history(request, room_name):
    try:
        room = Room.objects.get(name=room_name)
        messages = Message.objects.filter(room=room.id).order_by('date')
        format_type = request.GET.get('format', 'csv')
        
        if format_type == 'txt':
            # Generate plain text format
            content = f"Chat History for {room_name}\n"
            content += f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            for message in messages:
                content += f"[{message.date.strftime('%Y-%m-%d %H:%M:%S')}] {message.user}: {message.value}\n"
                if message.attachment:
                    content += f"    Attachment: {request.build_absolute_uri(message.attachment.url)}\n"
            
            response = HttpResponse(content, content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{room_name}_chat_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt"'
            
        else:
            # Default to CSV format
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(['Date', 'User', 'Message', 'Attachment'])
            
            for message in messages:
                attachment_url = request.build_absolute_uri(message.attachment.url) if message.attachment else ''
                writer.writerow([
                    message.date.strftime('%Y-%m-%d %H:%M:%S'),
                    message.user,
                    message.value,
                    attachment_url
                ])
            
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{room_name}_chat_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        return response
        
    except Room.DoesNotExist:
        return HttpResponse("Room not found", status=404)

@login_required(login_url='/login/')
def get_room_summary(request, room_name):
    """Get an AI-generated summary of the room's chat history"""
    try:
        summary = generate_summary(room_name)
        return JsonResponse({"summary": summary})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@require_POST
@login_required(login_url='/login/')
def ask_gemini_question(request):
    """Ask a question to the Gemini AI"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '')
        room_name = data.get('room_name', None)
        
        if not query:
            return JsonResponse({"error": "Query is required"}, status=400)
        
        response = ask_gemini(query, room_name)
        return JsonResponse({"response": response})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)