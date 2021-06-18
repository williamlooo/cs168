"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

import sim.api as api
from cs168.dv import RoutePacket, \
                     Table, TableEntry, \
                     DVRouterBase, Ports, \
                     FOREVER, INFINITY

class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # Dead entries should time out after this interval
    GARBAGE_TTL = 10

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = True

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (self.SPLIT_HORIZON and self.POISON_REVERSE), \
                    "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self

        #history datstruct for stage 10
        self.history = {} #{(out_port,dst):latency}
        #self.history = []


    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        # TODO: fill this in!
        self.table[host] = TableEntry(dst=host, port=port,latency=self.ports.get_latency(port),expire_time=FOREVER)

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        # TODO: fill this in!
        if packet.dst not in self.table or self.table[packet.dst].latency >= INFINITY:
            return #drop
        else:
            out_port = self.table[packet.dst].port
            self.send(packet,port=out_port)

    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        # TODO: fill this in!
                    
        if single_port != None:
            ports = [single_port]
        else:
            ports = self.ports.get_all_ports()

        for out_port in ports:
            for host,entry in self.table.items():
                if self.SPLIT_HORIZON:  # added during split horizon update (stage 6)
                    if entry.port == out_port:
                        continue

                if self.POISON_REVERSE:
                    if entry.port == out_port:
                        if force or ((out_port, host) not in self.history.keys() or (self.history[(out_port, host)] != INFINITY)):
                            self.send(RoutePacket(host, INFINITY), port=out_port)
                            self.history[(out_port, host)] = INFINITY
                            continue


                #if force or ((out_port, host) not in self.history.keys() or (self.history[(out_port, host)] != INFINITY and self.history[(out_port, host)] != self.table[host].latency)):
                if (out_port,host) in self.history.keys() and self.history[(out_port, host)] == INFINITY:
                    if force:
                        self.send(RoutePacket(host, entry.latency), port=out_port)
                        self.history[(out_port, host)] = entry.latency
                    continue
                if (out_port,host) not in self.history.keys() or self.history[(out_port, host)] != self.table[host].latency:
                    self.send(RoutePacket(host, entry.latency), port=out_port)
                    self.history[(out_port, host)] = entry.latency
                    continue
                if force:
                    self.send(RoutePacket(host, entry.latency), port=out_port)
                    self.history[(out_port, host)] = entry.latency
                    continue



    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        # TODO: fill this in!
        hosts_to_delete = []

        for host,entry in self.table.items():
            if entry.expire_time <= api.current_time(): #delete if equal to expiry time as well.
                hosts_to_delete.append(host)

        for host in hosts_to_delete:
            if self.POISON_EXPIRED:  # added during poison expired update (stage 9)
                self.table[host] = TableEntry(dst=self.table[host].dst, port=self.table[host].port, latency=INFINITY,
                                                   expire_time=self.table[host].expire_time)
            else:
                del self.table[host]
                self.s_log("Removed route to {} has expire time {}, time is {}".format(host, entry.expire_time, api.current_time()))


    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        # TODO: fill this in!

        if route_latency == INFINITY: #handling for infinity inputs (stage 8)
            if route_dst not in self.table:
                return #ignore if not in table
            else:
                print("RECEIVED INFINITY AD")
                if self.table[route_dst].latency != INFINITY:
                    self.table[route_dst] = TableEntry(dst=route_dst, port=port, latency=INFINITY,
                                                   expire_time=self.table[route_dst].expire_time)
                    #self.send_routes(force=False)
                    return
        else:
            if route_dst not in self.table:
                port_latency = self.ports.get_latency(port)
                self.table[route_dst] = TableEntry(dst=route_dst, port=port, latency=route_latency+port_latency,expire_time=api.current_time() + self.ROUTE_TTL)
                self.send_routes(force=False)
                return

            elif port == self.table[route_dst].port: #update same port
                port_latency = self.ports.get_latency(port)
                self.table[route_dst] = TableEntry(dst=route_dst, port=port,latency=route_latency+port_latency,expire_time=api.current_time() + self.ROUTE_TTL)
                self.send_routes(force=False)
                return

            elif route_latency+self.ports.get_latency(port) < self.table[route_dst].latency: #update with new port
                self.table[route_dst] = TableEntry(dst=route_dst, port=port,latency=route_latency + self.ports.get_latency(port),expire_time=api.current_time() + self.ROUTE_TTL)
                self.send_routes(force=False)
                return
            else: #subpar path, ignore
                return


    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

        # TODO: fill in the rest!

        if self.SEND_ON_LINK_UP:
            self.send_routes(force=True,single_port=port)
                


    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router does down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.ports.remove_port(port)

        # TODO: fill this in!
        print(self.table)
        print("HANDLE LINK DOWN FOR "+str(port))

        hosts_to_delete = []
        for host, entry in self.table.items():
            if entry.port == port:
                hosts_to_delete.append(host)

        if not self.POISON_ON_LINK_DOWN:
            for host in hosts_to_delete:
                del self.table[host]
                self.s_log("Removed route to {}, time is {}".format(host, api.current_time()))

        else: #POSION ON LINK DOWN
            print("POISON ON LINK DOWN")
            for host in hosts_to_delete:
                self.table[host] = TableEntry(dst=self.table[host].dst, port=self.table[host].port, latency=INFINITY,expire_time=self.table[host].expire_time)
                self.send_routes(force=False)
                self.s_log("Removed route to {}, time is {}".format(host,api.current_time()))
        print(self.table)

    # Feel free to add any helper methods!
