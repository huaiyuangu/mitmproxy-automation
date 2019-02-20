import threading
import json

from mitmproxy import cmdline
from mitmproxy import exceptions
from mitmproxy.proxy import config
from mitmproxy import dump
from mitmproxy import flow
from mitmproxy import utils
from mitmproxy.builtins import dumper
from mitmproxy.builtins.termlog import TermLog

from netlib import version_check
from netlib import debug
from netlib import tcp

from mitmproxy.builtins import anticache
from mitmproxy.builtins import anticomp
from mitmproxy.builtins import filestreamer
from mitmproxy.builtins import stickyauth
from mitmproxy.builtins import stickycookie
from mitmproxy.builtins import script
from mitmproxy.builtins import setheaders
from mitmproxy.builtins import serverplayback
from mitmproxy.builtins import clientplayback

import tornado
from mitmproxy.onboarding.app import Index, PEM, P12, Adapter

import global_config


def default_addons():
    return [
        anticache.AntiCache(),
        anticomp.AntiComp(),
        stickyauth.StickyAuth(),
        stickycookie.StickyCookie(),
        script.ScriptLoader(),
        filestreamer.FileStreamer(),
        # replace.Replace(),
        setheaders.SetHeaders(),
        serverplayback.ServerPlayback(),
        clientplayback.ClientPlayback(),
    ]


class FileTermLog (TermLog):
    def __init__(self):
        self.options = None

    def log(self, e):
        print (e.msg.replace('\n', ''))


class UsersEvents(tornado.web.RequestHandler):

    def get(self, user_id):
        user_id = user_id.rstrip('/')
        offset = int(self.get_argument('offset', 0, True))
        d = []
        if user_id in global_config.TEST_EVENTS_DATA:
            d = global_config.TEST_EVENTS_DATA[user_id]
        if len(d) > offset:
            d = d[offset:]
        else:
            d = []
        self.write(json.dumps(d))
        self.finish()


application1 = tornado.web.Application(
    [
        (r"/", Index),
        (r"/events/users/(.*)", UsersEvents),
        (r"/cert/pem", PEM),
        (r"/cert/p12", P12),
        (
            r"/static/(.*)",
            tornado.web.StaticFileHandler,
            {
                "path": utils.pkg_data.path("onboarding/static")
            }
        ),
    ],
    # debug=True
)
mapp1 = Adapter(application1)


class FileDumpMaster(dump.DumpMaster):

    def __init__(self, server, options):
        flow.FlowMaster.__init__(self, options, server, flow.DummyState())
        self.has_errored = False
        self.addons.add(FileTermLog())
        self.addons.add(*default_addons())
        self.addons.add(dumper.Dumper())
        # self.addons.add(FlowWriter())
        # This line is just for type hinting
        self.options = self.options  # type: Options
        self.set_stream_large_bodies(options.stream_large_bodies)

        if not self.options.no_server and server:
            self.add_log(
                "Proxy server listening at http://{}".format(server.address),
                "info"
            )

        if self.server and self.options.http2 and not tcp.HAS_ALPN:  # pragma: no cover
            self.add_log(
                "ALPN support missing (OpenSSL 1.0.2+ required)!\n"
                "HTTP/2 is disabled. Use --no-http2 to silence this warning.",
                "error"
            )

        if self.options.app:
            self.start_app(self.options.app_host, self.options.app_port)

    def start_app(self, host, port):
        self.apps.add(mapp1, host, port)


class MITMProxyRunThread(threading.Thread):
    """
    check all resource pool status and store in database
    """

    def __init__(self, port, name, plugin = []):
        super(MITMProxyRunThread, self).__init__(name=name)
        self.port = port
        self.name = name
        self.addon = plugin
        self.master = None

        self._stop = threading.Event()
        self.setDaemon(True)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        """
        start one proxy in background with specific port
        :param port:
        :param addon:
        :return:
        """
        args = ['-p', '%s' % self.port,
              '--stream', '100k'
              ]

        print ('proxy arguments: %s' % ' '.join(args))

        def process_options(parser, options, args):
            from mitmproxy.proxy import server
            if args.sysinfo:
                print(debug.sysinfo())
            try:
                debug.register_info_dumpers()
            except Exception as e:
                print (str(e))
            pconf = config.ProxyConfig(options)
            if options.no_server:
                return server.DummyServer(pconf)
            else:
                try:
                    return server.ProxyServer(pconf)
                except exceptions.ServerException as v:
                    print(str(v))
                    return

        version_check.check_pyopenssl_version()

        parser = cmdline.mitmdump()
        args = parser.parse_args(args)
        # if args.quiet:
        args.flow_detail = 0

        self.master = None
        try:
            dump_options = dump.Options(**cmdline.get_common_options(args))
            dump_options.flow_detail = args.flow_detail
            dump_options.keepserving = args.keepserving
            dump_options.filtstr = " ".join(args.args) if args.args else None
            server = process_options(parser, dump_options, args)
            self.master = FileDumpMaster(server, dump_options)

            for add_on in self.addon:
                self.master.addons.add(add_on)

            def cleankill(*args, **kwargs):
                self.master.shutdown()

            # signal.signal(signal.SIGTERM, cleankill)
            global_config.PROXY = self.master
            self.master.run()
        except (dump.DumpError, exceptions.OptionsError) as e:
            print("mitmdump: %s" % e)
            return
        # except (KeyboardInterrupt, _thread.error):
        #     pass
        if self.master is None or self.master.has_errored:
            print("mitmdump: errors occurred during run")
            return

