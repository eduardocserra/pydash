from r2a.ir2a import IR2A
from player.parser import *
import time
from statistics import mean
import sys


class R2A_Panda(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.throughputs = []
        self.calc_throughputs = []
        self.smooth_throughputs = []
        self.request_time = 0
        self.time_download = []
        self.wait_time = 0
        self.inter_request_time = []
        self.qi = []
        self.seg_duration = 1
        self.selected_qi = []
        self.buffer_min = 20

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
        #time.sleep(self.wait_time)
        self.request_time = time.perf_counter()
        x = 0
        w = 0.35 * 1000000
        k = 0.14  # 0.04, 0.07, 0.14 até 0.56, aumentando 0.14
        E = 0.15
        alfa = 0.2
        limit_calc_throughput = False

        if len(sys.argv) >= 5:
            w = float(sys.argv[1]) * 1000000
            k = float(sys.argv[2])
            E = float(sys.argv[3])
            alfa = float(sys.argv[4])
        
        if len(sys.argv) >= 8:
            limit_calc_throughput = True

        y = self.throughputs[0]
        if len(self.throughputs) == 1:
            x = self.throughputs[0]
        else:
            x = abs((w - max((0, self.calc_throughputs[-1] - self.throughputs[-1] + w))
                     ) * k * self.inter_request_time[-1] + self.calc_throughputs[-1])
            if self.whiteboard.get_amount_video_to_play() < self.buffer_min and x > 4 * self.throughputs[-1] and limit_calc_throughput:
                x = 4 * self.throughputs[-1]
                y = 4 * self.throughputs[-1]
            else:
                y = abs(-alfa * \
                    (self.smooth_throughputs[-1] - x) * \
                    self.inter_request_time[-1] + self.smooth_throughputs[-1])
            self.calc_throughputs.append(x)
            self.smooth_throughputs.append(y)

        selected_rup = self.qi[0]
        selected_rdown = self.qi[0]

        rup = y * (1 - E)
        rdown = y

        for i in self.qi:
            if rup > i:
                selected_rup = i
            if rdown > i:
                selected_rdown = i

        if len(self.selected_qi) == 0:
            self.selected_qi.append(selected_rdown)
        elif self.selected_qi[-1] < selected_rup:
            self.selected_qi.append(selected_rup)
        elif selected_rup <= self.selected_qi[-1] < selected_rdown:
            self.selected_qi.append(self.selected_qi[-1])
        else:
            self.selected_qi.append(selected_rdown)

        msg.add_quality_id(self.selected_qi[-1])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        
        beta = 0.2

        if len(sys.argv) >= 7:
            self.buffer_min = float(sys.argv[5])
            beta = float(sys.argv[6])

        B = self.whiteboard.get_amount_video_to_play()
        if len(self.throughputs) == 1:
            B = (1 - msg.get_bit_length() /
                 self.calc_throughputs[0]) * self.seg_duration / beta + self.buffer_min
        target_inter_time = msg.get_bit_length() * self.seg_duration / self.calc_throughputs[-1] + beta * (
                B - self.buffer_min)
        actual_inter_time = time.perf_counter() - self.request_time  # T~[n] próximo T~[n-1]
        if actual_inter_time < target_inter_time:
            self.wait_time = target_inter_time - actual_inter_time
        else:
            self.wait_time = 0

        self.inter_request_time.append(max((target_inter_time, actual_inter_time)))  # T[n] próximo T[n-1]
        self.throughputs.append(msg.get_bit_length() * self.seg_duration / actual_inter_time)
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
