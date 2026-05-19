from django.urls import path

from .views import InvitationCreateView


urlpatterns = [
    path("invitations/", InvitationCreateView.as_view()),
]
