

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=64, verbose_name='Название')),
                ('slug', models.SlugField(unique=True)),
            ],
            options={
                'verbose_name': 'Категория',
                'verbose_name_plural': 'Категории',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CustomPizza',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('crust', models.CharField(choices=[('thin', 'Тонкое'), ('thick', 'Толстое')], default='thin', max_length=16, verbose_name='Тесто')),
                ('size', models.CharField(choices=[('small', 'Маленькая'), ('medium', 'Средняя'), ('large', 'Большая')], default='medium', max_length=16, verbose_name='Размер')),
                ('price_cached', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Итоговая цена на момент добавления')),
            ],
            options={
                'verbose_name': 'Собранная пицца',
                'verbose_name_plural': 'Собранные пиццы',
            },
        ),
        migrations.CreateModel(
            name='Ingredient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, verbose_name='Название')),
                ('slug', models.SlugField(unique=True)),
                ('price_extra', models.DecimalField(decimal_places=2, default=Decimal('1.50'), max_digits=8, verbose_name='Доплата в конструкторе (BYN)')),
                ('image', models.ImageField(blank=True, upload_to='ingredients/', verbose_name='Картинка для куска')),
            ],
            options={
                'verbose_name': 'Ингредиент',
                'verbose_name_plural': 'Ингредиенты',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Promotion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=128, verbose_name='Заголовок')),
                ('text', models.TextField(verbose_name='Текст акции')),
                ('discount_percent', models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MaxValueValidator(100)], verbose_name='Скидка, %')),
                ('image', models.ImageField(blank=True, upload_to='promotions/', verbose_name='Баннер')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активна')),
                ('starts_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='С')),
                ('ends_at', models.DateTimeField(blank=True, null=True, verbose_name='По')),
            ],
            options={
                'verbose_name': 'Акция',
                'verbose_name_plural': 'Акции и скидки',
                'ordering': ['-starts_at'],
            },
        ),
        migrations.CreateModel(
            name='Cart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(blank=True, db_index=True, max_length=40)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='carts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Корзина',
                'verbose_name_plural': 'Корзины',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('accepted', 'Принят'), ('cooking', 'Готовится'), ('delivering', 'В доставке'), ('delivered', 'Доставлен'), ('cancelled', 'Отменён')], default='accepted', max_length=20, verbose_name='Статус заказа')),
                ('delivery_type', models.CharField(choices=[('courier', 'Курьер'), ('pickup', 'Самовывоз')], max_length=16, verbose_name='Доставка')),
                ('payment_type', models.CharField(choices=[('online', 'Онлайн'), ('cash', 'Наличными'), ('card', 'Картой при получении')], max_length=16, verbose_name='Оплата')),
                ('customer_name', models.CharField(max_length=120, verbose_name='Имя')),
                ('phone', models.CharField(max_length=20, verbose_name='Телефон')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='Email')),
                ('address', models.CharField(blank=True, max_length=255, verbose_name='Адрес')),
                ('comment', models.TextField(blank=True, verbose_name='Комментарий')),
                ('total', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Сумма (BYN)')),
                ('estimated_delivery_at', models.DateTimeField(blank=True, null=True, verbose_name='Ориентировочное время доставки')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='orders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Заказ',
                'verbose_name_plural': 'Заказы',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128, verbose_name='Название')),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField(blank=True, verbose_name='Описание / состав')),
                ('composition', models.TextField(blank=True, verbose_name='Состав (текст для карточки)')),
                ('price', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Цена (BYN)')),
                ('spiciness', models.PositiveSmallIntegerField(choices=[(0, 'Без остроты'), (1, 'Слабо'), (2, 'Средне'), (3, 'Остро')], default=0, verbose_name='Острота')),
                ('image', models.ImageField(blank=True, upload_to='products/', verbose_name='Изображение')),
                ('popularity', models.PositiveIntegerField(default=0, verbose_name='Популярность (для сортировки)')),
                ('in_stock', models.BooleanField(default=True, verbose_name='В наличии')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='products', to='shop.category', verbose_name='Категория')),
                ('ingredients', models.ManyToManyField(blank=True, related_name='menu_products', to='shop.ingredient', verbose_name='Ингредиенты для фильтра')),
            ],
            options={
                'verbose_name': 'Товар',
                'verbose_name_plural': 'Товары',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='Название позиции')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('line_total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('custom_pizza', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='order_item', to='shop.custompizza')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='shop.order')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='shop.product')),
            ],
            options={
                'verbose_name': 'Позиция заказа',
                'verbose_name_plural': 'Позиции заказов',
            },
        ),
        migrations.CreateModel(
            name='CartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(default=1)),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('line_total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('cart', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='shop.cart')),
                ('custom_pizza', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cart_item', to='shop.custompizza')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='cart_items', to='shop.product')),
            ],
            options={
                'verbose_name': 'Позиция корзины',
                'verbose_name_plural': 'Позиции корзины',
            },
        ),
        migrations.CreateModel(
            name='SavedAddress',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(default='Дом', max_length=64, verbose_name='Название')),
                ('address', models.CharField(max_length=255, verbose_name='Адрес')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='saved_addresses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Сохранённый адрес',
                'verbose_name_plural': 'Сохранённые адреса',
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, max_length=20, verbose_name='Телефон')),
                ('is_blocked', models.BooleanField(default=False, verbose_name='Заблокирован')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Профиль',
                'verbose_name_plural': 'Профили',
            },
        ),
        migrations.CreateModel(
            name='CustomPizzaTopping',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quarter', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(4)], verbose_name='Четверть (1–4)')),
                ('pizza', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='toppings', to='shop.custompizza')),
                ('ingredient', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='shop.ingredient')),
            ],
            options={
                'verbose_name': 'Топпинг на четверти',
                'verbose_name_plural': 'Топпинги',
                'constraints': [models.UniqueConstraint(fields=('pizza', 'quarter', 'ingredient'), name='uniq_quarter_ingredient')],
            },
        ),
    ]
