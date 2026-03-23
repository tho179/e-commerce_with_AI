from datetime import datetime, timedelta, timezone
import os

from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, User
import jwt
from rest_framework.response import Response
from rest_framework.views import APIView

from .rate_limit import is_rate_limited

ROLE_ADMIN = 'Admin'
ROLE_STAFF = 'Staff'
ROLE_CUSTOMER = 'Customer'
JWT_SECRET = os.getenv('JWT_SECRET', 'bookstore-jwt-secret')
JWT_ALGORITHM = 'HS256'
ACCESS_TOKEN_MINUTES = int(os.getenv('ACCESS_TOKEN_MINUTES', '30'))
REFRESH_TOKEN_DAYS = int(os.getenv('REFRESH_TOKEN_DAYS', '7'))
AUTH_ADMIN_TOKEN = os.getenv('AUTH_ADMIN_TOKEN', '')


def _ensure_role_groups():
    for role in [ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER]:
        Group.objects.get_or_create(name=role)


def _get_user_role(user):
    if user.is_superuser or user.groups.filter(name=ROLE_ADMIN).exists():
        return ROLE_ADMIN
    if user.groups.filter(name=ROLE_STAFF).exists():
        return ROLE_STAFF
    if user.groups.filter(name=ROLE_CUSTOMER).exists():
        return ROLE_CUSTOMER
    return ROLE_CUSTOMER


def _serialize_user(user):
    return {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.first_name,
        'role': _get_user_role(user),
    }


def _issue_token(user, token_type):
    now = datetime.now(timezone.utc)
    expires_at = now + (timedelta(minutes=ACCESS_TOKEN_MINUTES) if token_type == 'access' else timedelta(days=REFRESH_TOKEN_DAYS))
    payload = {
        'sub': user.username,
        'email': user.email,
        'role': _get_user_role(user),
        'type': token_type,
        'iat': int(now.timestamp()),
        'exp': int(expires_at.timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _issue_auth_payload(user):
    return {
        'user': _serialize_user(user),
        'access_token': _issue_token(user, 'access'),
        'refresh_token': _issue_token(user, 'refresh'),
    }


class HealthCheck(APIView):
    def get(self, request):
        return Response({'service': 'auth-service', 'status': 'ok'})


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        client_key = request.META.get('REMOTE_ADDR', 'unknown')
        if is_rate_limited(f'register:{client_key}', limit=15, window_seconds=300):
            return Response({'error': 'Too many registration attempts. Please try again later.'}, status=429)

        _ensure_role_groups()
        username = (request.data.get('username') or '').strip()
        email = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password') or ''
        full_name = (request.data.get('full_name') or '').strip()
        role = (request.data.get('role') or ROLE_CUSTOMER).strip()

        if not username or not email or not password:
            return Response({'error': 'Missing required fields.'}, status=400)
        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username already exists.'}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email already exists.'}, status=400)

        role_name = role if role in [ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER] else ROLE_CUSTOMER
        user = User.objects.create_user(username=username, email=email, password=password, first_name=full_name)
        user.groups.add(Group.objects.get(name=role_name))

        return Response(_issue_auth_payload(user), status=201)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        client_key = request.META.get('REMOTE_ADDR', 'unknown')
        if is_rate_limited(f'login:{client_key}', limit=30, window_seconds=300):
            return Response({'error': 'Too many login attempts. Please try again later.'}, status=429)

        _ensure_role_groups()
        username = (request.data.get('username') or '').strip()
        password = request.data.get('password') or ''
        user = authenticate(request, username=username, password=password)
        if not user:
            return Response({'error': 'Invalid credentials.'}, status=401)

        return Response(_issue_auth_payload(user))


class RefreshView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({'error': 'refresh_token is required.'}, status=400)

        try:
            payload = jwt.decode(refresh_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.PyJWTError:
            return Response({'error': 'Invalid refresh token.'}, status=401)

        if payload.get('type') != 'refresh':
            return Response({'error': 'Token is not a refresh token.'}, status=401)

        user = User.objects.filter(username=payload.get('sub')).first()
        if not user:
            return Response({'error': 'User not found.'}, status=404)

        return Response(_issue_auth_payload(user))


class VerifyView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'token is required.'}, status=400)

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.PyJWTError:
            return Response({'valid': False}, status=401)

        return Response({'valid': True, 'payload': payload})


class UpdateRoleView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        _ensure_role_groups()
        if not AUTH_ADMIN_TOKEN or request.headers.get('X-Admin-Token') != AUTH_ADMIN_TOKEN:
            return Response({'error': 'Unauthorized admin update.'}, status=401)

        username = (request.data.get('username') or '').strip()
        role = (request.data.get('role') or '').strip()
        if role not in [ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER]:
            return Response({'error': 'Invalid role.'}, status=400)

        user = User.objects.filter(username=username).first()
        if not user:
            return Response({'error': 'User not found.'}, status=404)

        groups = Group.objects.filter(name__in=[ROLE_ADMIN, ROLE_STAFF, ROLE_CUSTOMER])
        user.groups.remove(*groups)
        user.groups.add(Group.objects.get(name=role))

        return Response({'ok': True, 'user': _serialize_user(user)})
