__doc__ = """
Usage: %(scriptname)s [OPTIONS] COMMAND

Commands:
    run:
        Run the robot. This will enter an indefinite loop that will keep
        parsing and updating feeds forever. If at some point there are no
        feeds available that need to be updated, it will just wait.

        Options:
            --as-daemon     Run as a unix daemon.

    pause:
        Pauses a currently running robot.

    resume:
        Resumse a currently running, paused robot.

    stop:
        Shuts down a currently running robot.

    help:
        This message.

> feedplatform start
> feedplatform stop
> feedplatform status
> feedplatform suspend
> feedplatform validate (config file)
> feedplatform show-tables
"""

import sys
import Pyro.core

def cmd_run():
    """Implementation of the run command."""

    class RobotControl(Pyro.core.ObjBase):
        terminated = False
        paused = False
        @classmethod
        def pause(self):
            self.paused = True
        @classmethod
        def resume(self):
            self.paused = False
        @classmethod
        def stop(self):
            self.terminated = True

    Pyro.core.initServer(banner=0)
    daemon = Pyro.core.Daemon()
    robot = RobotControl()
    daemon.connect(robot, "control")

    try:
        while True:
            # get the next feed
            #check local queue:
            #or get from database
            # update the feed

            # handle control requests
            daemon.handleRequests(0)
            if robot.terminated:
                break;
            while robot.paused:
                pass
    finally:
        daemon.shutdown()

def main(argv):
    """Main program"""
    # parse arguments
    cmd = "run"

    if cmd == "run":
        #if runasdaemon:
        #    from djutils import daemon
        #    daemon.detach()
        return cmd_run()

if __name__ == '__main__':
    sys.exit(main(sys.argv) or 0)