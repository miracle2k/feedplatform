from django.db import models


class Feed(models.Model):

    class Meta:
        db_table = 'feed'

    language = models.CharField(max_length=255, blank=True)
    updated = models.DateTimeField(max_length=255, null=True, blank=True)
    url = models.CharField(max_length=255)
    title = models.CharField(max_length=255, null=True, blank=True)
    summary = models.TextField(null=True, blank=True)


class Item(models.Model):

    class Meta:
        db_table = 'item'

    feed = models.ForeignKey(Feed)
    guid = models.CharField(max_length=255)