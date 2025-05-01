from django.db import models
from datetime import datetime

class Room(models.Model):
    name = models.CharField(max_length=1000)

class Message(models.Model):
    value = models.CharField(max_length=1000000, blank=True)
    date = models.DateTimeField(default=datetime.now, blank=True)
    user = models.CharField(max_length=1000000)
    room = models.CharField(max_length=1000000)
    attachment = models.FileField(upload_to='attachments/', blank=True, null=True)
    is_edited = models.BooleanField(default=False)  # Add this field
    
    def save(self, *args, **kwargs):
        # If message already exists and value is changed, mark as edited
        if self.pk is not None:
            orig = Message.objects.get(pk=self.pk)
            if orig.value != self.value:
                self.is_edited = True
        super().save(*args, **kwargs)