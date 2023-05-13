from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['text', 'group', 'image']
        help_text = {
            'text': 'Текст поста',
            'group': 'Группа',
            'image': 'Изображение',
        }
        labels = {
            'group': 'Группа',
            'text': 'Текст',
            'image': 'Изображение',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['text']
        help_text = {
            'text': 'Комментарий',
        }
        labels = {
            'text': 'Комментарий',
        }
