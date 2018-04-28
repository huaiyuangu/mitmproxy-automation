from mitmproxy import cmdline
from mitmproxy import exceptions
from mitmproxy.proxy import config
from mitmproxy import dump
from netlib import version_check
from netlib import debug
from proxyserver import FileDumpMaster


if __name__ == '__main__':
    args = ['-p', '%s' % 8080,
            '--stream', '100k',
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

    master = None
    try:
        dump_options = dump.Options(**cmdline.get_common_options(args))
        dump_options.flow_detail = args.flow_detail
        dump_options.keepserving = args.keepserving
        dump_options.filtstr = " ".join(args.args) if args.args else None
        server = process_options(parser, dump_options, args)
        master = FileDumpMaster(server, dump_options)

        # beacon test
        from proxy_req_RequestRecorder import RequestContentRecorder
        master.addons.add(RequestContentRecorder())

        def cleankill(*args, **kwargs):
            master.shutdown()

        # signal.signal(signal.SIGTERM, cleankill)
        master.run()
    except (dump.DumpError, exceptions.OptionsError) as e:
        print("mitmdump: %s" % e)

    if master is None or master.has_errored:
        print("mitmdump: errors occurred during run")