from r2a.ir2a import IR2A
from player.parser import *
import time
from statistics import mean


class R2A_DynamicPanda(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.throughputs = []
        self.calc_throughputs = []
        self.time_download = []
        self.request_time = 0
        self.qi = []
        self.seg_duration = 1

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):

        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        t = time.perf_counter() - self.request_time
        if len(self.throughputs) == 0:
            self.throughputs.append(msg.get_bit_length() / t)
            self.calc_throughputs.append(msg.get_bit_length() / t)

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()
        x = 0
        B = 0
        beta = 0.2
        w = 0.3
        k = 0.14  #0.04, 0.07, 0.14 até 0.56, aumentando 0.14
        E = 0.15
        buffer_min = 26
        if len(self.throughputs) == 1:
            x = self.throughputs[0]
        else:
            x = (w - max((0, self.calc_throughputs[-1] - self.throughputs[-1] + w))
                 ) * k * (self.request_time - self.time_download[-1]) + self.calc_throughputs[-1]

        selected_qi = self.qi[0]
        for i in self.qi:
            if x > i:
                selected_qi = i
                break
        
        if len(self.throughputs) == 1:
            B = 1 - selected_qi / x * self.seg_duration / beta + buffer_min
        
        msg.add_quality_id(selected_qi)
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        t = time.perf_counter() - self.request_time
        self.time_download.append(time.perf_counter())
        self.throughputs.append(msg.get_bit_length() / t)
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
