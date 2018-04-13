from importlib import import_module
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from sockjs.tornado import SockJSRouter
from tornado import web, ioloop


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option(
            '--port',
            action='store',
            dest='port',
            default=getattr(settings, 'SOCKJS_PORT', 9999),
            help='What port number to run the socket server on'),
        make_option(
            '--no-keep-alive',
            action='store_true',
            dest='no_keep_alive',
            default=False,
            help='Set no_keep_alive on the connection if your server needs it')
    )

    def handle(self, **options):
        if len(settings.SOCKJS_CLASSES) > 1:
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured(
                "Multiple connections not yet supported"
            )

        module_name, cls_name = settings.SOCKJS_CLASSES[0].rsplit('.', 1)
        module = import_module(module_name)
        cls = getattr(module, cls_name)
        channel = getattr(settings, 'SOCKJS_CHANNEL', '/echo')
        if not channel.startswith('/'):
            channel = '/%s' % channel

        router = SockJSRouter(cls, channel)
        app_settings = {
            'debug': settings.DEBUG,
        }

        extra_urls = []
        if hasattr(settings, 'SOCKJS_PUSH_CLASS') and hasattr(
                settings, 'SOCKJS_PUSH_CLASS'):
            push_module_name, push_cls_name = \
                settings.SOCKJS_PUSH_CLASS.rsplit('.', 1)
            push_module = import_module(push_module_name)
            push_cls = getattr(push_module, push_cls_name)
            extra_urls.append((settings.SOCKJS_PUSH_URL, push_cls,
                               dict(router=router)),)

        PORT = int(options['port'])
        app = web.Application(router.urls + extra_urls, **app_settings)
        app.listen(PORT, no_keep_alive=options['no_keep_alive'])
        print("Running sock app on port {0} with channel {1}".format(
            PORT, channel))
        try:
            ioloop.IOLoop.instance().start()
        except KeyboardInterrupt:
            # so you don't think you errored when ^C'ing out
            pass
