from django.db import models
from django.utils.text import slugify

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Book(models.Model):
    BOOK_TYPE_CHOICES = [
        ('educational', 'Educational'),
        ('novel', 'Novel'),
    ]

    STOCK_CHOICES = [
        ('In Stock', 'In Stock'),
        ('Limited Stock', 'Limited Stock'),
        ('Out of Stock', 'Out of Stock'),
    ]

    title = models.CharField(max_length=255)
    authors = models.CharField(max_length=255, blank=True)
    published_date = models.CharField(max_length=20, blank=True, null=True)
    publisher = models.CharField(max_length=255, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    description = models.TextField(blank=True)
    thumbnail = models.URLField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    book_type = models.CharField(max_length=50, choices=BOOK_TYPE_CHOICES, blank=True)
    topic_tag = models.CharField(max_length=100, blank=True)
    slug = models.SlugField(max_length=100, blank=True, unique=True)
    raw_categories = models.TextField(blank=True)  # new
    stock_status = models.CharField(
        max_length=20,
        choices=STOCK_CHOICES,
        default='In Stock',
        blank=True
    )


    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(f"{self.title}-{self.topic_tag}" if self.topic_tag else self.title)[:90]
            slug = base
            i = 2
            # Ensure uniqueness and maximum length
            while Book.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                slug = f"{base[:100 - len(str(i)) - 1]}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)


    def __str__(self):
        return self.title
