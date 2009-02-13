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

import os, sys
import Pyro, Pyro.core

Pyro.config.PYRO_MULTITHREADED = 0 # We do the multithreading around here...

reserved_trait_names = ['trait_added','trait_modified','send_over_net']

class MaybeRemoteHasTraits(traits.HasTraits):
    send_over_net = traits.Bool(True)

class Sender:
    def __init__(self,callback_api,id):
        self._callback_api = callback_api
        self._id = id
    def doit(self, traited_object, trait_name, new_value):
        if traited_object.send_over_net:
            if trait_name in reserved_trait_names:
                return
            self._callback_api.fire(self._id,trait_name, new_value)


class RemoteAPI(Pyro.core.ObjBase):
    def __init__(self,*args,**kwds):
        if 'key' in kwds:
            self._key = kwds['key']
            del kwds['key']
        else:
            self._key = None
        Pyro.core.ObjBase.__init__(self,*args,**kwds)
        self._remote_pyro_cache = {}
        self._server = None
        self._name_obj_dict = {}
        self._strongrefs = [] # prevent garbage collection
        self._ids2objs = {}

    def get_key(self):
        return self._key

    def _local_set_server(self,server):
        self._server=server

    def _local_add_name(self,name,obj):
        self._name_obj_dict[name]=obj

    def get_clone_info(self,name):
        """return the class of the instance with name"""
        instance = self._name_obj_dict[name]
        klass = instance.__class__
        callback_id = '%d_%d'%(hash(instance),os.getpid())
        self._ids2objs[callback_id] = instance

        initial_value_dict = {}
        for n in instance.trait_names():
            if n in reserved_trait_names:
                continue
            if instance.traits()[n].type == 'event':
                # events are write-only (XXX how to check for other write only?)
                continue
            initial_value_dict[n]=getattr(instance,n)

        return klass, initial_value_dict, callback_id

    def register_listener(self, name, cb_hostname, cb_port, callback_id):
        obj = self._name_obj_dict[name]
        callback_api = self._server.get_remote_api( cb_hostname, cb_port)
        s = Sender( callback_api, callback_id)
        obj.on_trait_change( s.doit )
        self._strongrefs.append(s) # prevent garbage collection

    def fire(self,callback_id,trait_name,new_value):
        # We are in a oneway Pyro method here; an exception will do nothing.
        if callback_id not in self._ids2objs:
            sys.stderr.write('%s not found\n'%callback_id)
            sys.stderr.write('*'*80+'\n')
            sys.exit(1)
        traited_object = self._ids2objs[callback_id]

        # This is a crude lock that prevents our notifications from coming back:
        setattr( traited_object, 'send_over_net', False)
        setattr( traited_object, trait_name, new_value)
        setattr( traited_object, 'send_over_net', True)

class ServerObj(object):
    def __init__(self,hostname,port,key=None):
        Pyro.core.initServer(banner=0)
        self._hostname = hostname
        self._port = port
        self._daemon = Pyro.core.Daemon(host=self._hostname,port=self._port)
        self._key = key
        self._local_api = RemoteAPI(key=self._key)
        self._local_api._local_set_server(self)
        self._remote_apis = {}
        self._strongrefs = [] # prevent garbage collection
        URI=self._daemon.connect(self._local_api,'api')
    def serve_name(self,name,obj):
        self._local_api._local_add_name(name,obj)

    def handleRequests(self,*args,**kwds):
        self._daemon.handleRequests(*args,**kwds)

    def _connect(self,remote_hostname,remote_port):
        URI = "PYROLOC://%s:%d/%s" % (remote_hostname,remote_port,'api')
        remote_api = Pyro.core.getProxyForURI(URI)
        remote_api._setOneway(['fire','x'])
        remote_id = (remote_hostname,remote_port)
        self._remote_apis[remote_id] = remote_api

    def get_remote_api(self,remote_hostname,remote_port):
        remote_id = (remote_hostname,remote_port)
        if remote_id not in self._remote_apis:
            self._connect(remote_hostname,remote_port)
        return self._remote_apis[remote_id]

    def get_proxy_hastraits_instance(self,remote_hostname,remote_port,name,key=None):
        remote_api=self.get_remote_api(remote_hostname,remote_port)
        if key is not None:
            remote_key = remote_api.get_key()
            assert key == remote_key
        if self._key is not None:
            remote_key = remote_api.get_key()
            assert self._key == remote_key
        klass, val_dict, remote_callback_id = remote_api.get_clone_info(name)
        local_clone = klass(**val_dict)

        # register bi-directional listeners

        # 1) register remote changes to be reflected in local clone
        local_callback_id = '%s_%s'%(hash(local_clone),os.getpid())
        self._local_api._ids2objs[local_callback_id] = local_clone
        remote_api.register_listener(name,
                                     self._hostname,self._port,
                                     local_callback_id)

        # 2) register local changes to be reflected in remote

        # XXX TODO: create a handler function that checks remote to validate.

        s = Sender(remote_api, remote_callback_id)
        local_clone.on_trait_change( s.doit )
        self._strongrefs.append( s ) # prevent garbage collection

        return local_clone

