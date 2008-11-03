## Copyright (c) 2008, Andrew Straw

## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:

## The above copyright notice and this permission notice shall be included in
## all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
## THE SOFTWARE.

import enthought.traits.api as traits
from enthought.traits.ui.api import View, Item, Group
import wx
import remote_traits

import time, sys

class Camera(remote_traits.MaybeRemoteHasTraits):
    shutter = traits.Range(0.0, 10.0, 4.5)
    gain = traits.Range(0.0, 10.0, 1.5)
    brightness = traits.Range(0.0, 1.0, 0.5)

    # =======================================

    traits_view = View( Group( ( Item('shutter'),
                                 Item('gain'),
                                 Item('brightness',width=500),
                                 ),
                               orientation = 'horizontal',
                               show_border = False,
                               ),
                        title = 'Camera Parameters',
                        )


DO_HOSTNAME='localhost'
VIEW_HOSTNAME='localhost'

DO_PORT = 8492
VIEW_PORT = 8493

def my_trait_changed( obj, name, new_value ):
    if name in remote_traits.reserved_trait_names:
        return
    print '%s->%s'%(name,new_value)

def do_func():
    cam = Camera()
    #cam.on_trait_change( my_trait_changed, 'shutter' ) # watch shutter changes
    cam.on_trait_change( my_trait_changed) # watch all changes

    server = remote_traits.ServerObj(DO_HOSTNAME,DO_PORT)
    server.serve_name('cam',cam)

    cam.shutter = 1.0

    tstart = time.time()
    ## while time.time()-tstart<5.0: # run for 5 seconds
    while 1: # run forever

        server.handleRequests(timeout=1.0) # handle network events

        tnow = time.time()
        elapsed = tnow-tstart

        new_val = (elapsed // 2.0) % 10.0 # regularly update the shutter value
        if new_val < 5.5:
            cam.shutter = new_val

class MyApp(wx.App):
    def OnInit(self,*args,**kw):
        wx.InitAllImageHandlers()
        self.frame = wx.Frame(None, -1, "remote traits demo",size=(600,150))

        self.server = remote_traits.ServerObj(VIEW_HOSTNAME,VIEW_PORT)
        self.cam = self.server.get_proxy_hastraits_instance(DO_HOSTNAME,DO_PORT,'cam')

        self.cam.on_trait_change(self.OnShutterChange,'shutter')
        self.cam.on_trait_change(self.OnAnyTraitChange)

        # Create panel and fill it
        panel = wx.Panel(self.frame)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        control = self.cam.edit_traits( parent=panel,
                                        kind='subpanel',
                                        ).control
        sizer.Add(control, 1, wx.EXPAND)
        panel.SetSizer( sizer )

        # Add panel to frame's size
        box = wx.BoxSizer(wx.VERTICAL)
        box.Add(panel,1,wx.EXPAND)
        self.frame.SetSizer(box)
        self.frame.Layout()
        self.frame.SetAutoLayout(True)

        self.frame.Show()
        self.SetTopWindow(self.frame)

        ID_Timer  = wx.NewId()
        self.timer = wx.Timer(self,      # object to send the event to
                              ID_Timer)  # event id to use
        wx.EVT_TIMER(self,  ID_Timer, self.OnTimer)
        self.timer.Start(50) # call every 50 msec
        return True

    def OnTimer(self,event):
        # check for and handle network events
        self.server.handleRequests(timeout=0.0) # return immediately

    def OnAnyTraitChange(self):
        #print 'trait changed'
        pass

    def OnShutterChange(self):
        #print 'shutter changed'
        pass

def view_func():
    myapp = MyApp()
    myapp.MainLoop()

if __name__=='__main__':
    if sys.argv[1]=='do':
        do_func()
    elif sys.argv[1]=='view':
        view_func()
