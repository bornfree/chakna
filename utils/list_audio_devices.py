#!/usr/bin/env python3
import pyaudio

def get_devices():
    p = pyaudio.PyAudio()
    devices = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        devices.append({
            'Index': str(i),
            'Name': info['name'],
            'InCh': str(info['maxInputChannels']),
            'OutCh': str(info['maxOutputChannels']),
            'Rate': str(int(info['defaultSampleRate']))
        })
    p.terminate()
    return devices

def print_table(devices, columns):
    # compute column widths
    widths = {col: len(col) for col in columns}
    for dev in devices:
        for col in columns:
            widths[col] = max(widths[col], len(dev[col]))
    # header
    header = "  ".join(col.ljust(widths[col]) for col in columns)
    sep    = "  ".join('-'*widths[col]    for col in columns)
    print(header)
    print(sep)
    # rows
    for dev in devices:
        print("  ".join(dev[col].ljust(widths[col]) for col in columns))

if __name__ == '__main__':
    cols = ['Index','Name','InCh','OutCh','Rate']
    devs = get_devices()
    print_table(devs, cols)
