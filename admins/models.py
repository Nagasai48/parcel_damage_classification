from django.db import models

# Create your models here.
class AdminModel(models.Model):
    ROLE_CHOICES = [
        ('Super Admin', 'Super Admin'),
        ('Staff', 'Staff'),
    ]
    
    username = models.CharField(unique=True, max_length=100)
    email = models.EmailField(unique=True, max_length=100)
    password = models.CharField(max_length=100)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='Staff')
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
