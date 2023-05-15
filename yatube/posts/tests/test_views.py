import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.paginator import Page
from django import forms
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm, CommentForm
from posts.models import Group, Post, Follow, Comment

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create_user(username='auth')

        cls.group = Group.objects.create(
            title='Название группы',
            slug='test-slug',
            description='Описание группы'
        )

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

        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
            image=uploaded,

        )

        cls.templates_pages_names = [(reverse('posts:index'),
                                      'posts/index.html'),
                                     (reverse(
                                         'posts:group_list',
                                         kwargs={'slug': cls.group.slug}),
                                      'posts/group_list.html'),
                                     (reverse(
                                         'posts:profile',
                                         kwargs={'username': cls.user}),
                                      'posts/profile.html'),
                                     (reverse(
                                         'posts:post_detail',
                                         kwargs={'post_id': cls.post.id}),
                                      'posts/post_detail.html'),
                                     (reverse(
                                         'posts:post_edit',
                                         kwargs={'post_id': cls.post.id}),
                                      'posts/create_post.html'),
                                     (reverse('posts:post_create'),
                                      'posts/create_post.html'), ]

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_posts_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""

        for reverse_name, template in self.templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def first_page_info(self, context, is_page=True):
        if is_page:
            page = context.get('page_obj')
            self.assertIsInstance(page, Page)
            post = page[0]
        else:
            post = context.get('post')

        self.assertIsInstance(post, Post)

        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author.id, self.user.id)
        self.assertEqual(post.group.title, self.group.title)
        self.assertEqual(post.pub_date, self.post.pub_date)
        self.assertEqual(post.image, self.post.image)

    def test_index_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.first_page_info(response.context)

    def test_profile_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:profile',
            kwargs={'username': self.user}))
        self.first_page_info(response.context)
        self.assertEqual(response.context.get('author'), self.user)

    def test_group_list_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(
            'posts:group_list',
            kwargs={'slug': self.group.slug}
        ))

        self.first_page_info(response.context)
        self.assertEqual(response.context.get('group'), self.group)

    def test_post_detail_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        new_comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            text='New post'
        )

        response = self.authorized_client.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.id,
                            }))
        self.assertIn(new_comment, response.context.get('comments'))
        self.assertIsInstance(response.context.get('form'), CommentForm)
        self.first_page_info(response.context, is_page=False)

    def test_post_edit_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={'post_id': self.post.id}))

        self.first_page_info(response.context, is_page=False)

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }

        form = response.context.get('form')
        self.assertIsInstance(form, PostForm)

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = form.fields.get(value)
                self.assertIsInstance(form_field,
                                      expected)

        self.assertTrue(response.context.get('is_edit'))
        self.assertEqual(response.context.get('form').instance, self.post)

    def test_post_create_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_create'))

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }

        form = response.context.get('form')
        self.assertIsInstance(form, PostForm)

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = form.fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_in_right_pages(self):
        """Пост появляется на ожидаемых страница"""

        right_pages_tuple = (
            (reverse('posts:index'), 'поста нет на главной'),
            (reverse('posts:group_list',
                     kwargs={'slug': f'{self.group.slug}'}),
             'поста нет в профиле'),
            (reverse('posts:profile',
                     kwargs={'username': f'{self.user.username}'}),
             'поста нет в группе'),
        )

        new_post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=self.group,

        )

        for rev, text in right_pages_tuple:
            name = self.authorized_client.get(rev)
            self.assertIn(
                new_post,
                name.context.get('page_obj'),
                text)

    def test_no_post_in_wrong_group(self):
        """Пост не попадает на страницу группы, к которой не принадлежит"""
        group_new = Group.objects.create(
            title='Новая группа',
            slug='other-group',
            description='Новая группа'
        )

        post = Post.objects.create(
            text='Тестовый текст',
            author=self.user,
            group=group_new,
        )

        response = self.authorized_client.get(reverse(
            'posts:group_list', kwargs={'slug': self.group.slug}))
        all_objects = response.context['page_obj']
        self.assertNotIn(post, all_objects)

    def test_cache_index(self):
        """Проверка кэша для index"""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = response.content
        Post.objects.create(
            text='test_new_post',
            author=self.user,
        )
        response_old = self.authorized_client.get(reverse('posts:index'))
        old_posts = response_old.content
        self.assertEqual(old_posts, posts)
        cache.clear()
        response_new = self.authorized_client.get(reverse('posts:index'))
        new_posts = response_new.content
        self.assertNotEqual(old_posts, new_posts)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.count_post = settings.POSTS_LIMIT
        cls.CREATE_POST = 3
        cls.user = User.objects.create_user(username='Post_writer')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

        for i in range(settings.POSTS_LIMIT + cls.CREATE_POST):
            Post.objects.create(
                author=cls.user,
                text='Тестовый пост',
                group=cls.group
            )
        cls.authorised_client = Client()
        cls.authorised_client.force_login(cls.user)
        cls.guest_client = Client()

    def test_first_page_contains_ten_records(self):
        addresses = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user}),
        ]
        for address in addresses:
            response = self.authorised_client.get(address)
            self.assertEqual(len(response.context['page_obj']),
                             settings.POSTS_LIMIT)

    def test_second_page_contains_three_records(self):
        addresses = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user}),
        ]
        for address in addresses:
            response = self.authorised_client.get(address + '?page=2')
            self.assertEqual(len(response.context['page_obj']),
                             self.CREATE_POST)


class FollowTest(TestCase):
    def setUp(self):
        cache.clear()

        self.client_auth_follower = Client()
        self.client_auth_following = Client()
        self.user_follower = User.objects.create_user(
            username='First', email='first@mail.ru', password='pass')
        self.user_following = User.objects.create_user(
            username='Second', email='second@mail.ru', password='pass')
        self.post = Post.objects.create(
            author=self.user_following,
            text='test_post'
        )
        self.client_auth_follower.force_login(self.user_follower)
        self.client_auth_following.force_login(self.user_following)

    def test_follow(self):
        Follow.objects.all().delete()
        self.client_auth_follower.get(reverse('posts:profile_follow', kwargs={
            'username': self.user_following.username}))
        follow_exists = Follow.objects.filter(
            user=self.user_follower,
            author=self.user_following
        ).exists()
        self.assertTrue(follow_exists)

    def test_unfollow(self):
        user_following = User.objects.create_user(username='test_user_1', password='pass123')
        user_follower = User.objects.create_user(username='test_user_2', password='pass123')
        client_auth_follower = Client()
        client_auth_follower.login(username='tes_tuser_2', password='pass123')
        follow_not_exists = Follow.objects.filter(
            user=user_follower,
            author=user_following
        ).exists()
        self.assertFalse(follow_not_exists)

    def test_subscription_feed(self):
        Follow.objects.create(
            user=self.user_follower, author=self.user_following)
        response = self.client_auth_follower.get(
            reverse('posts:follow_index'))
        posts = response.context['page_obj']
        self.assertIn(self.post, posts)

    def test_unfollow_on_authors(self):
        response = self.client_auth_follower.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(self.post, response.context['page_obj'].object_list)
