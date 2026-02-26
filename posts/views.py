from django.shortcuts import render

# Create your views here.

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib.auth import get_user_model
from .models import Post, Comment
from .serializers import UserSerializer, PostSerializer, CommentSerializer
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({"message": "User created"}, status=status.HTTP_201_CREATED)

class PostListCreateView(generics.ListCreateAPIView):
    queryset = Post.objects.all().order_by('-created_at')
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [permissions.IsAuthenticated]

class LikePostView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        post = Post.objects.get(pk=pk)
        if request.user in post.likes.all():
            post.likes.remove(request.user)
            return Response({"message": "Unliked"})
        else:
            post.likes.add(request.user)
            # Notification trigger
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                "notifications",
                {"type": "send_notification", "message": f"{request.user.username} liked your post!"}
            )
            return Response({"message": "Liked"})

class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.filter(post_id=self.kwargs['pk'])

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, post_id=self.kwargs['pk'])