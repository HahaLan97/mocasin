# Copyright (C) 2017 TU Dresden
# All Rights Reserved
#
# Authors: Christian Menard
#          Bhaavan Goel

import numpy as np

from .platform import Resource


# This is not realy needed in the moment, but maybe we want to use
# other NoC topologies than mesh later on.
class Noc:

    def get_route(self, a, b):
        return None


class TorusNoc(Noc):
    def __init__(self, routing_algo, width, length):
        self.Routers=[]
        self.routing_algo=routing_algo
        self.width=width
        self.length=length

        routers=[[0 for l in range(length)] for w in range(width)]

        for l in range(length):
            for w in range(width):
                r=Router(w,l)
                r.outgoing_links.append(Link(8, str(w)+str(l)+'_'+str((w+1)%width)+str(l)))
                r.outgoing_links.append(Link(8, str(w)+str(l)+'_'+str((w-1)%width)+str(l)))
                r.outgoing_links.append(Link(8, str(w)+str(l)+'_'+str(w)+str((l+1)%length)))
                r.outgoing_links.append(Link(8, str(w)+str(l)+'_'+str(w)+str((l-1)%length)))
                routers[w][l]=r
        self.Routers=routers
    def create_ni(self, eps, x, y):
        ni_inst=NI(Link(8, eps[0].name+'_'+eps[1].name+' to '+str(x)+str(y)), eps)
        self.Routers[x][y].outgoing_links.append(Link(8, str(x)+str(y)+' to '+eps[0].name+'_'+eps[1].name))
        self.Routers[x][y].ni.append(ni_inst)

    def get_route(self, a, b):
        if self.routing_algo=="xy":
            return self.get_route_xy(a, b)

        if self.routing_algo=="yx":
            return self.get_route_yx(a, b)

    def get_route_xy(self, a, b):

        a_loc,a_ni,b_loc,b_ni,b_link=find(self, a, b)
        x_diff=[a_loc[0]-b_loc[0]]
        x_diff.append(np.sign(x_diff[0]))
        x_diff_rev=self.width-abs(x_diff[0])
        if x_diff_rev<abs(x_diff[0]):
            x_diff[0]=x_diff_rev
            x_diff[1]*=-1

        y_diff=[a_loc[1]-b_loc[1]]
        y_diff.append(np.sign(y_diff[0]))
        y_diff_rev=self.length-abs(y_diff[0])
        if y_diff_rev<abs(y_diff[0]):
            y_diff[0]=y_diff_rev
            y_diff[1]*=-1
        out=[a_ni.outgoing_link]
        for i in range(x_diff[0]*x_diff[1]):

            if x_diff[1]==-1:
                out.append(self.Routers[(a_loc[0]-i*x_diff[1])%self.width][a_loc[1]].outgoing_links[0])
            else:
                out.append(self.Routers[(a_loc[0]-i*x_diff[1])%self.width][a_loc[1]].outgoing_links[1])

        for j in range(y_diff[0]*y_diff[1]):

            if y_diff[1]==-1:
                out.append(self.Routers[b_loc[0]][(a_loc[1]-j*y_diff[1])%self.length].outgoing_links[2])
            else:
                out.append(self.Routers[b_loc[0]][(a_loc[1]-j*y_diff[1])%self.length].outgoing_links[3])

        out.append(b_link)
        return out

    def get_route_yx(self, a, b):

        a_loc,a_ni,b_loc,b_ni,b_link=find(self, a, b)
        x_diff=[a_loc[0]-b_loc[0]]
        x_diff.append(np.sign(x_diff[0]))
        x_diff_rev=self.width-abs(x_diff[0])
        if x_diff_rev<abs(x_diff[0]):
            x_diff[0]=x_diff_rev
            x_diff[1]*=-1

        y_diff=[a_loc[1]-b_loc[1]]
        y_diff.append(np.sign(y_diff[0]))
        y_diff_rev=self.length-abs(y_diff[0])
        if y_diff_rev<abs(y_diff[0]):
            y_diff[0]=y_diff_rev
            y_diff[1]*=-1

        out=[a_ni.outgoing_link]

        for j in range(y_diff[0]*y_diff[1]):

            if y_diff[1]==-1:
                out.append(self.Routers[b_loc[0]][(a_loc[1]-j*y_diff[1])%self.length].outgoing_links[2])
            else:
                out.append(self.Routers[b_loc[0]][(a_loc[1]-j*y_diff[1])%self.length].outgoing_links[3])

        for i in range(x_diff[0]*x_diff[1]):

            if x_diff[1]==-1:
                out.append(self.Routers[(a_loc[0]-i*x_diff[1])%self.width][a_loc[1]].outgoing_links[0])
            else:
                out.append(self.Routers[(a_loc[0]-i*x_diff[1])%self.width][a_loc[1]].outgoing_links[1])

        out.append(b_link)
        return out





