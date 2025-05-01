from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('checkview', views.checkview, name='checkview'),
    path('send', views.send, name='send'),
    path('getMessages/<str:room>/', views.getMessages, name='getMessages'),
    path('get_rooms/', views.get_rooms, name='get_rooms'),  # Add this line
    path('<str:room>/', views.room, name='room'),
    path('download/<path:file_path>/', views.download_attachment, name='download_attachment'),
    path('delete_message/', views.delete_message, name='delete_message'),
    path('edit_message/', views.edit_message, name='edit_message'),
    path('forward_message/', views.forward_message, name='forward_message'),
    # Add this to your urlpatterns list
    path('download-history/<str:room_name>/', views.download_chat_history, name='download_chat_history'),
]

# Add these URL patterns to your existing patterns
urlpatterns += [
    path('gemini/summary/<str:room_name>/', views.get_room_summary, name='get_room_summary'),
    path('gemini/ask/', views.ask_gemini_question, name='ask_gemini'),
]