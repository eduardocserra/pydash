#ALUNOS: EDUARDO CASTRO SERRA - 16/0005256
#		 MANOEL VIEIRA COELHO NETO - 18/0137816
#		MATHEUS SIADE FERREIRA - 16/0036691



from r2a.ir2a import IR2A
from player.parser import *
import time
from statistics import mean
import sys


class R2A_Panda(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.throughputs = [] # corresponde a uma lista com os valores reais do throughput
        self.calc_throughputs = [] # corresponde a uma lista com os valores alvo para o throughput usando o PANDA
        self.smooth_throughputs = [] # corresponde a uma lista com os throughputs alvos filtrados
        self.request_time = 0
        self.inter_request_time = [] # tempo entre cada requisição de um novo segmento
        self.qi = []
        self.seg_duration = 1 # duração de um segmento
        self.selected_qi = [] # lista com a qualidade selecionada para cada segmento
        self.buffer_min = 20 # tamanho mínimo para o buffer, deve ser inferior ao máximo definido no json

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)

    def handle_xml_response(self, msg):

        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        t = time.perf_counter() - self.request_time
        if len(self.throughputs) == 0: # utiliza a resposta do mpd para inicializar os valores de throughput
            self.throughputs.append(msg.get_bit_length() / t)
            self.calc_throughputs.append(msg.get_bit_length() / t)
            self.smooth_throughputs.append(msg.get_bit_length() / t)

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()
        x = 0
        w = 0.35 * 1000000 # incremento de prova do bitrate
        k = 0.14  # taxa de convergência de prova
        E = 0.15 # margem de multiplicação
        alfa = 0.2 # taxa de convergência de suavização do throughput alvo
        limit_calc_throughput = False

        if len(sys.argv) >= 2: # permite usar o w como um argumento
            w = float(sys.argv[1]) * 1000000
        
        if len(sys.argv) >= 4: # permite definir se será usado um limitador para o throughput alvo em relação ao real
            limit_calc_throughput = True

        y = self.throughputs[0]
        if len(self.throughputs) == 1: # inicialização o throughput alvo com o valor obtido ao transferir o arquivo mpd
            x = self.throughputs[0]
        else:
            x = abs((w - max((0, self.calc_throughputs[-1] - self.throughputs[-1] + w))
                     ) * k * self.inter_request_time[-1] + self.calc_throughputs[-1]) # faz a equação 1
            if self.whiteboard.get_amount_video_to_play() < self.buffer_min and x > 4 * self.throughputs[-1] and limit_calc_throughput:
                # limitador para o valor máximo do throughput, está definido como 4x o valor do real
                x = 4 * self.throughputs[-1]
                y = 4 * self.throughputs[-1]
            else:
                y = abs(-alfa * \
                    (self.smooth_throughputs[-1] - x) * \
                    self.inter_request_time[-1] + self.smooth_throughputs[-1])  # faz a equação 2
            # guarda o throughput alvo e a suavização
            self.calc_throughputs.append(x)
            self.smooth_throughputs.append(y)

        # Deadzone

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

        msg.add_quality_id(self.selected_qi[-1]) # envia o valor que acabou de ser adicionado na lista após uso do deadzone
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        
        beta = 0.2

        if len(sys.argv) >= 3: # adiciona um valor para o buffer_min por argumento
            self.buffer_min = float(sys.argv[2])

        B = self.whiteboard.get_amount_video_to_play()
        if len(self.throughputs) == 1: # inicializa o valor do buffer, já que inicialmente, não há buffer
            B = (1 - msg.get_bit_length() /
                 self.calc_throughputs[0]) * self.seg_duration / beta + self.buffer_min
        target_inter_time = msg.get_bit_length() * self.seg_duration / self.smooth_throughputs[-1] + beta * (
                B - self.buffer_min) # Equação 5
        actual_inter_time = time.perf_counter() - self.request_time  # T~[n] próximo T~[n-1]

        self.inter_request_time.append(max((target_inter_time, actual_inter_time)))  # T[n] próximo T[n-1], obtém o máximo entre tempo real e alvo
        self.throughputs.append(msg.get_bit_length() * self.seg_duration / actual_inter_time) # adiciona o throughput real na lista para uso no próximo segmento
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
