Juju Wait
=========

This is a Juju plugin that provides the following new juju command::

    juju wait

This command waits until all hooks in the environment have completed
running and there are no more queued to run. It is primarily used by
deployment wrappers and test suites to know when a series on juju
commands (which run asynchronously) have completed and the system is
ready for the next step. Once the Juju environment has reached this
stable state, it will remain stable until some action destabalizes it,
such as operator action, machine reboots or scheduled tasks.
