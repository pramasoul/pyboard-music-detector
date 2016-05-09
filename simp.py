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


class Thing:
    pass
        

def timed_lase(freq):

    class LS:
        def __init__(self, codelen):
            self.phase = 0
            self.x = 1
            self.code = array.array('B', (rng() & 1 for t in range(codelen)))
            self.code_i = 0


        def tick(self):
            laser.value(self.x)
            if self.code_i >= len(self.code):
                self.x = 1
            else:
                if self.phase:
                    self.x = not self.x
                else:
                    #self.x = rng() & 1
                    self.x = self.code[self.code_i]
                    self.code_i += 1
            self.phase = not self.phase
            self.signal()

        def signal(self):
            scope.value(self.phase)


    def tick(t):
        ls.tick()

    print('timed lasing')
    print(10)
    xtim = Timer(7)
    laser = Pin('Y3', Pin.OUT_OD)
    photodiode = ADC('X11')
    scope = Pin('Y12', Pin.OUT_PP)
    pd_buf = array.array('h', range(16))
    ls = LS(len(pd_buf)//2)
    rtim = Timer(8)
    print(ls.code)
    xtim.init(freq=freq)
    rtim.init(freq=freq)
    xtim.callback(tick)

    n = 0
    while True:    
        photodiode.read_timed(pd_buf, rtim)
        #print(n, ls.code_i, sum(pd_buf)/len(pd_buf))
        print(n, ls.code_i, pd_buf)
        ls.code_i = 0
        n += 1


def simple_lase():
    print('simple lasing')
    laser = Pin('Y3', Pin.OUT_OD)
    photodiode = ADC('X11')
    phase = 0
    v = 0
    x = prev_x = 0
    filtered = 0.0
    peak_filtered = 0.0
    baseline = 0.0
    i = 0
    mon = DAC('X5', bits=12)
    mon2 = DAC('X6', bits=12)
    scope = Pin('Y12', Pin.OUT_PP)
    scope2 = Pin('Y10', Pin.OUT_PP)
    while True:
        scope.value(phase)
        v = photodiode.read()
        laser.value(x)
        delta = 0.01 * v
        if prev_x:
            filtered -= delta
        else:
            filtered += delta
        prev_x = x
        if phase:
            x = rng() & 1
        else:
            x = not x
            if filtered > peak_filtered:
                peak_filtered = filtered
            else:
                peak_filtered += (filtered - peak_filtered) * 0.001
            
            hammer = filtered < 0.4 * peak_filtered and peak_filtered > 10.0
            scope2.value(hammer)

            mon.write(min(4095, max(0, int(filtered + 127.5))))
            mon2.write(min(4095, max(0, int(peak_filtered + 127.5))))

            if i%500 == 0:
                print(filtered, peak_filtered - filtered)
            i += 1
            filtered *= 0.99
        phase = not phase


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


def main():
    micropython.alloc_emergency_exception_buf(100)
    print('simp here')
    beam = LaserBeam('Y3', 'X11')
    mic = Mic('X12')
    while True:
        print('laser {}, mic {}'.format(beam.interrupted(), mic.excited()))

    tim = Timer(6)
    tim.init(freq=96000)
    buf = array.array('h', range(9600))
    ac = array.array('f', range(9600))
    mic = ADC('X12')
    mon = DAC('X5', bits=12)
    #mon.write_timed(buf, tim, mode=DAC.CIRCULAR)
    while True:
        mic.read_timed(buf, tim)
        mon.write_timed(buf, tim, mode=DAC.NORMAL)
        mean = sum(buf) / len(buf)
        for i in range(len(buf)):
            ac[i] = buf[i] - mean
        print(sum(ac), ac[:10])
        power = sum(v*v for v in ac) / len(ac)
        hv2 = hv(ac, 2) / power
        hv3 = hv(ac, 2) / power
        print("mean {}, power {}, h2 {}, h3 {}".format(mean, power, hv2, hv3))

if __name__ == '__main__':
    main()
