from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from apps.academics.models import ClassSession
from apps.accounts.models import Role, get_role

from .live import session_group

# Close codes in the application range, so the browser can tell "not signed in" from "not allowed".
NOT_SIGNED_IN = 4401
FORBIDDEN = 4403


class LiveConsumer(JsonWebsocketConsumer):
    """Base consumer: staff only, forwards worker updates to the browser unchanged."""
    group: str | None = None

    def authorize(self, user, role) -> bool:
        return True

    def connect(self):
        user = self.scope.get('user')
        if user is None or not user.is_authenticated:
            self.close(code=NOT_SIGNED_IN)
            return
        role = get_role(user)
        if role == Role.VIEWER or not self.authorize(user, role):
            self.close(code=FORBIDDEN)
            return
        async_to_sync(self.channel_layer.group_add)(self.group, self.channel_name)
        self.accept()

    def disconnect(self, code):
        if self.group:
            async_to_sync(self.channel_layer.group_discard)(self.group, self.channel_name)

    def live_update(self, event):
        self.send_json(event['payload'])


class SessionConsumer(LiveConsumer):
    """Live faces and attendance changes for one session. Teachers may watch only their own."""

    def authorize(self, user, role) -> bool:
        session_id = self.scope['url_route']['kwargs']['session_id']
        session = ClassSession.objects.select_related('teacher').filter(pk=session_id).first()
        if session is None:
            return False
        if role == Role.TEACHER and not (session.teacher and session.teacher.user_id == user.id):
            return False
        self.group = session_group(session_id)
        return True
