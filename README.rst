Background
----------

This is a very crude hack to make Enthought's Traits_ work in a
multi-process situation. Let's say a process called Alice has a
variable called camera, which is an instance of (a subclass of)
HasTraits. Now, if another process called Bob wants to be notified
when camera.shutter changes, this should happen using the normal
Traits machinery. Furthermore, if Bob wants to change Alice's
camera.shutter settings, Alice should be notified of those changes.

There was a little discussion_ on this subject on the enthought-dev
email list, with Robert Kern's idea being to use Python 2.6's
multiprocess module to create Proxy objects of HasTraits subclasses
which would transparently do this. I suspect such an approach would be
very slick, but was beyond my one-day abilities, and I was on a
deadline to get some code working.

Therefore, I created a hack: both the Alice and Bob processes have
full copies of the camera instance which mirror each other. For my
real world usage, Alice's camera instance would be connected to
something that actually *does* something, such as take pictures with a
real camera, whereas Bob's camera instance would be connected to a GUI
on a remote computer. The synchronization between the two processes
happens using Pyro_ (Python remote objects). (The dependency on Pyro
could probably be removed in favor of using multiprocess, but I was
already familiar with Pyro and couldn't immediately figure out how to
do the equivalent things with multiprocess.)

Anyhow, that is the motivation behing the example here. I plan to
continue tinkering with this code until it's working for me in the
real world.

 - Andrew Straw <strawman@astraw.com>

.. _discussion: https://mail.enthought.com/pipermail/enthought-dev/2008-October/018545.html
.. _Traits: http://code.enthought.com/projects/traits/
.. _Pyro: http://pyro.sourceforge.net/

Quickstart
----------

To run the demo, run this in one terminal::

  # Start the "do" program -- Alice in the motivation above
  python wx_demo.py do

And run this in another terminal::

  # Start the "view" program -- Bob in the motivation above
  python wx_demo.py view

License
-------

This code licensed with the MIT license (see the source code for the
full license).
