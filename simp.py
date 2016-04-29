#
# simple

import array
import pyb
import micropython


def hv(signal, harmonic):
    return 0.0


def main():
    print('simp here')
    micropython.alloc_emergency_exception_buf(100)
    tim = pyb.Timer(6)
    tim.init(freq=96000)
    buf = array.array('h', range(9600))
    ac = array.array('f', range(9600))
    mic = pyb.ADC('X12')
    mon = pyb.DAC('X5', bits=12)
    #mon.write_timed(buf, tim, mode=pyb.DAC.CIRCULAR)
    while True:
        mic.read_timed(buf, tim)
        mon.write_timed(buf, tim, mode=pyb.DAC.NORMAL)
        mean = sum(buf) / len(buf)
        for i in range(len(buf)):
            ac[i] = buf[i] - mean
        power = sum(v**2 for v in ac) / len(ac)
        
        print(mean, power, end='\r')

if __name__ == '__main__':
    main()
