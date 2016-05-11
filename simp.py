#
# simple

import array
from pyb import Pin, Timer, rng, ADC, DAC
from time import sleep
import micropython


def hv(signal, harmonic):
    length = len(signal)
    return sum(signal[i]*signal[(harmonic*i)%length]
               for i in range(length)) / length

class LaserBeam:
    def __init__(self, laser_pinname, photodiode_pinname):
        self.laser = Pin(laser_pinname, Pin.OUT_OD)
        self.photodiode = ADC(photodiode_pinname)
        self.threshold = 100

    def ping(self):
        dark = self.photodiode.read()
        self.laser.value(0)          # pull down to on
        light = self.photodiode.read()
        self.laser.value(1)          # float to off
        return light-dark

    def interrupted(self):
        return self.ping() < self.threshold \
            and sum(self.ping() for i in range(10)) < 10 * self.threshold


class Mic:
    def __init__(self, mic_pinname, timer_id=6):
        self.mic = ADC(mic_pinname)
        self.tim = Timer(timer_id, freq=48000)
        self.samples = array.array('h', range(4800))

    def level(self):
        samples = self.samples
        self.mic.read_timed(samples, self.tim)
        ave = sum(samples) / len(samples)
        return sum((v-ave)**2 for v in samples) / len(samples)

    def excited(self):
        return self.level() > 100000


class Piano:
    def __init__(self, mic, beam):
        self.mic = mic
        self.beam = beam

    def playing(self):
        #FIXME
        return self.beam or self.mic


class CL1:
    def __init__(self, stop_cmd, stop_status,
                 rec_cmd, rec_status,
                 play_cmd, play_status):
        self.rec_cmd = Pin(rec_cmd, Pin.OUT_OD)
        self.rec_cmd.value(1)
        self.stop_cmd = Pin(stop_cmd, Pin.OUT_OD)
        self.stop_cmd.value(1)
        self.play_cmd = Pin(play_cmd, Pin.OUT_OD)
        self.play_cmd.value(1)
        self.rec_status = Pin(rec_status, Pin.IN, pull=Pin.PULL_UP)
        self.stop_status = Pin(stop_status, Pin.IN, pull=Pin.PULL_UP)
        self.play_status = Pin(play_status, Pin.IN, pull=Pin.PULL_UP)


    def stopped(self):
        return not self.stop_status.value()

    def recording(self):
        return not self.rec_status.value()

    def playing(self):
        return not self.play_status.value()

    #FIXME: timeouts
    def stop(self):
        if not self.stopped():
            self.stop_cmd.value(0)
            sleep(0.1)
        self.stop_cmd.value(1)

    def record(self):
        if not self.recording():
            self.rec_cmd.value(0)
            sleep(0.1)
        self.rec_cmd.value(1)

    def play(self):
        if not self.playing():
            self.play_cmd.value(0)
            sleep(0.1)
        self.play_cmd.value(1)



def main():
    micropython.alloc_emergency_exception_buf(100)
    print('simp here')
    beam = LaserBeam('Y3', 'X11')
    mic = Mic('X12')
    deck = CL1('X17', 'X18', 'X19', 'X20', 'X21', 'X22')
    t = ((deck.stopped, 'stopped'),
         (deck.recording, 'recording'),
         (deck.playing, 'playing'))
    while True:
        print('laser {}, mic {}'.format(beam.interrupted(), mic.excited()))
        for test, label in t:
            if test():
                print(label)

if __name__ == '__main__':
    main()
