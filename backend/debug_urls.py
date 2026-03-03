import django
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'collection.settings'
django.setup()

from django.urls import get_resolver

def show_urls(resolver, prefix=''):
    for pattern in resolver.url_patterns:
        p = str(pattern.pattern)
        if hasattr(pattern, 'url_patterns'):
            show_urls(pattern, prefix + p)
        else:
            print(prefix + p)

show_urls(get_resolver())
