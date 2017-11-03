from tgt_grease.core.Types import Command
import platform
import sys
import os
import subprocess
import datetime
if platform.system().lower().startswith("win"):
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager
    import socket


    class AppServerSvc (win32serviceutil.ServiceFramework):
        """Windows Service Configuration"""
        _svc_name_ = "GreaseDaemon"
        _svc_display_name_ = "GREASE Daemon Server"
        _svc_description_ = "GREASE Async Daemon Server for Automation Work"

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            socket.setdefaulttimeout(60)

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            self.main()

        def main(self):
            if 'install' not in sys.argv:
                inst = Daemon()
                inst.run()
            else:
                return

        def start(self):
            self.SvcDoRun()

        def stop(self):
            self.SvcStop()

        def restart(self):
            self.SvcStop()
            self.SvcDoRun()


MacOSPListFile = """
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>net.grease.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>{0}</string>
        <string>{1}/grease</string>
        <string>daemon</string>
        <string>run</string>
    </array>
    <key>RunAtLoad</key>
    <true />
</dict>
</plist>
""".format(sys.executable, os.sep.join(sys.executable.split(os.sep)[:-1]))

SystemdFile = """
[Unit]
Description=GREASE Daemon Service
After=syslog.target

[Service]
Type=simple
WorkingDirectory=/opt/grease
PIDFile=/var/run/grease.pid
ExecStart={0} {1}/grease daemon run
StandardOutput=syslog
StandardError=syslog

[Install]
WantedBy=multi-user.target
""".format(sys.executable, os.sep.join(sys.executable.split(os.sep)[:-1]))


class Daemon(Command):
    """Daemon Class for the daemon"""

    __author__ = "James E. Bell Jr."
    __version__ = "2.0.0"
    purpose = "Control Daemon Processing in GREASE"
    help = """
    Provide simple abstraction for daemon operations in GREASE
    
    Args:
        install
            install the daemon on the system 
        start
            start the daemon
        stop
            stop the daemon
        run
            run the daemon in the foreground    
            
        --timing:<int>
            Seconds to run daemon for
        --foreground
            If provided this will print log messages into the foreground
    
    """

    def __init__(self):
        super(Daemon, self).__init__()

    def execute(self, context):
        if context.get('foreground'):
            self.ioc.getLogger().foreground = True
        if 'install' in context.get('grease_other_args'):
            return bool(self.install())
        elif 'start' in context.get('grease_other_args'):
            return bool(self.start())
        elif 'stop' in context.get('grease_other_args'):
            return bool(self.stop())
        elif 'run' in context.get('grease_other_args'):
            try:
                self.run(context.get('timing'))
                return True
            except KeyboardInterrupt:
                return True
        else:
            print("Invalid Sub-command here is help data:")
            print(self.help)
            return False

    def install(self):
        """Handle Daemon Installation based on the platform we're working with

        Returns:
            bool: installation success

        """
        global MacOSPListFile, SystemdFile
        plat = platform.system().lower()
        if plat.startswith("win"):
            # Windows
            win32serviceutil.HandleCommandLine(AppServerSvc)
            return True
        elif plat.startswith("dar"):
            # MacOS
            try:
                fil = open("/Library/LaunchDaemons/net.grease.daemon.plist", 'w')
                fil.write(MacOSPListFile)
                fil.close()
                return True
            except IOError:
                self.ioc.getLogger().error("Failed to install Daemon, Permission Denied")
                print("Failed! Permission denied creating Plist entry!")
                print("=============")
                print("To Solve this put the file below in /Library/LaunchDaemons/ as net.grease.daemon.plist")
                print("<=============================>")
                print(MacOSPListFile)
                print("<=============================>")
                print("Make sure you have the right permissions set on the file!!")
                return False
        elif plat.startswith("lin"):
            # Linux
            try:
                fil = open("/etc/systemd/system/grease.service", 'w')
                fil.write(SystemdFile)
                fil.close()
                print("Please ensure you run `systemctl daemon-reload` to effect change!")
                return True
            except IOError:
                self.ioc.getLogger().error("Failed to install Daemon, Permission Denied")
                print("Failed! Permission denied creating Systemd entry!")
                print("=============")
                print("To Solve this put the file below in /etc/systemd/system/ as grease.service")
                print("<=============================>")
                print(SystemdFile)
                print("<=============================>")
                print("Make sure you have the right permissions set on the file!!")
                print("Please ensure you run `systemctl daemon-reload` to effect change!")
                return False
        else:
            self.ioc.getLogger().error("Unrecognized operating system [{0}]".format(platform))
            print("Unrecognized operating system [{0}]".format(platform))
            return False

    def start(self):
        """Starting the daemon based on platform

        Returns:
            bool: start success

        """
        plat = platform.system().lower()
        if plat.startswith("win"):
            # Windows
            win32serviceutil.HandleCommandLine(AppServerSvc, argv=['', 'start'])
            return True
        elif plat.startswith("dar"):
            # MacOS
            if subprocess.call(["sudo", "launchctl", "load", "/Library/LaunchDaemons/net.grease.daemon.plist"]) != 0:
                return False
            return True
        elif plat.startswith("lin"):
            # Linux
            if subprocess.call(["sudo", "systemctl", "start", "grease"]) != 0:
                return False
            return True
        else:
            self.ioc.getLogger().error("Unrecognized operating system [{0}]".format(platform))
            return False

    def stop(self):
        """Stopping the daemon based on the platform

        Returns:
            bool: stop success

        """
        plat = platform.system().lower()
        if plat.startswith("win"):
            # Windows
            win32serviceutil.HandleCommandLine(AppServerSvc, argv=['', 'stop'])
            return True
        elif plat.startswith("dar"):
            if subprocess.call(["sudo", "launchctl", "unload", "/Library/LaunchDaemons/net.grease.daemon.plist"]) != 0:
                return False
            # MacOS
            return True
        elif plat.startswith("lin"):
            # Linux
            if subprocess.call(["sudo", "systemctl", "stop", "grease"]) != 0:
                return False
            return True
        else:
            self.ioc.getLogger().error("Unrecognized operating system [{0}]".format(platform))
            return False

    def run(self, timing=None):
        """Actual running of the daemon

        Args:
            timing (int): Amount of seconds the daemon should run for

        Returns:
            None: Should never return

        """
        i = 0
        if not timing:
            while True:
                if i % 100 == 0:
                    self.ioc.getLogger().debug("Test Message {0}".format(i))
                i += 1
        else:
            current_second = datetime.datetime.utcnow().second
            while current_second + 5 >= datetime.datetime.utcnow().second:
                if i % 100 == 0:
                    self.ioc.getLogger().debug("Test Message {0}".format(i))
                i += 1