class MeshNoc(Noc):

    def __init__(self, routing_algo, width, length):
        self.Routers=[]
        self.routing_algo = routing_algo

        routers=[[0 for l in range(length)] for w in range(width)]

        for l in range(length):
            for w in range(width):

                r=Router(w,l)
                r.outgoing_links=[None]*4

                if w+1<width:
                    r.outgoing_links[0]=Link(8, str(w)+str(l)+'_'+str(w+1)+str(l))

                if w-1>=0:
                    r.outgoing_links[1]=Link(8, str(w)+str(l)+'_'+str(w-1)+str(l))

                if l+1<length:
                    r.outgoing_links[2]=Link(8, str(w)+str(l)+'_'+str(w)+str(l+1))

                if l-1>=0:
                    r.outgoing_links[3]=Link(8, str(w)+str(l)+'_'+str(w)+str(l-1))

                routers[w][l]=r
        self.Routers=routers

    def create_ni(self, eps, x, y):
        ni_inst=NI(Link(8, eps[0].name+'_'+eps[1].name+' to '+str(x)+str(y)), eps)
        self.Routers[x][y].outgoing_links.append(Link(8, str(x)+str(y)+' to '+eps[0].name+'_'+eps[1].name))
        self.Routers[x][y].ni.append(ni_inst)

    def get_route(self, a, b):
        if self.routing_algo=="xy":
            return self.get_route_xy(a, b)

        if self.routing_algo=="yx":
            return self.get_route_yx(a, b)

    def get_route_xy(self, a, b):

        a_loc,a_ni,b_loc,b_ni,b_link=find(self, a,b)
        x_diff=[a_loc[0]-b_loc[0]]
        x_diff.append(np.sign(x_diff[0]))
        y_diff=[a_loc[1]-b_loc[1]]
        y_diff.append(np.sign(y_diff[0]))

        out=[a_ni.outgoing_link]
        for i in range(x_diff[0]*x_diff[1]):

            if x_diff[1]==-1:
                out.append(self.Routers[a_loc[0]-i*x_diff[1]][a_loc[1]].outgoing_links[0])
            else:
                out.append(self.Routers[a_loc[0]-i*x_diff[1]][a_loc[1]].outgoing_links[1])

        for j in range(y_diff[0]*y_diff[1]):

            if y_diff[1]==-1:
                out.append(self.Routers[b_loc[0]][a_loc[1]-j*y_diff[1]].outgoing_links[2])
            else:
                out.append(self.Routers[b_loc[0]][a_loc[1]-j*y_diff[1]].outgoing_links[3])

        out.append(b_link)
        return out

    def get_route_yx(self, a, b):

        a_loc,a_ni,b_loc,b_ni,b_link=find(self, a, b)
        x_diff=[a_loc[0]-b_loc[0]]
        x_diff.append(np.sign(x_diff[0]))
        y_diff=[a_loc[1]-b_loc[1]]
        y_diff.append(np.sign(y_diff[0]))

        out=[a_ni.outgoing_link]

        for j in range(y_diff[0]*y_diff[1]):

            if y_diff[1]==-1:
                out.append(self.Routers[b_loc[0]][a_loc[1]-j*y_diff[1]].outgoing_links[2])
            else:
                out.append(self.Routers[b_loc[0]][a_loc[1]-j*y_diff[1]].outgoing_links[3])

        for i in range(x_diff[0]*x_diff[1]):

            if x_diff[1]==-1:
                out.append(self.Routers[a_loc[0]-i*x_diff[1]][a_loc[1]].outgoing_links[0])
            else:
                out.append(self.Routers[a_loc[0]-i*x_diff[1]][a_loc[1]].outgoing_links[1])

        out.append(b_link)
        return out


def find(noc, a, b):
    a_loc=[]
    a_ni=0
    b_loc=[]
    b_ni=0
    b_link=0
    for i in noc.Routers:
        for j in i:
            for ni in j.ni:
                for e in ni.eps:

                    if e.name==a:
                        a_loc=[j.x, j.y]
                        a_ni= ni

                    if e.name==b:
                        b_loc=[j.x, j.y]
                        b_ni=ni
                        for k in j.outgoing_links:
                            if k!=None:
                                if b in k.name:
                                    b_link=k

    return a_loc,a_ni,b_loc,b_ni,b_link


class NI:

    def __init__(self, link, eps):
        self.outgoing_link = link
        self.eps=eps


class Router:

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.outgoing_links = []
        self.ni=[]


class Link(Resource):
    '''
    Represents a communication link between hardware components.

    Each link defines a bandwidth and extends the Resource class. Since
    capacity is set to 1, links may only be used exclusively.
    '''

    def __init__(self, bandwidth, name):
        Resource.__init__(self, name, 1)
        self.bandwidth = bandwidth
