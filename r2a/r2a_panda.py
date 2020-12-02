from r2a.ir2a import IR2A
from player.parser import *
import time
from statistics import mean


class R2A_Panda(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.throughputs = []
        self.calc_throughputs = []
        self.smooth_throughputs = []
        self.time_download = []
        self.inter_request_time = []
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
            self.smooth_throughputs.append(msg.get_bit_length() / t)

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()
        x = 0
        w = 0.35 * 1000000
        k = 0.14  #0.04, 0.07, 0.14 até 0.56, aumentando 0.14
        E = 0.15
        alfa = 0.2
        y = self.throughputs[0]
        if len(self.throughputs) == 1:
            x = self.throughputs[0]
        else:
            x = abs((w - max((0, self.calc_throughputs[-1] - self.throughputs[-1] + w))
                 ) * k * self.inter_request_time[-1] + self.calc_throughputs[-1])
            y = -alfa * \
                (self.smooth_throughputs[-1] - x) * \
                self.inter_request_time[-1] + self.smooth_throughputs[-1]
            self.calc_throughputs.append(x)
            self.smooth_throughputs.append(y)
            
        print(f'real_throughput={self.throughputs}')
        print(f'calc_throughput={self.calc_throughputs}')
        print(f'smooth_throughput={self.smooth_throughputs}')
        selected_qi = self.qi[0]
        for i in self.qi:
            if y > i:
                selected_qi = i
        print(f'qi={selected_qi}')
        msg.add_quality_id(selected_qi)
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        buffer_min = 55
        beta = 0.2
        B = self.whiteboard.get_amount_video_to_play()
        if len(self.throughputs) == 1:
            B = (1 - msg.get_bit_length() /
                 self.calc_throughputs[0]) * self.seg_duration / beta + buffer_min
            print(f'B={B}')
        target_inter_time = msg.get_bit_length() * self.seg_duration / self.calc_throughputs[-1] + beta * (B - buffer_min)
        actual_inter_time = time.perf_counter() - self.request_time  # T~[n] próximo T~[n-1]
        
        self.inter_request_time.append(max((target_inter_time, actual_inter_time)))  #T[n] próximo T[n-1]
        print(f'time={self.inter_request_time}')
        self.throughputs.append(msg.get_bit_length() * self.seg_duration / actual_inter_time)
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
