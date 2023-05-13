import shutil
import tempfile
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.models import Group, Post, Comment

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='auth')

        cls.group = Group.objects.create(
            title='Название группы',
            slug='test-slug',
            description='Описание группы'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        Post.objects.all().delete()
        post_count = Post.objects.count()
        name = 'small.gif'

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name=name,
            content=small_gif,
            content_type='image/gif'
        )
        templates_form_names = {
            'text': 'Самый новый пост',
            'group': self.group.id,
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=templates_form_names,
            follow=True)

        self.assertEqual(Post.objects.count(), post_count + 1)
        first_post = Post.objects.first()
        self.assertEqual(first_post.text, templates_form_names['text'])
        self.assertEqual(first_post.group.id, templates_form_names['group'])
        self.assertEqual(first_post.image, f"posts/{name}")

    def test_edit_post(self):
        post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group,
        )

        group_new = Group.objects.create(
            title='Название новой группы',
            slug='test-slug-new',
            description='Описание новой группы'
        )

        templates_form_names = {'text': 'New post text',
                                'group': group_new.id}

        response = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': post.id}),
            data=templates_form_names,
            follow=True)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        post = Post.objects.get(id=post.id)
        self.assertEqual(post.text, templates_form_names['text'])
        self.assertEqual(post.group.id, templates_form_names['group'])

    def test_not_auth(self):
        post_count = Post.objects.count()

        templates_form_names = {'text': 'Самый новый пост',
                                'group': self.group.id,
                                }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=templates_form_names,
            follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), post_count)

    def test_not_auth_comment(self):
        comment_count = Comment.objects.count()
        post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group,
        )

        templates_form_names = {'text': 'Тестовый комментарий'}

        response = self.guest_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': post.id}),
            data=templates_form_names,
            follow=True)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.count(), comment_count)

    def test_create_comment(self):
        post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group,
        )

        templates_form_names = {'text': 'Тестовый комментарий'}

        response = self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': post.id}),
            data=templates_form_names,
            follow=True)

        comment_count = Comment.objects.count()

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Comment.objects.count(), comment_count)
